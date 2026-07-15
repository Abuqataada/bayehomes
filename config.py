import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'licwjrkhxwlezdqx*&^%&^@#@&^#$%#$#&@mr24uirey4n2uwnejkrhxwUICRNHIERUUUYN7824526wkrhc4nr87y34oct38nti3ry7xn3ceygfi3r8')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///bayehomes.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/uploads/properties')
    BLOG_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/uploads/blog')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    MAIL_SERVER = 'smtp.gmail.com'  # or your SMTP
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Meta API Configuration
    META_ACCESS_TOKEN = os.environ.get('META_ACCESS_TOKEN', '')  # Long-lived Page Access Token
    META_PAGE_ID = os.environ.get('META_PAGE_ID', '')           # Facebook Page ID
    META_INSTAGRAM_BUSINESS_ID = os.environ.get('META_INSTAGRAM_BUSINESS_ID', '')  # Instagram Business Account ID
    META_API_VERSION = 'v18.0'  # Use latest stable version
    