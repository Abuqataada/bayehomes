from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(allowed_roles):
    """
    Decorator to restrict access to users with specific roles.
    allowed_roles: list of UserRole enum values or strings (e.g., ['admin', 'staff'])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = getattr(current_user.role, 'value', current_user.role)
            normalized_roles = [getattr(role, 'value', role) for role in allowed_roles]
            if not current_user.is_authenticated or user_role not in normalized_roles:
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

