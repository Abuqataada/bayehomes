import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, and_
from models import db, Property, Sale, PropertyStatus, User, UserRole
from forms.property_forms import PropertyForm, PropertyFilterForm
from decorators import role_required
from datetime import datetime, timedelta, timezone

property_mgmt_bp = Blueprint('property_mgmt', __name__, url_prefix='/admin/properties')

# Helper: slugify
def slugify(text):
    import re
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text

def generate_unique_slug(title):
    slug = slugify(title)
    count = 1
    while Property.query.filter_by(slug=slug).first():
        slug = f"{slugify(title)}-{count}"
        count += 1
    return slug

def save_uploaded_images(files, upload_folder):
    """Save uploaded images and return list of filenames."""
    filenames = []
    if not files:
        return filenames
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            file_path = os.path.join(upload_folder, unique_name)
            file.save(file_path)
            filenames.append(unique_name)
    return filenames

# ------------------------------
# Dashboard / Analytics
# ------------------------------

@property_mgmt_bp.route('/dashboard')
@login_required
@role_required(['admin', 'staff'])
def dashboard():
    # Total properties
    total = Property.query.count()
    available = Property.query.filter_by(status='available').count()
    reserved = Property.query.filter_by(status='reserved').count()
    sold = Property.query.filter_by(status='sold').count()
    under_dev = Property.query.filter_by(status='under_development').count()

    # Per estate counts
    estates = db.session.query(Property.estate, func.count(Property.id)).group_by(Property.estate).all()

    # Revenue per estate (from sales)
    revenue_estate = db.session.query(Property.estate, func.sum(Sale.total_amount)).join(Sale, Sale.property_id == Property.id).group_by(Property.estate).all()

    # Monthly sales trend (last 6 months)
    months = []
    sales_trend = []
    for i in range(6):
        month = datetime.utcnow().replace(day=1) - timedelta(days=i*30)
        month_label = month.strftime('%b %Y')
        months.append(month_label)
        count = Sale.query.filter(
            Sale.sale_date >= month,
            Sale.sale_date < month.replace(day=1) + timedelta(days=31) if i==0 else month.replace(day=1) - timedelta(days=30)
        ).count()
        sales_trend.append(count)
    months.reverse()
    sales_trend.reverse()

    return render_template('property_mgmt/dashboard.html',
                           total=total, available=available, reserved=reserved,
                           sold=sold, under_dev=under_dev,
                           estates=estates, revenue_estate=revenue_estate,
                           months=months, sales_trend=sales_trend)

# ------------------------------
# Property List
# ------------------------------

@property_mgmt_bp.route('/')
@login_required
@role_required(['admin', 'staff'])
def property_list():
    form = PropertyFilterForm(request.args, meta={'csrf': False})
    query = Property.query

    if form.status.data:
        query = query.filter(Property.status == form.status.data)
    if form.property_type.data:
        query = query.filter(Property.property_type == form.property_type.data)
    if form.estate.data:
        query = query.filter(Property.estate.ilike(f"%{form.estate.data}%"))
    if form.search.data:
        search = f"%{form.search.data}%"
        query = query.filter(Property.title.ilike(search) | Property.location.ilike(search))

    properties = query.order_by(Property.created_at.desc()).all()
    return render_template('property_mgmt/properties.html', properties=properties, form=form)

# ------------------------------
# Add Property
# ------------------------------

@property_mgmt_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'staff'])
def add_property():
    form = PropertyForm()
    if form.validate_on_submit():
        # Generate slug if not provided
        if form.slug.data:
            slug = slugify(form.slug.data)
            if Property.query.filter_by(slug=slug).first():
                flash('Slug already exists.', 'danger')
                return render_template('property_mgmt/property_form.html', form=form)
        else:
            slug = generate_unique_slug(form.title.data)

        # Save images
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'properties')
        os.makedirs(upload_folder, exist_ok=True)
        images = save_uploaded_images(request.files.getlist('images'), upload_folder)

        property = Property(
            title=form.title.data,
            slug=slug,
            property_type=form.property_type.data,
            estate=form.estate.data,
            plot_number=form.plot_number.data,
            size_sqm=form.size_sqm.data,
            price=form.price.data,
            description=form.description.data,
            location=form.location.data,
            city=form.city.data,
            state=form.state.data,
            bedrooms=form.bedrooms.data,
            bathrooms=form.bathrooms.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            assigned_staff_id=form.assigned_staff_id.data or None,
            status=form.status.data,
            featured=form.featured.data,
            images=images
        )
        db.session.add(property)
        db.session.commit()
        flash('Property added successfully.', 'success')
        return redirect(url_for('property_mgmt.property_list'))

    return render_template('property_mgmt/property_form.html', form=form, title='Add Property')

# ------------------------------
# Edit Property
# ------------------------------

@property_mgmt_bp.route('/<property_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'staff'])
def edit_property(property_id):
    property = Property.query.get_or_404(property_id)
    form = PropertyForm(obj=property)

    if form.validate_on_submit():
        property.title = form.title.data
        if form.slug.data:
            new_slug = slugify(form.slug.data)
            if new_slug != property.slug and Property.query.filter_by(slug=new_slug).first():
                flash('Slug already exists.', 'danger')
                return render_template('property_mgmt/property_form.html', form=form, property=property)
            property.slug = new_slug
        else:
            # If no slug provided, keep existing or generate from title
            pass
        property.property_type = form.property_type.data
        property.estate = form.estate.data
        property.plot_number = form.plot_number.data
        property.size_sqm = form.size_sqm.data
        property.price = form.price.data
        property.description = form.description.data
        property.location = form.location.data
        property.city = form.city.data
        property.state = form.state.data
        property.bedrooms = form.bedrooms.data
        property.bathrooms = form.bathrooms.data
        property.latitude = form.latitude.data
        property.longitude = form.longitude.data
        property.assigned_staff_id = form.assigned_staff_id.data or None
        property.status = form.status.data
        property.featured = form.featured.data

        # Handle image uploads (append new images)
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'properties')
        new_images = save_uploaded_images(request.files.getlist('images'), upload_folder)
        if new_images:
            if property.images:
                property.images.extend(new_images)
            else:
                property.images = new_images

        # Handle image deletion (if any)
        delete_images = request.form.getlist('delete_images')
        if delete_images:
            current_images = property.images or []
            for img in delete_images:
                if img in current_images:
                    img_path = os.path.join(upload_folder, img)
                    if os.path.exists(img_path):
                        os.remove(img_path)
                    current_images.remove(img)
            property.images = current_images

        db.session.commit()
        flash('Property updated.', 'success')
        return redirect(url_for('property_mgmt.property_list'))

    return render_template('property_mgmt/property_form.html', form=form, property=property, title='Edit Property')

# ------------------------------
# Delete Property
# ------------------------------

@property_mgmt_bp.route('/<property_id>/delete', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_property(property_id):
    property = Property.query.get_or_404(property_id)
    # Delete image files
    if property.images:
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'properties')
        for img in property.images:
            img_path = os.path.join(upload_folder, img)
            if os.path.exists(img_path):
                os.remove(img_path)
    db.session.delete(property)
    db.session.commit()
    flash('Property deleted.', 'success')
    return redirect(url_for('property_mgmt.property_list'))

# ------------------------------
# Property Detail (for admin view)
# ------------------------------

@property_mgmt_bp.route('/<property_id>')
@login_required
@role_required(['admin', 'staff'])
def property_detail(property_id):
    property = Property.query.get_or_404(property_id)
    sales = Sale.query.filter_by(property_id=property.id).all()
    return render_template('property_mgmt/property_detail.html', property=property, sales=sales)

# ------------------------------
# Plot Allocation (assign to customer via Sale)
# ------------------------------

@property_mgmt_bp.route('/<property_id>/allocate', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'staff'])
def allocate_plot(property_id):
    property = Property.query.get_or_404(property_id)
    if getattr(property.status, 'value', property.status) != 'available':
        flash('Property is not available for allocation.', 'danger')
        return redirect(url_for('property_mgmt.property_detail', property_id=property.id))

    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        customer = User.query.get_or_404(customer_id)
        if getattr(customer.role, 'value', customer.role) != 'customer':
            flash('Selected user is not a customer.', 'danger')
            return render_template('property_mgmt/allocate.html', property=property)

        # Create sale (pending)
        sale = Sale(
            customer_id=customer.id,
            property_id=property.id,
            staff_id=current_user.id,
            total_amount=property.price,
            amount_paid=0,
            balance=property.price,
            status='pending',
            is_installment=False
        )
        property.status = 'reserved'  # Mark as reserved
        db.session.add(sale)
        db.session.commit()
        flash('Property allocated to customer. Sale record created.', 'success')
        return redirect(url_for('property_mgmt.property_detail', property_id=property.id))

    # GET: show customer search form
    return render_template('property_mgmt/allocate.html', property=property)

# ------------------------------
# Reports
# ------------------------------

@property_mgmt_bp.route('/reports')
@login_required
@role_required(['admin', 'staff'])
def reports():
    # Available properties
    available = Property.query.filter_by(status='available').all()
    sold_properties = Property.query.filter_by(status='sold').all()
    # Revenue summary
    total_revenue = db.session.query(func.sum(Sale.total_amount)).scalar() or 0
    revenue_by_estate = db.session.query(Property.estate, func.sum(Sale.total_amount)).join(Sale).group_by(Property.estate).all()
    return render_template('property_mgmt/reports.html',
                           available=available,
                           sold_properties=sold_properties,
                           total_revenue=total_revenue,
                           revenue_by_estate=revenue_by_estate)

# ------------------------------
# Analytics (JSON for charts)
# ------------------------------

@property_mgmt_bp.route('/analytics/data')
@login_required
@role_required(['admin', 'staff'])
def analytics_data():
    # Status distribution
    status_counts = db.session.query(Property.status, func.count(Property.id)).group_by(Property.status).all()
    status_labels = [s.value for s, _ in status_counts]
    status_values = [count for _, count in status_counts]

    # Monthly sales (last 12 months)
    months = []
    sales_counts = []
    for i in range(12):
        month_start = datetime.now(timezone.utc).replace(day=1, month=datetime.now(timezone.utc).month - i) if i > 0 else datetime.now(timezone.utc).replace(day=1)
        month_end = month_start.replace(day=1, month=month_start.month+1) - timedelta(days=1)
        count = Sale.query.filter(Sale.sale_date >= month_start, Sale.sale_date <= month_end).count()
        months.append(month_start.strftime('%b %Y'))
        sales_counts.append(count)
    months.reverse()
    sales_counts.reverse()

    return jsonify({
        'status_labels': status_labels,
        'status_values': status_values,
        'months': months,
        'sales_counts': sales_counts
    })
    
