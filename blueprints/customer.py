import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Message
from models import db, User, Profile, SavedProperty, PropertyInquiry, Sale, Payment, Document, Property
from forms.customer_forms import (
    RegistrationForm, LoginForm, ProfileForm,
    PasswordResetRequestForm, PasswordResetForm
)

# Create blueprint
customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

# ------------------------------
# Helper functions
# ------------------------------

def send_verification_email(user):
    """Send email verification link to the user."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = serializer.dumps(user.email, salt='email-verify')
    verification_url = url_for('customer.verify_email', token=token, _external=True)
    msg = Message('Verify your email address', recipients=[user.email])
    msg.body = f'''Welcome to Baye Homes!

Please click the following link to verify your email address:
{verification_url}

If you did not create an account, please ignore this email.
'''
    current_app.extensions['mail'].send(msg)

def send_password_reset_email(user):
    """Send password reset link."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = serializer.dumps(user.email, salt='password-reset')
    reset_url = url_for('customer.reset_password', token=token, _external=True)
    msg = Message('Reset your password', recipients=[user.email])
    msg.body = f'''To reset your password, click the link below:
{reset_url}

If you did not request this, please ignore this email.
'''
    current_app.extensions['mail'].send(msg)

def save_avatar(file):
    """Save uploaded avatar and return file path."""
    if not file:
        return None
    filename = secure_filename(file.filename)
    # Generate unique name to avoid collisions
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)
    return f'uploads/avatars/{unique_name}'

def delete_old_avatar(user):
    """Delete old avatar file if exists."""
    if user.profile and user.profile.avatar_url:
        old_path = os.path.join(current_app.root_path, 'static', user.profile.avatar_url)
        if os.path.exists(old_path):
            os.remove(old_path)

# ------------------------------
# Authentication routes
# ------------------------------

@customer_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('customer.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role='customer'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        # Send verification email
        send_verification_email(user)
        flash('Registration successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('customer.login'))
    return render_template('customer/register.html', form=form)

@customer_bp.route('/verify/<token>')
def verify_email(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-verify', max_age=86400)  # 1 day
    except (SignatureExpired, BadSignature):
        flash('The verification link is invalid or expired.', 'danger')
        return redirect(url_for('customer.login'))
    user = User.query.filter_by(email=email).first()
    if user:
        user.email_verified = True
        db.session.commit()
        flash('Your email has been verified. You can now log in.', 'success')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('customer.login'))

@customer_bp.route('/resend-verification', methods=['POST'])
@login_required
def resend_verification():
    if current_user.email_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('customer.dashboard'))
    send_verification_email(current_user)
    flash('A new verification link has been sent to your email.', 'success')
    return redirect(url_for('customer.dashboard'))

@customer_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('customer.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            if not user.email_verified:
                flash('Please verify your email address to access all features.', 'warning')
            return redirect(next_page) if next_page else redirect(url_for('customer.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('customer/login.html', form=form)

@customer_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.home'))

@customer_bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('customer.dashboard'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash('A password reset link has been sent to your email.', 'success')
        else:
            flash('No account with that email address.', 'danger')
        return redirect(url_for('customer.login'))
    return render_template('customer/reset_password_request.html', form=form)

@customer_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('customer.dashboard'))
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)  # 1 hour
    except (SignatureExpired, BadSignature):
        flash('The password reset link is invalid or expired.', 'danger')
        return redirect(url_for('customer.reset_password_request'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(form.password.data)
            db.session.commit()
            flash('Your password has been reset. Please log in.', 'success')
            return redirect(url_for('customer.login'))
        else:
            flash('User not found.', 'danger')
    return render_template('customer/reset_password.html', form=form, token=token)

# ------------------------------
# Dashboard & Profile
# ------------------------------

@customer_bp.route('/dashboard')
@login_required
def dashboard():
    user = current_user
    saved = user.saved_properties.count()
    inquiries = user.property_inquiries.count()
    purchases = user.sales.filter_by(status='completed').count()
    # Get recent payments (last 5)
    payments = Payment.query.join(Sale).filter(Sale.customer_id == user.id)\
                              .order_by(Payment.payment_date.desc()).limit(5).all()
    return render_template('customer/dashboard.html',
                           saved=saved, inquiries=inquiries, purchases=purchases,
                           payments=payments, user=user)

@customer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = current_user
    form = ProfileForm(obj=user)
    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.phone = form.phone.data
        # Update profile
        if not user.profile:
            user.profile = Profile(user_id=user.id)
        user.profile.address = form.address.data
        user.profile.city = form.city.data
        user.profile.state = form.state.data
        user.profile.country = form.country.data or 'Nigeria'
        # Avatar upload
        if form.avatar.data:
            # Delete old avatar
            delete_old_avatar(user)
            new_avatar = save_avatar(form.avatar.data)
            user.profile.avatar_url = new_avatar
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('customer.profile'))
    # Pre-fill form with existing data
    if user.profile:
        form.address.data = user.profile.address
        form.city.data = user.profile.city
        form.state.data = user.profile.state
        form.country.data = user.profile.country
    return render_template('customer/profile.html', form=form, user=user)

# ------------------------------
# Saved Properties
# ------------------------------

@customer_bp.route('/saved-properties')
@login_required
def saved_properties():
    saved = current_user.saved_properties.order_by(SavedProperty.saved_at.desc()).all()
    return render_template('customer/saved_properties.html', saved=saved)

@customer_bp.route('/property/<property_id>/save', methods=['POST'])
@login_required
def toggle_save_property(property_id):
    property = Property.query.get_or_404(property_id)
    saved = SavedProperty.query.filter_by(user_id=current_user.id, property_id=property.id).first()
    if saved:
        db.session.delete(saved)
        flash('Property removed from saved list.', 'info')
    else:
        new_saved = SavedProperty(user_id=current_user.id, property_id=property.id)
        db.session.add(new_saved)
        flash('Property saved successfully.', 'success')
    db.session.commit()
    return redirect(request.referrer or url_for('public.property_detail', slug=property.slug))

# ------------------------------
# Property Inquiries
# ------------------------------

@customer_bp.route('/inquiries')
@login_required
def inquiries():
    inquiries = current_user.property_inquiries.order_by(PropertyInquiry.created_at.desc()).all()
    return render_template('customer/inquiries.html', inquiries=inquiries)

@customer_bp.route('/property/<property_id>/inquiry', methods=['POST'])
@login_required
def submit_inquiry(property_id):
    property = Property.query.get_or_404(property_id)
    message = request.form.get('message', '').strip()
    if not message:
        flash('Please enter a message.', 'danger')
        return redirect(request.referrer or url_for('public.property_detail', slug=property.slug))
    inquiry = PropertyInquiry(user_id=current_user.id, property_id=property.id, message=message)
    db.session.add(inquiry)
    db.session.commit()
    flash('Your inquiry has been submitted. We will get back to you soon.', 'success')
    return redirect(request.referrer or url_for('public.property_detail', slug=property.slug))

# ------------------------------
# Purchased Properties
# ------------------------------

@customer_bp.route('/purchases')
@login_required
def purchases():
    sales = current_user.sales.order_by(Sale.sale_date.desc()).all()
    return render_template('customer/purchases.html', sales=sales)

# ------------------------------
# Payment History
# ------------------------------

@customer_bp.route('/payments')
@login_required
def payments():
    payments = Payment.query.join(Sale).filter(Sale.customer_id == current_user.id)\
                            .order_by(Payment.payment_date.desc()).all()
    return render_template('customer/payments.html', payments=payments)

# ------------------------------
# Document Downloads
# ------------------------------

@customer_bp.route('/documents/<document_id>/download')
@login_required
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    # Check if document belongs to a sale of the current user
    if document.sale.customer_id != current_user.id:
        abort(403)  # Forbidden
    # Serve file
    file_path = os.path.join(current_app.root_path, 'static', document.file_path)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path),
                               as_attachment=True)
    
