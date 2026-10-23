from flask import Blueprint, render_template, request
from app.models.audit import AuditLog
from app.utils.decorators import login_required, role_required

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')


@audit_bp.route('/', strict_slashes=False)
@audit_bp.route('', strict_slashes=False)
@login_required
@role_required('admin')
def index():
    action = request.args.get('action', '').strip()
    username = request.args.get('username', '').strip()

    query = AuditLog.query
    if action:
        query = query.filter(AuditLog.action == action)
    if username:
        query = query.filter(AuditLog.username.ilike(f'%{username}%'))

    logs = query.order_by(AuditLog.created_at.desc()).limit(150).all()
    actions = sorted(list(set(l.action for l in AuditLog.query.all())))

    return render_template(
        'audit/index.html',
        logs=logs,
        actions=actions,
        selected_action=action,
        search_username=username
    )
