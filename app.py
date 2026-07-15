import os
from flask import Flask
from config import Config
from extensions import db, migrate, login_manager, mail
from models import User, UserRole
from supabase_client import init_supabase, get_supabase  # new import
from blueprints.public import public_bp
from blueprints.admin import admin_bp
from blueprints.staff import staff_bp
from blueprints.users import users_bp
from blueprints.customer import customer_bp
from blueprints.crm import crm_bp
from blueprints.sales import sales_bp
from blueprints.investment import investment_bp
from blueprints.auth import auth_bp
from blueprints.property_mgmt import property_mgmt_bp
import dotenv

dotenv.load_dotenv()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Initialize Supabase
    init_supabase(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    # Register blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(customer_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(investment_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(property_mgmt_bp)
    
    # Create upload folders
    #os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    #os.makedirs(app.config['BLOG_UPLOAD_FOLDER'], exist_ok=True)
    
    return app

app = create_app()
        
        
with app.app_context():
    db.create_all()
    
    # Create admin user
    admin = User.query.filter_by(username=os.environ.get('ADMIN_USERNAME', 'admin')).first()
    if not admin:
        admin = User(
            username=os.environ.get('ADMIN_USERNAME', 'admin'),
            email=os.environ.get('ADMIN_EMAIL', 'admin@bayehomes.com'),
            first_name='Admin',
            last_name='User',
            phone='1234567890',
            role=UserRole.ADMIN,
            email_verified=True,
            is_admin=True
        )
        admin.set_password(os.environ.get('ADMIN_PASSWORD', 'admin123'))
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin user already exists.")

if __name__ == '__main__':
    app.run(debug=True)
    
    