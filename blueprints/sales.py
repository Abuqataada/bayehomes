import uuid
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, Response, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func
from models import db, User, Property, Sale, Payment, Receipt, Invoice, Document, StaffDailyReport
from forms.sales_forms import SaleForm, PaymentForm, SalesFilterForm
from decorators import role_required

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')

# ------------------------------
# Helper functions
# ------------------------------

def generate_receipt_number():
    """Generate a unique receipt number: REC-YYYYMMDD-XXXX"""
    today = datetime.utcnow().strftime('%Y%m%d')
    count = Receipt.query.filter(Receipt.generated_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)).count() + 1
    return f"REC-{today}-{count:04d}"

def generate_invoice_number():
    """Generate a unique invoice number: INV-YYYYMMDD-XXXX"""
    today = datetime.utcnow().strftime('%Y%m%d')
    count = Invoice.query.filter(Invoice.issued_date >= datetime.utcnow().replace(hour=0, minute=0, second=0)).count() + 1
    return f"INV-{today}-{count:04d}"

def generate_installment_invoices(sale):
    """Generate invoices for installment plan."""
    if not sale.is_installment or not sale.installment_plan:
        return
    plan = sale.installment_plan
    down_payment_percent = plan.get('down_payment_percent', 0)
    months = plan.get('months', 1)
    total = sale.total_amount
    down_payment = total * Decimal(down_payment_percent) / 100
    remaining = total - down_payment
    monthly = remaining / months if months > 0 else 0

    # Down payment invoice
    if down_payment > 0:
        inv = Invoice(
            sale_id=sale.id,
            invoice_number=generate_invoice_number(),
            total=down_payment,
            balance_due=down_payment,
            due_date=sale.sale_date,
            status='unpaid'
        )
        db.session.add(inv)

    # Monthly installments
    for i in range(1, months + 1):
        due_date = sale.sale_date + timedelta(days=30*i)
        inv = Invoice(
            sale_id=sale.id,
            invoice_number=generate_invoice_number(),
            total=monthly,
            balance_due=monthly,
            due_date=due_date,
            status='unpaid'
        )
        db.session.add(inv)

def generate_receipt(payment):
    """Generate a receipt for a payment."""
    receipt = Receipt(
        sale_id=payment.sale_id,
        receipt_number=generate_receipt_number(),
        generated_at=payment.payment_date,
        file_url=None  # will be generated as PDF later
    )
    db.session.add(receipt)
    return receipt

# ------------------------------
# List Sales
# ------------------------------

@sales_bp.route('/')
@login_required
@role_required(['admin', 'staff'])
def list_sales():
    form = SalesFilterForm(request.args, meta={'csrf': False})
    query = Sale.query

    if form.customer_id.data:
        query = query.filter(Sale.customer_id == form.customer_id.data)
    if form.property_id.data:
        query = query.filter(Sale.property_id == form.property_id.data)
    if form.status.data:
        query = query.filter(Sale.status == form.status.data)
    if form.start_date.data:
        query = query.filter(Sale.sale_date >= form.start_date.data)
    if form.end_date.data:
        query = query.filter(Sale.sale_date <= form.end_date.data)

    sales = query.order_by(Sale.sale_date.desc()).all()
    return render_template('sales/list.html', sales=sales, form=form)

# ------------------------------
# Create Sale
# ------------------------------

@sales_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'staff'])
def create_sale():
    form = SaleForm()
    if form.validate_on_submit():
        total = form.total_amount.data
        sale = Sale(
            customer_id=form.customer_id.data,
            property_id=form.property_id.data,
            staff_id=current_user.id,
            total_amount=total,
            amount_paid=0,
            balance=total,
            sale_date=form.sale_date.data,
            status='pending',
            is_installment=form.is_installment.data
        )
        if form.is_installment.data:
            sale.installment_plan = {
                'down_payment_percent': form.down_payment_percent.data or 0,
                'months': form.months.data or 1
            }
        else:
            sale.installment_plan = None

        db.session.add(sale)
        db.session.flush()

        # Generate invoices if installment plan
        if sale.is_installment:
            generate_installment_invoices(sale)

        # Update property status to reserved
        prop = Property.query.get(sale.property_id)
        if prop:
            prop.status = 'reserved'

        db.session.commit()
        flash('Sale created successfully.', 'success')
        return redirect(url_for('sales.sale_detail', sale_id=sale.id))

    return render_template('sales/create.html', form=form)

# ------------------------------
# Sale Detail
# ------------------------------

@sales_bp.route('/<sale_id>')
@login_required
@role_required(['admin', 'staff'])
def sale_detail(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    payment_form = PaymentForm()
    # Get invoices and payments
    invoices = sale.invoices.order_by(Invoice.issued_date).all()
    payments = sale.payments.order_by(Payment.payment_date.desc()).all()
    return render_template('sales/detail.html',
                           sale=sale,
                           payment_form=payment_form,
                           invoices=invoices,
                           payments=payments)

# ------------------------------
# Record Payment
# ------------------------------

@sales_bp.route('/<sale_id>/pay', methods=['POST'])
@login_required
@role_required(['admin', 'staff'])
def record_payment(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    form = PaymentForm()
    if form.validate_on_submit():
        amount = form.amount.data
        # Ensure amount does not exceed balance
        if amount > sale.balance:
            flash('Payment amount exceeds outstanding balance.', 'danger')
            return redirect(url_for('sales.sale_detail', sale_id=sale.id))

        payment = Payment(
            sale_id=sale.id,
            amount=amount,
            method=form.method.data,
            reference=form.reference.data,
            status='pending'  # default pending, admin will verify
        )
        db.session.add(payment)
        db.session.flush()

        # Generate receipt (pending verification)
        receipt = generate_receipt(payment)
        db.session.add(receipt)

        # Update sale balance (temporarily, will be final after verification)
        # We update after verification; for now we just record pending payment
        # But we can optionally update amount_paid if we want to show pending payments separately
        # We'll keep sale.amount_paid as verified payments only.
        # For now, we just record payment and keep sale balance unchanged until verified.
        # We can show pending payments in a separate column.

        db.session.commit()
        flash('Payment recorded successfully. Awaiting verification.', 'success')
    else:
        flash('Invalid payment details.', 'danger')
    return redirect(url_for('sales.sale_detail', sale_id=sale.id))

# ------------------------------
# Verify Payment
# ------------------------------

@sales_bp.route('/payment/<payment_id>/verify', methods=['POST'])
@login_required
@role_required(['admin', 'staff'])
def verify_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    if payment.status == 'verified':
        flash('Payment already verified.', 'info')
        return redirect(url_for('sales.sale_detail', sale_id=payment.sale_id))

    payment.status = 'verified'
    payment.verified_by = current_user.id
    payment.verified_at = datetime.utcnow()

    # Update sale amount_paid and balance
    sale = payment.sale
    sale.amount_paid += payment.amount
    sale.balance = sale.total_amount - sale.amount_paid
    if sale.balance <= 0:
        sale.status = 'completed'
        # Update property status to sold
        prop = Property.query.get(sale.property_id)
        if prop and prop.status == 'reserved':
            prop.status = 'sold'

    # Update corresponding invoice if exists
    # Find the earliest unpaid invoice with balance due
    invoice = sale.invoices.filter(Invoice.status == 'unpaid').order_by(Invoice.issued_date).first()
    if invoice:
        if payment.amount >= invoice.balance_due:
            # Pay off this invoice
            invoice.balance_due = 0
            invoice.status = 'paid'
            # If there's remaining amount, apply to next invoice (handled by logic if needed)
        else:
            invoice.balance_due -= payment.amount

    db.session.commit()
    flash('Payment verified successfully.', 'success')
    return redirect(url_for('sales.sale_detail', sale_id=sale.id))

# ------------------------------
# Invoice Management
# ------------------------------

@sales_bp.route('/invoice/<invoice_id>/download')
@login_required
@role_required(['admin', 'staff'])
def download_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    # Generate a printable invoice view (render a template)
    # For now, redirect to a printable page
    return render_template('sales/invoice_print.html', invoice=invoice)

# ------------------------------
# Receipt Download
# ------------------------------

@sales_bp.route('/receipt/<receipt_id>/download')
@login_required
@role_required(['admin', 'staff'])
def download_receipt(receipt_id):
    receipt = Receipt.query.get_or_404(receipt_id)
    # Generate printable receipt view
    return render_template('sales/receipt_print.html', receipt=receipt)

# ------------------------------
# Dashboard / Reports
# ------------------------------

@sales_bp.route('/reports')
@login_required
@role_required(['admin', 'staff'])
def reports():
    # Summary stats
    total_sales = Sale.query.count()
    total_revenue = db.session.query(func.sum(Sale.total_amount)).scalar() or 0
    total_verified_payments = db.session.query(func.sum(Payment.amount)).filter(Payment.status == 'verified').scalar() or 0
    outstanding = total_revenue - total_verified_payments

    # Monthly revenue (current year) - SQLite compatible (no month()/year() functions)
    current_year = datetime.now(timezone.utc).year
    month_expr = func.cast(func.strftime('%m', Sale.sale_date), db.Integer)
    monthly_revenue = db.session.query(
        month_expr.label('month'),
        func.sum(Sale.total_amount).label('revenue')
    ).filter(func.strftime('%Y', Sale.sale_date) == str(current_year)) \
     .group_by(month_expr) \
     .order_by(month_expr) \
     .all()

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    revenue_data = [0]*12
    for m in monthly_revenue:
        revenue_data[m.month-1] = float(m.revenue)
        
    reports = StaffDailyReport.query.all()

    return render_template('sales/reports.html',
                           total_sales=total_sales,
                           total_revenue=total_revenue,
                           total_verified_payments=total_verified_payments,
                           outstanding=outstanding,
                           months=months,
                           revenue_data=revenue_data,
                           reports=reports)

# ------------------------------
# Export Sales (CSV)
# ------------------------------

@sales_bp.route('/export')
@login_required
@role_required(['admin', 'staff'])
def export_sales():
    sales = Sale.query.all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Customer', 'Property', 'Total Amount', 'Paid', 'Balance', 'Status', 'Sale Date'])
    for sale in sales:
        customer = User.query.get(sale.customer_id)
        property = Property.query.get(sale.property_id)
        writer.writerow([
            sale.id,
            customer.get_full_name() if customer else '',
            property.title if property else '',
            str(sale.total_amount),
            str(sale.amount_paid),
            str(sale.balance),
            sale.status,
            sale.sale_date.strftime('%Y-%m-%d')
        ])
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=sales.csv'})
    
