import os
from flask import Flask, app
from config import Config
from extensions import db, migrate, login_manager, mail
from models import User, UserRole
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
dotenv.load_dotenv()  # Load environment variables from .env file

def ensure_sqlite_schema(app):
    if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
        return
    with db.engine.connect() as conn:
        property_columns = {row[1] for row in conn.exec_driver_sql('PRAGMA table_info(properties)').fetchall()}
        property_additions = {
            'latitude': 'NUMERIC(10, 7)',
            'longitude': 'NUMERIC(10, 7)',
            'assigned_staff_id': 'VARCHAR(36)'
        }
        for column, definition in property_additions.items():
            if column not in property_columns:
                conn.exec_driver_sql(f'ALTER TABLE properties ADD COLUMN {column} {definition}')
        enum_normalizers = {
            'users': {'role': {'ADMIN': 'admin', 'STAFF': 'staff', 'CUSTOMER': 'customer'}},
            'properties': {'status': {'AVAILABLE': 'available', 'RESERVED': 'reserved', 'SOLD': 'sold', 'UNDER_DEVELOPMENT': 'under_development'}},
            'leads': {'status': {'NEW': 'new', 'CONTACTED': 'contacted', 'FOLLOW_UP': 'follow_up', 'NEGOTIATION': 'negotiation', 'CONVERTED': 'converted', 'CLOSED': 'closed'}, 'source': {'WEBSITE_CONTACT': 'website_contact', 'PROPERTY_INQUIRY': 'property_inquiry', 'WHATSAPP': 'whatsapp', 'INVESTMENT_REQUEST': 'investment_request'}},
            'payments': {'status': {'PENDING': 'pending', 'VERIFIED': 'verified', 'FAILED': 'failed'}},
            'investments': {'status': {'ACTIVE': 'active', 'COMPLETED': 'completed', 'DEFAULTED': 'defaulted'}},
            'staff_profiles': {'department': {'SALES': 'sales', 'MARKETING': 'marketing', 'OPERATIONS': 'operations', 'ADMIN': 'administration', 'LEGAL': 'legal'}},
            'documents': {'document_type': {'DEED': 'deed', 'SURVEY': 'survey', 'BUILDING_PLAN': 'building_plan', 'PERMIT': 'permit', 'RECEIPT': 'receipt', 'OTHER': 'other'}}
        }
        tables = {row[0] for row in conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for table, columns in enum_normalizers.items():
            if table not in tables:
                continue
            table_columns = {row[1] for row in conn.exec_driver_sql(f'PRAGMA table_info({table})').fetchall()}
            for column, mapping in columns.items():
                if column not in table_columns:
                    continue
                for old, new in mapping.items():
                    conn.exec_driver_sql(f'UPDATE {table} SET {column} = :new WHERE {column} = :old', {'new': new, 'old': old})
        conn.commit()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(Config)
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)  # user_id is a UUID string
    
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
    
    # Create upload folder if not exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['BLOG_UPLOAD_FOLDER'], exist_ok=True)
    
    return app

app = create_app()

with app.app_context():
    db.create_all()
    ensure_sqlite_schema(app)

    admin = User.query.filter_by(username=os.environ.get('ADMIN_USERNAME')).first()
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
    