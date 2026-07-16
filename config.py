import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///bayehomes.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        "pool_pre_ping": True,
        "connect_args": {
        "ssl": {}
        }
    }
    
    WTF_CSRF_ENABLED = False
    
    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
    
    # Upload folders
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/uploads/properties')
    BLOG_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/uploads/blog')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Mail configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Meta API Configuration
    META_ACCESS_TOKEN = os.environ.get('META_ACCESS_TOKEN', '')
    META_PAGE_ID = os.environ.get('META_PAGE_ID', '')
    META_INSTAGRAM_BUSINESS_ID = os.environ.get('META_INSTAGRAM_BUSINESS_ID', '')
    META_API_VERSION = 'v18.0'
    