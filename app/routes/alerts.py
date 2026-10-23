from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.alert import OperationalAlert
from app.services.alert_service import AlertService
from app.utils.decorators import login_required, role_required, get_current_user

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alerts')


@alerts_bp.route('/', strict_slashes=False)
@alerts_bp.route('', strict_slashes=False)
@login_required
def index():
    severity = request.args.get('severity', '').strip()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', 'unack').strip()  # 'unack', 'ack', 'all'

    query = OperationalAlert.query
    if severity:
        query = query.filter(OperationalAlert.severity == severity)
    if category:
        query = query.filter(OperationalAlert.category == category)
    if status == 'unack':
        query = query.filter(OperationalAlert.is_acknowledged.is_(False))
    elif status == 'ack':
        query = query.filter(OperationalAlert.is_acknowledged.is_(True))

    alerts = query.order_by(OperationalAlert.created_at.desc()).all()

    return render_template(
        'alerts/index.html',
        alerts=alerts,
        selected_severity=severity,
        selected_category=category,
        selected_status=status
    )


@alerts_bp.route('/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
@role_required('admin', 'coordinator', 'manager')
def acknowledge(alert_id: int):
    user = get_current_user()
    if AlertService.acknowledge_alert(alert_id, user=user):
        flash('Alert marked as acknowledged.', 'info')
    else:
        flash('Alert not found.', 'danger')
    return redirect(url_for('alerts.index'))


@alerts_bp.route('/refresh', methods=['POST'])
@login_required
@role_required('admin', 'coordinator')
def refresh():
    AlertService.evaluate_and_generate_alerts()
    flash('Operational intelligence alerts refreshed.', 'success')
    return redirect(url_for('alerts.index'))
