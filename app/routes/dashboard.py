from flask import Blueprint, render_template, request
from app.models.shelter import Shelter
from app.models.request import ShelterRequest
from app.models.allocation import ConfirmedAllocation
from app.models.alert import OperationalAlert
from app.services.forecasting_engine import ForecastingEngine
from app.utils.decorators import login_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    horizon_hours = int(request.args.get('horizon', 6))
    if horizon_hours not in (1, 3, 6, 12):
        horizon_hours = 6

    area_filter = request.args.get('area', '').strip()

    # Base queries
    shelter_query = Shelter.query
    if area_filter:
        shelter_query = shelter_query.filter(Shelter.location_name.ilike(f'%{area_filter}%'))

    shelters = shelter_query.all()

    # KPIs
    total_shelters = len(shelters)
    active_shelters = sum(1 for s in shelters if s.is_active)
    total_capacity = sum(s.total_capacity for s in shelters)
    current_occupancy = sum(s.current_occupancy for s in shelters)
    reserved_capacity = sum(s.reserved_capacity for s in shelters)
    available_capacity = sum(s.available_capacity for s in shelters)
    
    overall_utilization = round(((current_occupancy + reserved_capacity) / total_capacity * 100), 1) if total_capacity > 0 else 0.0

    # Request KPIs
    pending_requests = ShelterRequest.query.filter(ShelterRequest.status.in_(['Submitted', 'Under Review', 'Recommended'])).count()
    confirmed_allocations = ConfirmedAllocation.query.count()

    # Capacity Pressure Forecasts
    pressure_list = []
    total_forecasted_incoming = 0
    high_critical_count = 0

    for s in shelters:
        if s.status != 'Inactive':
            f_res = ForecastingEngine.forecast_shelter_demand(s, horizon_hours=horizon_hours)
            pressure_list.append(f_res)
            total_forecasted_incoming += f_res['forecasted_incoming']
            if f_res['risk_category'] in ('HIGH', 'CRITICAL'):
                high_critical_count += 1

    pressure_list.sort(key=lambda x: x['projected_utilization_pct'], reverse=True)

    # Active operational alerts
    active_alerts = OperationalAlert.query.filter_by(is_acknowledged=False).order_by(
        OperationalAlert.created_at.desc()
    ).limit(6).all()

    # Recent confirmed allocations
    recent_allocations = ConfirmedAllocation.query.order_by(
        ConfirmedAllocation.confirmed_at.desc()
    ).limit(5).all()

    # Area distribution
    areas = db_areas = list(set(s.location_name for s in Shelter.query.all()))
    areas.sort()

    return render_template(
        'dashboard/index.html',
        total_shelters=total_shelters,
        active_shelters=active_shelters,
        total_capacity=total_capacity,
        current_occupancy=current_occupancy,
        reserved_capacity=reserved_capacity,
        available_capacity=available_capacity,
        overall_utilization=overall_utilization,
        pending_requests=pending_requests,
        confirmed_allocations=confirmed_allocations,
        total_forecasted_incoming=total_forecasted_incoming,
        high_critical_count=high_critical_count,
        pressure_list=pressure_list[:5],  # Top 5 most critical
        shelters=shelters,
        active_alerts=active_alerts,
        recent_allocations=recent_allocations,
        horizon_hours=horizon_hours,
        areas=areas,
        selected_area=area_filter
    )
