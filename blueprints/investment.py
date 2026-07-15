import uuid
import csv
from io import StringIO
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, Response
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, User, InvestmentPackage, Investment, ROITransaction
from forms.investment_forms import PackageForm, InvestmentRequestForm
from decorators import role_required

investment_bp = Blueprint('investment', __name__, url_prefix='/investment')

# ------------------------------
# Helper: Calculate ROI for an investment
# ------------------------------
def calculate_roi(investment_id, force=False):
    """
    Calculate ROI for a single investment.
    If force=True, recalculates even if already completed.
    Returns the ROI amount.
    """
    investment = Investment.query.get_or_404(investment_id)
    # Only calculate if active or if forcing
    if investment.status != 'active' and not force:
        return None

    package = InvestmentPackage.query.get(investment.package_id)
    if not package:
        return None

    # ROI = amount * (expected_roi / 100)
    roi_amount = investment.amount * (package.expected_roi / 100)
    return roi_amount

def calculate_all_roi():
    """
    Calculate ROI for all active investments that have reached their end_date.
    This can be called via a cron job or manually.
    """
    now = datetime.utcnow()
    active_investments = Investment.query.filter(Investment.status == 'active',
                                                 Investment.end_date <= now).all()
    for inv in active_investments:
        roi = calculate_roi(inv.id, force=False)
        if roi is not None:
            # Record ROI transaction
            roi_trans = ROITransaction(
                investment_id=inv.id,
                amount=roi,
                date=datetime.utcnow(),
                note='Auto-calculated ROI'
            )
            inv.roi_earned += roi
            inv.status = 'completed'
            db.session.add(roi_trans)
            db.session.commit()

# ------------------------------
# Public: List investment packages
# ------------------------------
@investment_bp.route('/packages')
def list_packages():
    """Public route for customers to view available investment packages."""
    packages = InvestmentPackage.query.filter_by(is_active=True).all()
    return render_template('investment/packages.html', packages=packages)

# ------------------------------
# Customer: Invest in a package
# ------------------------------
@investment_bp.route('/invest', methods=['GET', 'POST'])
@login_required
def invest():
    """Customer submits investment request."""
    form = InvestmentRequestForm()
    if form.validate_on_submit():
        package = InvestmentPackage.query.get(form.package_id.data)
        if not package:
            flash('Invalid package.', 'danger')
            return redirect(url_for('investment.list_packages'))

        # Check amount is within package limits
        if form.amount.data < package.min_amount:
            flash(f'Amount must be at least ₦{package.min_amount:,.2f}', 'danger')
            return redirect(url_for('investment.invest'))
        if package.max_amount and form.amount.data > package.max_amount:
            flash(f'Amount cannot exceed ₦{package.max_amount:,.2f}', 'danger')
            return redirect(url_for('investment.invest'))

        # Create investment (pending approval if needed)
        # For now, we auto-approve and set as active
        investment = Investment(
            investor_id=current_user.id,
            package_id=package.id,
            amount=form.amount.data,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=package.duration_months*30),
            status='active',
            notes=form.notes.data
        )
        db.session.add(investment)
        db.session.commit()
        flash('Your investment has been recorded successfully.', 'success')
        return redirect(url_for('investment.my_investments'))
    return render_template('investment/invest.html', form=form)

# ------------------------------
# Customer: View my investments
# ------------------------------
@investment_bp.route('/my-investments')
@login_required
def my_investments():
    """Customer dashboard showing their investments."""
    investments = Investment.query.filter_by(investor_id=current_user.id).order_by(Investment.created_at.desc()).all()
    # Calculate totals
    total_invested = sum(i.amount for i in investments)
    total_roi_earned = sum(i.roi_earned for i in investments)
    active_count = sum(1 for i in investments if i.status == 'active')
    return render_template('investment/my_investments.html',
                           investments=investments,
                           total_invested=total_invested,
                           total_roi_earned=total_roi_earned,
                           active_count=active_count)

# ------------------------------
# Admin: Manage investment packages (CRUD)
# ------------------------------
@investment_bp.route('/admin/packages')
@login_required
@role_required(['admin'])
def admin_packages():
    """Admin view of all packages."""
    packages = InvestmentPackage.query.order_by(InvestmentPackage.created_at.desc()).all()
    return render_template('investment/admin_packages.html', packages=packages)

@investment_bp.route('/admin/package/create', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def create_package():
    form = PackageForm()
    if form.validate_on_submit():
        package = InvestmentPackage(
            name=form.name.data,
            description=form.description.data,
            min_amount=form.min_amount.data,
            max_amount=form.max_amount.data,
            expected_roi=form.expected_roi.data,
            duration_months=form.duration_months.data,
            is_active=form.is_active.data
        )
        db.session.add(package)
        db.session.commit()
        flash('Investment package created.', 'success')
        return redirect(url_for('investment.admin_packages'))
    return render_template('investment/package_form.html', form=form, title='Create Package')

@investment_bp.route('/admin/package/<package_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_package(package_id):
    package = InvestmentPackage.query.get_or_404(package_id)
    form = PackageForm(obj=package)
    if form.validate_on_submit():
        package.name = form.name.data
        package.description = form.description.data
        package.min_amount = form.min_amount.data
        package.max_amount = form.max_amount.data
        package.expected_roi = form.expected_roi.data
        package.duration_months = form.duration_months.data
        package.is_active = form.is_active.data
        db.session.commit()
        flash('Package updated.', 'success')
        return redirect(url_for('investment.admin_packages'))
    return render_template('investment/package_form.html', form=form, title='Edit Package')

@investment_bp.route('/admin/package/<package_id>/delete', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_package(package_id):
    package = InvestmentPackage.query.get_or_404(package_id)
    # Check if any investment references this package
    if Investment.query.filter_by(package_id=package.id).first():
        flash('Cannot delete package with existing investments.', 'danger')
        return redirect(url_for('investment.admin_packages'))
    db.session.delete(package)
    db.session.commit()
    flash('Package deleted.', 'success')
    return redirect(url_for('investment.admin_packages'))

# ------------------------------
# Admin: View all investments
# ------------------------------
@investment_bp.route('/admin/investments')
@login_required
@role_required(['admin'])
def admin_investments():
    investments = Investment.query.order_by(Investment.created_at.desc()).all()
    return render_template('investment/admin_investments.html', investments=investments)

# ------------------------------
# Admin: Calculate ROI manually (trigger)
# ------------------------------
@investment_bp.route('/admin/calculate-roi', methods=['POST'])
@login_required
@role_required(['admin'])
def trigger_roi_calculation():
    calculate_all_roi()
    flash('ROI calculation triggered successfully.', 'success')
    return redirect(url_for('investment.admin_investments'))

# ------------------------------
# Admin: Investment Reports
# ------------------------------
@investment_bp.route('/admin/reports')
@login_required
@role_required(['admin'])
def admin_reports():
    # Summary
    total_invested = db.session.query(func.sum(Investment.amount)).scalar() or 0
    total_roi_earned = db.session.query(func.sum(Investment.roi_earned)).scalar() or 0
    active_investments = Investment.query.filter_by(status='active').count()
    completed_investments = Investment.query.filter_by(status='completed').count()

    # Investment by package
    package_stats = db.session.query(
        InvestmentPackage.name,
        func.count(Investment.id).label('count'),
        func.sum(Investment.amount).label('total_amount')
    ).join(InvestmentPackage, Investment.package_id == InvestmentPackage.id)\
     .group_by(InvestmentPackage.name).all()

    return render_template('investment/admin_reports.html',
                           total_invested=total_invested,
                           total_roi_earned=total_roi_earned,
                           active_investments=active_investments,
                           completed_investments=completed_investments,
                           package_stats=package_stats)

# ------------------------------
# Export Investments (CSV)
# ------------------------------
@investment_bp.route('/admin/export')
@login_required
@role_required(['admin'])
def export_investments():
    investments = Investment.query.all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Investor', 'Package', 'Amount', 'Status', 'Start Date', 'End Date', 'ROI Earned'])
    for inv in investments:
        investor = User.query.get(inv.investor_id)
        package = InvestmentPackage.query.get(inv.package_id)
        writer.writerow([
            inv.id,
            investor.get_full_name() if investor else '',
            package.name if package else '',
            str(inv.amount),
            inv.status,
            inv.start_date.strftime('%Y-%m-%d'),
            inv.end_date.strftime('%Y-%m-%d'),
            str(inv.roi_earned)
        ])
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=investments.csv'})
    
