import uuid
import secrets
import string
import csv
from io import StringIO
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, Response
from flask_login import login_required, current_user
from flask_mail import Message
from sqlalchemy import or_
from models import db, User, Lead, LeadNote, FollowUpReminder, LeadStatus, LeadSource
from forms.crm_forms import LeadFilterForm, LeadNoteForm, FollowUpReminderForm, AssignStaffForm
from decorators import role_required

crm_bp = Blueprint('crm', __name__, url_prefix='/crm')

# ------------------------------
# Helper: Send welcome email
# ------------------------------
def send_welcome_email(user, temp_password):
    """Send welcome email with temporary password to a newly converted customer."""
    msg = Message(
        subject='Welcome to Baye Homes – Your Account Has Been Created',
        recipients=[user.email]
    )
    msg.body = f"""
Dear {user.get_full_name()},

Welcome to Baye Homes!

An account has been created for you using the information from your lead.
You can now log in to your customer portal at:

{url_for('customer.login', _external=True)}

Your temporary password is: {temp_password}

For security reasons, please change your password after your first login.

If you have any questions, feel free to contact us.

Best regards,
Baye Homes Team
"""
    current_app.extensions['mail'].send(msg)

# ------------------------------
# Lead List (with filters)
# ------------------------------

@crm_bp.route('/leads')
@login_required
@role_required(['admin', 'staff'])
def list_leads():
    form = LeadFilterForm(request.args, meta={'csrf': False})
    query = Lead.query

    if form.status.data:
        query = query.filter(Lead.status == form.status.data)
    if form.source.data:
        query = query.filter(Lead.source == form.source.data)
    if form.assigned_to.data:
        if form.assigned_to.data == '':
            query = query.filter(Lead.assigned_to.is_(None))
        else:
            query = query.filter(Lead.assigned_to == form.assigned_to.data)
    if form.search.data:
        search = f"%{form.search.data}%"
        query = query.filter(or_(Lead.name.ilike(search), Lead.email.ilike(search), Lead.phone.ilike(search)))

    leads = query.order_by(Lead.created_at.desc()).all()
    return render_template('crm/leads.html', leads=leads, form=form)

# ------------------------------
# Lead Detail
# ------------------------------

@crm_bp.route('/lead/<lead_id>')
@login_required
@role_required(['admin', 'staff'])
def lead_detail(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    note_form = LeadNoteForm()
    reminder_form = FollowUpReminderForm()
    assign_form = AssignStaffForm(obj=lead)
    return render_template('crm/lead_detail.html',
                           lead=lead,
                           note_form=note_form,
                           reminder_form=reminder_form,
                           assign_form=assign_form)

# ------------------------------
# Add Note
# ------------------------------

@crm_bp.route('/lead/<lead_id>/note', methods=['POST'])
@login_required
@role_required(['admin', 'staff'])
def add_note(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    form = LeadNoteForm()
    if form.validate_on_submit():
        note = LeadNote(lead_id=lead.id, note=form.note.data, created_by=current_user.id)
        db.session.add(note)
        db.session.commit()
        flash('Note added.', 'success')
    else:
        flash('Error adding note.', 'danger')
    return redirect(url_for('crm.lead_detail', lead_id=lead.id))

# ------------------------------
# Set Reminder
# ------------------------------

@crm_bp.route('/lead/<lead_id>/reminder', methods=['POST'])
@login_required
@role_required(['admin', 'staff'])
def set_reminder(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    form = FollowUpReminderForm()
    if form.validate_on_submit():
        reminder = FollowUpReminder(
            lead_id=lead.id,
            reminder_date=form.reminder_date.data,
            note=form.note.data
        )
        db.session.add(reminder)
        db.session.commit()
        flash('Reminder set.', 'success')
    else:
        flash('Invalid date format or missing fields.', 'danger')
    return redirect(url_for('crm.lead_detail', lead_id=lead.id))

# ------------------------------
# Mark Reminder as Completed
# ------------------------------

@crm_bp.route('/reminder/<reminder_id>/complete', methods=['POST'])
@login_required
@role_required(['admin', 'staff'])
def complete_reminder(reminder_id):
    reminder = FollowUpReminder.query.get_or_404(reminder_id)
    reminder.is_completed = True
    db.session.commit()
    flash('Reminder completed.', 'success')
    return redirect(url_for('crm.lead_detail', lead_id=reminder.lead_id))

# ------------------------------
# Assign Staff
# ------------------------------

@crm_bp.route('/lead/<lead_id>/assign', methods=['POST'])
@login_required
@role_required(['admin', 'staff'])
def assign_staff(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    form = AssignStaffForm()
    if form.validate_on_submit():
        lead.assigned_to = form.assigned_to.data
        db.session.commit()
        flash('Staff assigned.', 'success')
    else:
        flash('Error assigning staff.', 'danger')
    return redirect(url_for('crm.lead_detail', lead_id=lead.id))

# ------------------------------
# Convert Lead to Customer
# ------------------------------

@crm_bp.route('/lead/<lead_id>/convert', methods=['POST'])
@login_required
@role_required(['admin', 'staff'])
def convert_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if not lead.email:
        flash('Lead has no email address. Cannot convert.', 'danger')
        return redirect(url_for('crm.lead_detail', lead_id=lead.id))

    existing_user = User.query.filter_by(email=lead.email).first()
    if existing_user:
        flash('A user with this email already exists.', 'danger')
        return redirect(url_for('crm.lead_detail', lead_id=lead.id))

    # Generate a temporary password
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))

    # Create user
    name_parts = lead.name.split() if lead.name else ['', '']
    user = User(
        email=lead.email,
        first_name=name_parts[0] if name_parts else '',
        last_name=' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
        phone=lead.phone,
        role='customer',
        email_verified=True,
        is_active=True
    )
    user.set_password(temp_password)
    db.session.add(user)
    db.session.flush()  # get user.id

    # Update lead
    lead.converted_to_customer = user.id
    lead.status = LeadStatus.CONVERTED
    lead.assigned_to = current_user.id
    db.session.commit()

    # Send welcome email
    send_welcome_email(user, temp_password)

    flash('Lead successfully converted to customer. Welcome email sent.', 'success')
    return redirect(url_for('crm.lead_detail', lead_id=lead.id))

# ------------------------------
# Update Lead Status
# ------------------------------

@crm_bp.route('/lead/<lead_id>/status', methods=['POST'])
@login_required
@role_required(['admin', 'staff'])
def update_status(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    new_status = request.form.get('status')
    if new_status and new_status in [s.value for s in LeadStatus]:
        lead.status = new_status
        db.session.commit()
        flash('Status updated.', 'success')
    else:
        flash('Invalid status.', 'danger')
    return redirect(url_for('crm.lead_detail', lead_id=lead.id))

# ------------------------------
# Export Leads (CSV)
# ------------------------------

@crm_bp.route('/leads/export')
@login_required
@role_required(['admin', 'staff'])
def export_leads():
    leads = Lead.query.all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Source', 'Status', 'Assigned To', 'Created'])
    for lead in leads:
        assigned = User.query.get(lead.assigned_to)
        writer.writerow([
            lead.id,
            lead.name,
            lead.email,
            lead.phone,
            lead.source.value,
            lead.status.value,
            assigned.get_full_name() if assigned else '',
            lead.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=leads.csv'})
    
    