from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.models.user import User
from app.utils.decorators import login_user, logout_user, login_required, get_current_user
from app.services.audit_service import AuditService

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                return render_template('auth/login.html')

            login_user(user)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            AuditService.log(
                action='LOGIN',
                resource_type='User',
                resource_id=user.username,
                details=f"Successful authentication for {user.username} ({user.role})",
                user=user
            )

            flash(f'Welcome back, {user.full_name} ({user.role.title()})!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            AuditService.log(
                action='FAILED_LOGIN_ATTEMPT',
                resource_type='User',
                resource_id=username,
                details=f"Failed login attempt for username '{username}'"
            )
            flash('Invalid username or password. Please verify credentials.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    user = get_current_user()
    if user:
        AuditService.log(
            action='LOGOUT',
            resource_type='User',
            resource_id=user.username,
            details=f"User {user.username} logged out",
            user=user
        )
    logout_user()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    user = get_current_user()
    recent_activity = user.audit_logs.order_by(user.audit_logs.column_descriptions[0]['entity'].created_at.desc()).limit(10).all() if hasattr(user, 'audit_logs') else []
    return render_template('auth/profile.html', user=user, recent_activity=recent_activity)


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    user = get_current_user()
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm_pw = request.form.get('confirm_password', '')

    if not user.check_password(current_pw):
        flash('Current password verification failed.', 'danger')
        return redirect(url_for('auth.profile'))

    if len(new_pw) < 8:
        flash('New password must be at least 8 characters long.', 'danger')
        return redirect(url_for('auth.profile'))

    if new_pw != confirm_pw:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('auth.profile'))

    user.set_password(new_pw)
    db.session.commit()

    AuditService.log(
        action='PASSWORD_CHANGE',
        resource_type='User',
        resource_id=user.username,
        details="User updated their account password",
        user=user
    )

    flash('Your password has been changed successfully.', 'success')
    return redirect(url_for('auth.profile'))
