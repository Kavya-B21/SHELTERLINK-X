from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from app.models.shelter import Shelter
from app.models.history import ShelterHistory
from app.services.shelter_service import ShelterService
from app.services.forecasting_engine import ForecastingEngine
from app.utils.decorators import login_required, role_required, get_current_user

shelters_bp = Blueprint('shelters', __name__, url_prefix='/shelters')


@shelters_bp.route('/', strict_slashes=False)
@shelters_bp.route('', strict_slashes=False)
@login_required
def index():
    status = request.args.get('status', '').strip()
    area = request.args.get('area', '').strip()
    search = request.args.get('search', '').strip()
    min_cap = request.args.get('min_capacity')
    try:
        min_cap = int(min_cap) if min_cap else None
    except ValueError:
        min_cap = None

    has_acc = request.args.get('has_accessibility') == '1'
    has_med = request.args.get('has_medical') == '1'
    has_fam = request.args.get('has_family') == '1'

    shelters = ShelterService.get_all_shelters(
        status=status or None,
        area=area or None,
        search=search or None,
        min_available=min_cap,
        has_accessibility=has_acc,
        has_medical=has_med,
        has_family=has_fam
    )

    areas = sorted(list(set(s.location_name for s in Shelter.query.all())))

    return render_template(
        'shelters/index.html',
        shelters=shelters,
        areas=areas,
        selected_status=status,
        selected_area=area,
        search_query=search,
        min_capacity=min_cap,
        has_acc=has_acc,
        has_med=has_med,
        has_fam=has_fam
    )


@shelters_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'coordinator')
def create():
    if request.method == 'POST':
        user = get_current_user()
        data = request.form.to_dict()
        shelter, msg = ShelterService.create_shelter(data, user=user)
        if shelter:
            flash(msg, 'success')
            return redirect(url_for('shelters.detail', shelter_id=shelter.id))
        else:
            flash(msg, 'danger')

    return render_template('shelters/form.html', shelter=None, title='Register New Emergency Shelter')


@shelters_bp.route('/<int:shelter_id>')
@login_required
def detail(shelter_id: int):
    shelter = ShelterService.get_shelter_by_id(shelter_id)
    if not shelter:
        abort(404)

    # 6-hour forecast
    forecast = ForecastingEngine.forecast_shelter_demand(shelter, horizon_hours=6)

    # Recent telemetry history
    history = ShelterHistory.query.filter_by(shelter_id=shelter.id).order_by(
        ShelterHistory.timestamp.desc()
    ).limit(15).all()

    # Active requests assigned or confirmed
    confirmed_allocations = shelter.allocations.order_by(
        shelter.allocations.column_descriptions[0]['entity'].confirmed_at.desc()
    ).limit(10).all()

    return render_template(
        'shelters/detail.html',
        shelter=shelter,
        forecast=forecast,
        history=history,
        confirmed_allocations=confirmed_allocations
    )


@shelters_bp.route('/<int:shelter_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'coordinator', 'manager')
def edit(shelter_id: int):
    shelter = ShelterService.get_shelter_by_id(shelter_id)
    if not shelter:
        abort(404)

    user = get_current_user()
    if request.method == 'POST':
        data = request.form.to_dict()
        success, msg = ShelterService.update_shelter(shelter, data, user=user)
        if success:
            flash(msg, 'success')
            return redirect(url_for('shelters.detail', shelter_id=shelter.id))
        else:
            flash(msg, 'danger')

    return render_template('shelters/form.html', shelter=shelter, title=f"Edit Shelter: {shelter.name}")


@shelters_bp.route('/<int:shelter_id>/occupancy', methods=['POST'])
@login_required
@role_required('admin', 'coordinator', 'manager')
def update_occupancy(shelter_id: int):
    shelter = ShelterService.get_shelter_by_id(shelter_id)
    if not shelter:
        abort(404)

    user = get_current_user()
    change_type = request.form.get('change_type', 'arrival')
    try:
        count = int(request.form.get('count', 0))
    except ValueError:
        flash('Invalid occupancy count.', 'danger')
        return redirect(url_for('shelters.detail', shelter_id=shelter.id))

    reason = request.form.get('reason', '').strip()
    allow_override = request.form.get('allow_override') == '1'

    success, msg = ShelterService.update_occupancy(
        shelter=shelter,
        count_change=count,
        change_type=change_type,
        reason=reason,
        user=user,
        allow_override=allow_override
    )

    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('shelters.detail', shelter_id=shelter.id))


@shelters_bp.route('/map')
@login_required
def map_view():
    shelters = Shelter.query.filter(Shelter.status != 'Inactive').all()
    areas = sorted(list(set(s.location_name for s in Shelter.query.all())))
    return render_template('shelters/map.html', shelters=shelters, areas=areas)
