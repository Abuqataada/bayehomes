from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SelectField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo
from wtforms import ValidationError
from models import User, StaffDepartment

class StaffRegistrationForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=80)])
    phone = StringField('Phone', validators=[Length(max=20)])
    # Use StaffDepartment.ALL to get the list of values
    department = SelectField('Department', 
                             choices=[(d, d.title()) for d in StaffDepartment.ALL], 
                             validators=[DataRequired()])
    role = StringField('Job Title', validators=[Optional(), Length(max=50)])
    reports_to = SelectField('Reports To', coerce=str, validators=[Optional()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    is_active = BooleanField('Active', default=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        staff_users = User.query.filter(User.role.in_(['admin', 'staff'])).all()
        self.reports_to.choices = [('', 'None')] + [(str(u.id), u.get_full_name()) for u in staff_users]

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

class StaffEditForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=80)])
    phone = StringField('Phone', validators=[Length(max=20)])
    department = SelectField('Department', 
                             choices=[(d, d.title()) for d in StaffDepartment.ALL], 
                             validators=[DataRequired()])
    role = StringField('Job Title', validators=[Optional(), Length(max=50)])
    reports_to = SelectField('Reports To', coerce=str, validators=[Optional()])
    is_active = BooleanField('Active', default=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        staff_users = User.query.filter(User.role.in_(['admin', 'staff'])).all()
        self.reports_to.choices = [('', 'None')] + [(str(u.id), u.get_full_name()) for u in staff_users]

class StaffFilterForm(FlaskForm):
    search = StringField('Search', validators=[Optional()])
    department = SelectField('Department', 
                             choices=[('', 'All')] + [(d, d.title()) for d in StaffDepartment.ALL], 
                             validators=[Optional()])
    is_active = SelectField('Status', 
                            choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')], 
                            validators=[Optional()])
    
    