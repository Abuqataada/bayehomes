import uuid
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Message
from models import db, User, UserRole
from forms.auth_forms import RegistrationForm, LoginForm, PasswordResetRequestForm, PasswordResetForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# ------------------------------
# Helper: send email
# ------------------------------
def send_email(subject, recipients, body):
    msg = Message(subject=subject, recipients=recipients)
    msg.body = body
    current_app.extensions['mail'].send(msg)

def send_verification_email(user):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = serializer.dumps(user.email, salt='email-verify')
    verification_url = url_for('auth.verify_email', token=token, _external=True)
    body = f'''Welcome to Baye Homes!

Please click the following link to verify your email address:
{verification_url}

If you did not create an account, please ignore this email.
'''
    send_email('Verify your email address', [user.email], body)

def send_password_reset_email(user):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = serializer.dumps(user.email, salt='password-reset')
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    body = f'''To reset your password, click the link below:
{reset_url}

If you did not request this, please ignore this email.
'''
    send_email('Reset your password', [user.email], body)

# ------------------------------
# Registration
# ------------------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('customer.dashboard' if current_user.role == UserRole.CUSTOMER else 'staff.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.email.data.split('@')[0],  # fallback username
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role=UserRole.CUSTOMER,
            is_active=True,
            email_verified=False
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        send_verification_email(user)
        flash('Registration successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

# ------------------------------
# Email Verification
# ------------------------------
@auth_bp.route('/verify/<token>')
def verify_email(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-verify', max_age=86400)  # 1 day
    except (SignatureExpired, BadSignature):
        flash('The verification link is invalid or expired.', 'danger')
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(email=email).first()
    if user:
        user.email_verified = True
        db.session.commit()
        flash('Your email has been verified. You can now log in.', 'success')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('auth.login'))

@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
@login_required
def resend_verification():
    if current_user.email_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('customer.dashboard' if current_user.role == UserRole.CUSTOMER else 'staff.dashboard'))
    send_verification_email(current_user)
    flash('A new verification link has been sent to your email.', 'success')
    return redirect(request.referrer or url_for('customer.dashboard'))

# ------------------------------
# Login / Logout
# ------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('customer.dashboard' if current_user.role == UserRole.CUSTOMER else 'staff.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            if not user.email_verified:
                flash('Please verify your email address to access all features.', 'warning')
            # Redirect based on role
            if user.is_customer():
                return redirect(next_page or url_for('customer.dashboard'))
            else:
                return redirect(next_page or url_for('staff.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.home'))

# ------------------------------
# Password Reset
# ------------------------------
@auth_bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('customer.dashboard' if current_user.role == UserRole.CUSTOMER else 'staff.dashboard'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash('A password reset link has been sent to your email.', 'success')
        else:
            flash('No account with that email address.', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('customer.dashboard' if current_user.role == UserRole.CUSTOMER else 'staff.dashboard'))
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)  # 1 hour
    except (SignatureExpired, BadSignature):
        flash('The password reset link is invalid or expired.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(form.password.data)
            db.session.commit()
            flash('Your password has been reset. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('User not found.', 'danger')
    return render_template('auth/reset_password.html', form=form, token=token)

