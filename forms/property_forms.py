from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, DecimalField, IntegerField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from models import Property, PropertyStatus, User, UserRole

class PropertyForm(FlaskForm):
    title = StringField('Property Title', validators=[DataRequired()])
    slug = StringField('Slug', validators=[Optional()])  # auto-generated if empty
    property_type = SelectField('Property Type', choices=[('land', 'Land'), ('building', 'Building')], validators=[DataRequired()])
    estate = StringField('Estate Name')
    plot_number = StringField('Plot Number')
    size_sqm = DecimalField('Size (sqm)', places=2, validators=[Optional()])
    price = DecimalField('Price (₦)', places=2, validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Description')
    location = StringField('Location', validators=[DataRequired()])
    city = StringField('City', default='Abuja')
    state = StringField('State', default='FCT')
    bedrooms = IntegerField('Bedrooms', validators=[Optional()])
    bathrooms = IntegerField('Bathrooms', validators=[Optional()])
    latitude = DecimalField('Latitude', places=7, validators=[Optional()])
    longitude = DecimalField('Longitude', places=7, validators=[Optional()])
    assigned_staff_id = SelectField('Assigned Staff', choices=[], validators=[Optional()])
    # Fix: use PropertyStatus.ALL instead of iterating over the class
    status = SelectField('Status', choices=[(s, s.replace('_', ' ').title()) for s in PropertyStatus.ALL], validators=[DataRequired()])
    featured = BooleanField('Featured Property')
    images = FileField('Upload Images', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        staff_users = User.query.filter(User.role.in_([UserRole.ADMIN, UserRole.STAFF])).order_by(User.first_name).all()
        self.assigned_staff_id.choices = [('', 'Unassigned')] + [(user.id, user.get_full_name()) for user in staff_users]

    def validate_slug(self, field):
        if field.data:
            # Check if slug is unique (except for editing)
            pass  # handled in route

class PropertyFilterForm(FlaskForm):
    # Fix: use PropertyStatus.ALL
    status = SelectField('Status', choices=[('', 'All')] + [(s, s.replace('_', ' ').title()) for s in PropertyStatus.ALL], coerce=str)
    property_type = SelectField('Type', choices=[('', 'All'), ('land', 'Land'), ('building', 'Building')])
    estate = StringField('Estate')
    search = StringField('Search')
    
    