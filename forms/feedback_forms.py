from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TextAreaField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional

class VisitorFeedbackForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired(), Length(max=100)])
    email = EmailField('Email (optional)', validators=[Optional(), Email(), Length(max=120)])
    message = TextAreaField('Feedback / Message', validators=[DataRequired(), Length(max=2000)])
    rating = IntegerField('Rating', validators=[Optional(), NumberRange(min=1, max=5)], default=5)
    page_url = HiddenField()
    page_title = HiddenField()
    
    