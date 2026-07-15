from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField, FileField, DateTimeField
from wtforms.validators import DataRequired, Optional, Length

class SocialMediaPostForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=2200)])
    image = FileField('Image (optional)', validators=[Optional()])
    video = FileField('Video (optional)', validators=[Optional()])
    platforms = SelectMultipleField('Post to', choices=[('facebook', 'Facebook'), ('instagram', 'Instagram')], validators=[DataRequired()])
    scheduled_time = DateTimeField('Schedule (optional)', validators=[Optional()], format='%Y-%m-%d %H:%M')