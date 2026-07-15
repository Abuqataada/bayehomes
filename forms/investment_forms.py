from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, BooleanField, SelectField
from wtforms.validators import DataRequired, NumberRange, Optional
from models import InvestmentPackage

class PackageForm(FlaskForm):
    name = StringField('Package Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    min_amount = DecimalField('Minimum Amount (₦)', validators=[DataRequired(), NumberRange(min=0)])
    max_amount = DecimalField('Maximum Amount (₦)', validators=[Optional(), NumberRange(min=0)])
    expected_roi = DecimalField('Expected ROI (%)', validators=[DataRequired(), NumberRange(min=0)])
    duration_months = IntegerField('Duration (months)', validators=[DataRequired(), NumberRange(min=1)])
    is_active = BooleanField('Active', default=True)

class InvestmentRequestForm(FlaskForm):
    package_id = SelectField('Investment Package', coerce=str, validators=[DataRequired()])
    amount = DecimalField('Amount (₦)', validators=[DataRequired(), NumberRange(min=0)])
    notes = TextAreaField('Notes', validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.package_id.choices = [(str(p.id), f"{p.name} - {p.expected_roi}% ROI") for p in InvestmentPackage.query.filter_by(is_active=True).all()]
        
