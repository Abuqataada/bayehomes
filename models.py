import uuid
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from sqlalchemy import CheckConstraint

# Helper to generate UUID strings
def generate_uuid():
    return str(uuid.uuid4())

# ============================
# VALID VALUES (as constants, for reference)
# ============================

class UserRole:
    ADMIN = 'admin'
    STAFF = 'staff'
    CUSTOMER = 'customer'
    ALL = (ADMIN, STAFF, CUSTOMER)

class PropertyStatus:
    AVAILABLE = 'available'
    RESERVED = 'reserved'
    SOLD = 'sold'
    UNDER_DEVELOPMENT = 'under_development'
    ALL = (AVAILABLE, RESERVED, SOLD, UNDER_DEVELOPMENT)

class LeadStatus:
    NEW = 'new'
    CONTACTED = 'contacted'
    FOLLOW_UP = 'follow_up'
    NEGOTIATION = 'negotiation'
    CONVERTED = 'converted'
    CLOSED = 'closed'
    ALL = (NEW, CONTACTED, FOLLOW_UP, NEGOTIATION, CONVERTED, CLOSED)

class LeadSource:
    WEBSITE_CONTACT = 'website_contact'
    PROPERTY_INQUIRY = 'property_inquiry'
    WHATSAPP = 'whatsapp'
    INVESTMENT_REQUEST = 'investment_request'
    ALL = (WEBSITE_CONTACT, PROPERTY_INQUIRY, WHATSAPP, INVESTMENT_REQUEST)

class PaymentStatus:
    PENDING = 'pending'
    VERIFIED = 'verified'
    FAILED = 'failed'
    ALL = (PENDING, VERIFIED, FAILED)

class InvestmentStatus:
    ACTIVE = 'active'
    COMPLETED = 'completed'
    DEFAULTED = 'defaulted'
    ALL = (ACTIVE, COMPLETED, DEFAULTED)

class StaffDepartment:
    SALES = 'sales'
    MARKETING = 'marketing'
    OPERATIONS = 'operations'
    ADMIN = 'administration'
    LEGAL = 'legal'
    ALL = (SALES, MARKETING, OPERATIONS, ADMIN, LEGAL)

class DocumentType:
    DEED = 'deed'
    SURVEY = 'survey'
    BUILDING_PLAN = 'building_plan'
    PERMIT = 'permit'
    RECEIPT = 'receipt'
    OTHER = 'other'
    ALL = (DEED, SURVEY, BUILDING_PLAN, PERMIT, RECEIPT, OTHER)

# ============================
# USER
# ============================

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='customer')  # values: admin, staff, customer
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True)
    reset_token = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    profile = db.relationship('Profile', backref='user', uselist=False)
    saved_properties = db.relationship('SavedProperty', backref='customer', lazy='dynamic')
    property_inquiries = db.relationship('PropertyInquiry', backref='customer', lazy='dynamic')
    sales = db.relationship('Sale', foreign_keys='Sale.customer_id', backref='customer', lazy='dynamic')
    leads_assigned = db.relationship('Lead', foreign_keys='Lead.assigned_to', backref='staff_user')
    investments = db.relationship('Investment', foreign_keys='Investment.investor_id', backref='investor', lazy='dynamic')
    staff_profile = db.relationship('StaffProfile', foreign_keys='StaffProfile.user_id', backref='user', uselist=False)
    activity_logs = db.relationship('ActivityLog', backref='user', lazy='dynamic')

    # Constraints
    __table_args__ = (
        CheckConstraint(role.in_(UserRole.ALL), name='check_user_role'),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or self.username or self.email

    def is_admin_user(self):
        return self.role == UserRole.ADMIN

    def is_staff_user(self):
        return self.role in (UserRole.ADMIN, UserRole.STAFF)

    def is_customer(self):
        return self.role == UserRole.CUSTOMER

    def __repr__(self):
        return f'<User {self.email}>'


class Profile(db.Model):
    __tablename__ = 'profiles'

    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), primary_key=True)
    avatar_url = db.Column(db.String(255))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Nigeria')
    bio = db.Column(db.Text)


# ============================
# STAFF (legacy, kept for compatibility)
# ============================

class Staff(db.Model):
    __tablename__ = 'staff'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    designation = db.Column(db.String(256), nullable=False)
    state_of_origin = db.Column(db.String(30), nullable=False)
    qualification = db.Column(db.String(256), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f'<Staff {self.email}>'


# ============================
# PROPERTIES
# ============================

class Property(db.Model):
    __tablename__ = 'properties'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    property_type = db.Column(db.String(20), nullable=False)  # 'land' or 'building'
    estate = db.Column(db.String(100))
    plot_number = db.Column(db.String(50))
    size_sqm = db.Column(db.Numeric(10, 2))
    price = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), default='Abuja')
    state = db.Column(db.String(100), default='FCT')
    bedrooms = db.Column(db.Integer)
    bathrooms = db.Column(db.Integer)
    status = db.Column(db.String(20), default='available')  # available, reserved, sold, under_development
    images = db.Column(db.JSON)
    documents = db.Column(db.JSON)
    featured = db.Column(db.Boolean, default=False)
    latitude = db.Column(db.Numeric(10, 7))
    longitude = db.Column(db.Numeric(10, 7))
    assigned_staff_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    inquiries = db.relationship('PropertyInquiry', backref='property', lazy='dynamic')
    sales = db.relationship('Sale', backref='property', lazy='dynamic')
    investments = db.relationship('Investment', backref='property', lazy='dynamic')
    assigned_staff = db.relationship('User', foreign_keys=[assigned_staff_id], backref='managed_properties')

    # Constraints
    __table_args__ = (
        CheckConstraint(property_type.in_(('land', 'building')), name='check_property_type'),
        CheckConstraint(status.in_(PropertyStatus.ALL), name='check_property_status'),
    )

    def get_primary_image(self):
        return self.images[0] if self.images else 'placeholder.jpg'

    def __repr__(self):
        return f'<Property {self.title}>'


class SavedProperty(db.Model):
    __tablename__ = 'saved_properties'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    property_id = db.Column(db.String(36), db.ForeignKey('properties.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('user_id', 'property_id', name='unique_saved'),)


class PropertyInquiry(db.Model):
    __tablename__ = 'property_inquiries'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    property_id = db.Column(db.String(36), db.ForeignKey('properties.id'), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, responded, closed
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint(status.in_(('pending', 'responded', 'closed')), name='check_inquiry_status'),
    )


# ============================
# TESTIMONIALS
# ============================

class Testimonial(db.Model):
    __tablename__ = 'testimonials'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    client_name = db.Column(db.String(100), nullable=False)
    client_role = db.Column(db.String(100))
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))


# ============================
# BLOG POSTS
# ============================

class BlogPost(db.Model):
    __tablename__ = 'blog_posts'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    excerpt = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100))
    image = db.Column(db.String(255))
    views = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


# ============================
# CONTACT MESSAGES
# ============================

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))


# ============================
# LEADS & CRM
# ============================

class Lead(db.Model):
    __tablename__ = 'leads'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    source = db.Column(db.String(30), default='website_contact')
    status = db.Column(db.String(30), default='new')
    message = db.Column(db.Text)
    assigned_to = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    converted_to_customer = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    notes = db.relationship('LeadNote', backref='lead', lazy='dynamic')
    reminders = db.relationship('FollowUpReminder', backref='lead', lazy='dynamic')
    converted_customer = db.relationship('User', foreign_keys=[converted_to_customer], backref='converted_leads')

    __table_args__ = (
        CheckConstraint(source.in_(LeadSource.ALL), name='check_lead_source'),
        CheckConstraint(status.in_(LeadStatus.ALL), name='check_lead_status'),
    )


class LeadNote(db.Model):
    __tablename__ = 'lead_notes'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    lead_id = db.Column(db.String(36), db.ForeignKey('leads.id'), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))


class FollowUpReminder(db.Model):
    __tablename__ = 'follow_up_reminders'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    lead_id = db.Column(db.String(36), db.ForeignKey('leads.id'), nullable=False)
    reminder_date = db.Column(db.DateTime, nullable=False)
    note = db.Column(db.Text)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))


# ============================
# SALES & PAYMENTS
# ============================

class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    customer_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    property_id = db.Column(db.String(36), db.ForeignKey('properties.id'), nullable=False)
    staff_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(15, 2), default=0)
    balance = db.Column(db.Numeric(15, 2))
    sale_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='pending')  # pending, completed, defaulted
    is_installment = db.Column(db.Boolean, default=False)
    installment_plan = db.Column(db.JSON)

    # Relationships
    payments = db.relationship('Payment', backref='sale', lazy='dynamic')
    receipts = db.relationship('Receipt', backref='sale', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='sale', lazy='dynamic')
    documents = db.relationship('Document', backref='sale', lazy='dynamic')

    __table_args__ = (
        CheckConstraint(status.in_(('pending', 'completed', 'defaulted')), name='check_sale_status'),
    )


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    sale_id = db.Column(db.String(36), db.ForeignKey('sales.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    method = db.Column(db.String(20), nullable=False)  # cash, transfer, card
    reference = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')  # pending, verified, failed
    verified_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime)

    __table_args__ = (
        CheckConstraint(method.in_(('cash', 'transfer', 'card')), name='check_payment_method'),
        CheckConstraint(status.in_(PaymentStatus.ALL), name='check_payment_status'),
    )


class Receipt(db.Model):
    __tablename__ = 'receipts'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    sale_id = db.Column(db.String(36), db.ForeignKey('sales.id'), nullable=False)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    file_url = db.Column(db.String(255))


class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    sale_id = db.Column(db.String(36), db.ForeignKey('sales.id'), nullable=False)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    issued_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    due_date = db.Column(db.DateTime)
    total = db.Column(db.Numeric(15, 2), nullable=False)
    balance_due = db.Column(db.Numeric(15, 2))
    status = db.Column(db.String(20), default='unpaid')  # unpaid, paid, overdue

    __table_args__ = (
        CheckConstraint(status.in_(('unpaid', 'paid', 'overdue')), name='check_invoice_status'),
    )


# ============================
# INVESTMENT MANAGEMENT
# ============================

class InvestmentPackage(db.Model):
    __tablename__ = 'investment_packages'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    min_amount = db.Column(db.Numeric(15, 2), nullable=False)
    max_amount = db.Column(db.Numeric(15, 2))
    expected_roi = db.Column(db.Numeric(5, 2))
    duration_months = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))


class Investment(db.Model):
    __tablename__ = 'investments'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    investor_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    property_id = db.Column(db.String(36), db.ForeignKey('properties.id'), nullable=True)
    package_id = db.Column(db.String(36), db.ForeignKey('investment_packages.id'), nullable=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    end_date = db.Column(db.DateTime)
    roi_earned = db.Column(db.Numeric(15, 2), default=0)
    status = db.Column(db.String(20), default='active')  # active, completed, defaulted
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships
    roi_transactions = db.relationship('ROITransaction', backref='investment', lazy='dynamic')

    __table_args__ = (
        CheckConstraint(status.in_(InvestmentStatus.ALL), name='check_investment_status'),
    )


class ROITransaction(db.Model):
    __tablename__ = 'roi_transactions'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    investment_id = db.Column(db.String(36), db.ForeignKey('investments.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    note = db.Column(db.Text)


# ============================
# STAFF MANAGEMENT
# ============================

class StaffProfile(db.Model):
    __tablename__ = 'staff_profiles'

    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), primary_key=True)
    staff_id = db.Column(db.String(20), unique=True)
    department = db.Column(db.String(30), default='sales')
    role = db.Column(db.String(50))
    hire_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    phone_extension = db.Column(db.String(10))
    reports_to = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)

    # Self reference for hierarchy
    subordinates = db.relationship('User', foreign_keys=[reports_to], remote_side='User.id')

    __table_args__ = (
        CheckConstraint(department.in_(StaffDepartment.ALL), name='check_staff_department'),
    )


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))


class StaffDailyReport(db.Model):
    __tablename__ = 'staff_daily_reports'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    staff_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    leads_contacted = db.Column(db.Integer, default=0)
    site_visits = db.Column(db.Integer, default=0)
    sales_closed = db.Column(db.Integer, default=0)
    challenges = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    staff = db.relationship('User', foreign_keys=[staff_id], backref='daily_reports')


class StaffDevice(db.Model):
    __tablename__ = 'staff_devices'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    staff_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    device_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    staff = db.relationship('User', foreign_keys=[staff_id], backref='staff_devices')

    def __repr__(self):
        return f'<StaffDevice device_id={self.device_id}>'


class StaffAttendanceRecord(db.Model):
    __tablename__ = 'staff_attendance_records'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    staff_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default='present')
    check_in = db.Column(db.String(20))
    check_out = db.Column(db.String(20))
    source_file = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    staff = db.relationship('User', foreign_keys=[staff_id], backref='attendance_records')


class StaffRating(db.Model):
    __tablename__ = 'staff_ratings'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    staff_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    period_type = db.Column(db.String(20), nullable=False)
    period_label = db.Column(db.String(20), nullable=False)
    attendance_score = db.Column(db.Numeric(5, 2), default=0)
    reporting_score = db.Column(db.Numeric(5, 2), default=0)
    sales_score = db.Column(db.Numeric(5, 2), default=0)
    total_score = db.Column(db.Numeric(5, 2), default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    staff = db.relationship('User', foreign_keys=[staff_id], backref='ratings')


class StaffChatMessage(db.Model):
    __tablename__ = 'staff_chat_messages'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    sender_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_staff_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_staff_messages')


class StaffNotification(db.Model):
    __tablename__ = 'staff_notifications'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    creator = db.relationship('User', foreign_keys=[created_by], backref='created_staff_notifications')


class StaffNotificationRead(db.Model):
    __tablename__ = 'staff_notification_reads'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    notification_id = db.Column(db.String(36), db.ForeignKey('staff_notifications.id'), nullable=False)
    staff_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    notification = db.relationship('StaffNotification', backref='reads')
    staff = db.relationship('User', foreign_keys=[staff_id], backref='notification_reads')

    __table_args__ = (db.UniqueConstraint('notification_id', 'staff_id', name='unique_notification_read'),)


# ============================
# DOCUMENTS
# ============================

class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    sale_id = db.Column(db.String(36), db.ForeignKey('sales.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(30), default='other')
    uploaded_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    uploaded_by = db.Column(db.String(36), db.ForeignKey('users.id'))

    __table_args__ = (
        CheckConstraint(document_type.in_(DocumentType.ALL), name='check_document_type'),
    )
    
    