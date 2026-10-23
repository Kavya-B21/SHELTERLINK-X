from functools import wraps
from flask import session, redirect, url_for, flash, request, abort, current_app
from app.models.user import User


def get_current_user():
    """Retrieve current logged-in user from session, or None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


def login_user(user: User):
    """Store user in session."""
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session.permanent = True


def logout_user():
    """Clear user session."""
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)


def login_required(f):
    """Decorator to require an authenticated session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        user = get_current_user()
        if not user or not user.is_active:
            logout_user()
            flash('Your account is inactive or not found. Please log in again.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """Decorator to enforce server-side Role-Based Access Control (RBAC)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('user_id'):
                flash('Please log in to perform this action.', 'warning')
                return redirect(url_for('auth.login', next=request.path))
            
            user = get_current_user()
            if not user or not user.is_active:
                logout_user()
                flash('Account not active.', 'danger')
                return redirect(url_for('auth.login'))
            
            if user.role not in allowed_roles and user.role != 'admin':
                # Log unauthorized access attempt
                from app.services.audit_service import AuditService
                AuditService.log(
                    action='UNAUTHORIZED_ACCESS_ATTEMPT',
                    resource_type='Route',
                    resource_id=request.path,
                    details=f"User '{user.username}' with role '{user.role}' attempted to access route requiring: {', '.join(allowed_roles)}",
                    user=user
                )
                current_app.logger.warning(
                    f"Forbidden access: {user.username} ({user.role}) -> {request.path}"
                )
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
