from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, BooleanField, IntegerField, DateField, StringField
from wtforms.validators import DataRequired, NumberRange, Optional
from models import User, Property

class SaleForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=str, validators=[DataRequired()])
    property_id = SelectField('Property', coerce=str, validators=[DataRequired()])
    total_amount = DecimalField('Total Amount (₦)', validators=[DataRequired(), NumberRange(min=0)])
    is_installment = BooleanField('Installment Plan')
    down_payment_percent = IntegerField('Down Payment (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    months = IntegerField('Installment Months', validators=[Optional(), NumberRange(min=1)])
    sale_date = DateField('Sale Date', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer_id.choices = [(str(u.id), u.get_full_name()) for u in User.query.filter_by(role='customer').all()]
        self.property_id.choices = [(str(p.id), f"{p.title} - {p.location}") for p in Property.query.filter_by(status='available').all()]

class PaymentForm(FlaskForm):
    amount = DecimalField('Amount (₦)', validators=[DataRequired(), NumberRange(min=0)])
    method = SelectField('Payment Method', choices=[('cash', 'Cash'), ('transfer', 'Bank Transfer'), ('card', 'Card')], validators=[DataRequired()])
    reference = StringField('Reference (optional)')

class SalesFilterForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=str, choices=[('', 'All')])
    property_id = SelectField('Property', coerce=str, choices=[('', 'All')])
    status = SelectField('Status', choices=[('', 'All'), ('pending', 'Pending'), ('completed', 'Completed'), ('defaulted', 'Defaulted')])
    start_date = DateField('From', validators=[Optional()])
    end_date = DateField('To', validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer_id.choices += [(str(u.id), u.get_full_name()) for u in User.query.filter_by(role='customer').all()]
        self.property_id.choices += [(str(p.id), p.title) for p in Property.query.all()]
        
