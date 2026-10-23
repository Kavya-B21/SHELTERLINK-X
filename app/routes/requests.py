from datetime import datetime, timezone
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from app.extensions import db
from app.models.request import ShelterRequest
from app.models.shelter import Shelter
from app.services.audit_service import AuditService
from app.utils.decorators import login_required, role_required, get_current_user
from app.utils.geo import get_area_coordinates

requests_bp = Blueprint('requests', __name__, url_prefix='/requests')


@requests_bp.route('/', strict_slashes=False)
@requests_bp.route('', strict_slashes=False)
@login_required
def index():
    status = request.args.get('status', '').strip()
    area = request.args.get('area', '').strip()
    priority = request.args.get('priority', '').strip()

    query = ShelterRequest.query
    if status:
        query = query.filter(ShelterRequest.status == status)
    if area:
        query = query.filter(ShelterRequest.affected_area.ilike(f'%{area}%'))
    if priority:
        query = query.filter(ShelterRequest.priority_level == priority)

    requests_list = query.order_by(ShelterRequest.created_at.desc()).all()
    areas = sorted(list(set(r.affected_area for r in ShelterRequest.query.all())))

    return render_template(
        'requests/index.html',
        requests=requests_list,
        areas=areas,
        selected_status=status,
        selected_area=area,
        selected_priority=priority
    )


@requests_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        user = get_current_user()
        
        # Household alias pseudonymous generator if empty
        alias = request.form.get('household_alias', '').strip()
        if not alias:
            alias = f"Household {chr(random.randint(65, 90))}-{random.randint(10, 99)}"

        try:
            people_count = int(request.form.get('people_count', 1))
        except ValueError:
            flash('Household size must be a valid number.', 'danger')
            return render_template('requests/form.html', request_item=None)

        if people_count <= 0:
            flash('Household size must be at least 1.', 'danger')
            return render_template('requests/form.html', request_item=None)

        area = request.form.get('affected_area', '').strip()
        if not area:
            flash('Affected area / location is required.', 'danger')
            return render_template('requests/form.html', request_item=None)

        lat = request.form.get('latitude')
        lon = request.form.get('longitude')
        try:
            lat = float(lat) if lat not in (None, '') else None
            lon = float(lon) if lon not in (None, '') else None
        except ValueError:
            lat, lon = None, None

        if lat is None or lon is None:
            lat, lon = get_area_coordinates(area)

        # Unique code
        req_code = f"REQ-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

        req_obj = ShelterRequest(
            request_code=req_code,
            household_alias=alias,
            people_count=people_count,
            affected_area=area,
            latitude=lat,
            longitude=lon,
            accommodation_type=request.form.get('accommodation_type', 'Standard'),
            requires_accessibility=request.form.get('requires_accessibility') == '1',
            requires_medical=request.form.get('requires_medical') == '1',
            requires_family_room=request.form.get('requires_family_room') == '1',
            priority_level=request.form.get('priority_level', 'Standard'),
            status='Submitted',
            notes=request.form.get('notes', '').strip()
        )
        db.session.add(req_obj)
        db.session.commit()

        AuditService.log(
            action='REQUEST_REGISTER',
            resource_type='ShelterRequest',
            resource_id=req_obj.request_code,
            details=f"Registered shelter request for {alias} ({people_count} pax) in {area}",
            user=user
        )

        flash(f'Shelter request {req_obj.request_code} registered successfully.', 'success')
        return redirect(url_for('allocation.recommend', request_id=req_obj.id))

    areas = sorted(list(set(s.location_name for s in Shelter.query.all())))
    return render_template('requests/form.html', request_item=None, areas=areas, title='Register Household Shelter Request')


@requests_bp.route('/<int:request_id>')
@login_required
def detail(request_id: int):
    req_obj = ShelterRequest.query.get(request_id)
    if not req_obj:
        abort(404)
    return render_template('requests/detail.html', request_item=req_obj)


@requests_bp.route('/<int:request_id>/cancel', methods=['POST'])
@login_required
@role_required('admin', 'coordinator')
def cancel(request_id: int):
    req_obj = ShelterRequest.query.get(request_id)
    if not req_obj:
        abort(404)

    user = get_current_user()
    req_obj.status = 'Cancelled'
    db.session.commit()

    AuditService.log(
        action='REQUEST_CANCEL',
        resource_type='ShelterRequest',
        resource_id=req_obj.request_code,
        details=f"Cancelled request {req_obj.request_code}",
        user=user
    )

    flash(f"Request {req_obj.request_code} has been cancelled.", 'info')
    return redirect(url_for('requests.index'))
