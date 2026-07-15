from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TextAreaField, SelectField, DateTimeField
from wtforms.validators import DataRequired, Email, Length, Optional
from models import LeadStatus, LeadSource, User

class LeadFilterForm(FlaskForm):
    status = SelectField('Status', choices=[('', 'All')] + [(s.value, s.value.replace('_', ' ').title()) for s in LeadStatus], coerce=str)
    source = SelectField('Source', choices=[('', 'All')] + [(s.value, s.value.replace('_', ' ').title()) for s in LeadSource], coerce=str)
    assigned_to = SelectField('Assigned To', choices=[], coerce=str)
    search = StringField('Search', validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        staff = User.query.filter(User.role.in_(['admin', 'staff'])).all()
        self.assigned_to.choices = [('', 'Unassigned')] + [(str(u.id), u.get_full_name()) for u in staff]

class LeadNoteForm(FlaskForm):
    note = TextAreaField('Note', validators=[DataRequired()])

class FollowUpReminderForm(FlaskForm):
    reminder_date = DateTimeField('Reminder Date & Time', validators=[DataRequired()], format='%Y-%m-%d %H:%M')
    note = TextAreaField('Note', validators=[Optional()])

class AssignStaffForm(FlaskForm):
    assigned_to = SelectField('Assign Staff', coerce=str, validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        staff = User.query.filter(User.role.in_(['admin', 'staff'])).all()
        self.assigned_to.choices = [(str(u.id), u.get_full_name()) for u in staff]
        
        