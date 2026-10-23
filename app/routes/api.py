from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from sqlalchemy import text
from app.extensions import db
from app.models.shelter import Shelter
from app.models.history import ShelterHistory
from app.models.request import ShelterRequest
from app.services.forecasting_engine import ForecastingEngine

api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health():
    """Cloud-ready health check endpoint for container orchestrators & load balancers."""
    db_status = "healthy"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    history_count = ShelterHistory.query.count()
    model_status = "ready" if history_count >= 20 else "baseline_mode"

    return jsonify({
        'status': 'healthy' if db_status == 'healthy' else 'degraded',
        'application': 'SHELTERLINK X',
        'version': '1.0.0',
        'database': db_status,
        'telemetry_samples': history_count,
        'forecasting_engine': model_status,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), (200 if db_status == 'healthy' else 503)


@api_bp.route('/api/shelters/geojson')
def shelters_geojson():
    """GeoJSON endpoint for Leaflet.js interactive shelter map."""
    shelters = Shelter.query.filter(
        Shelter.latitude.isnot(None),
        Shelter.longitude.isnot(None)
    ).all()

    features = []
    for s in shelters:
        # Determine pin color classification
        if s.status in ('Inactive', 'Temporarily Closed'):
            color = '#6c757d'  # gray
        elif s.utilization_percentage >= 95.0 or s.available_capacity <= 0:
            color = '#dc3545'  # danger red
        elif s.utilization_percentage >= 85.0:
            color = '#fd7e14'  # warning orange
        elif s.utilization_percentage >= 70.0:
            color = '#ffc107'  # amber
        else:
            color = '#198754'  # success green

        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [s.longitude, s.latitude]
            },
            'properties': {
                'id': s.id,
                'code': s.shelter_code,
                'name': s.name,
                'location': s.location_name,
                'total_capacity': s.total_capacity,
                'current_occupancy': s.current_occupancy,
                'available_capacity': s.available_capacity,
                'utilization_pct': s.utilization_percentage,
                'status': s.status,
                'has_accessibility': s.has_accessibility_ramps,
                'has_medical': s.has_medical_support,
                'has_family': s.has_family_rooms,
                'color': color
            }
        })

    return jsonify({
        'type': 'FeatureCollection',
        'features': features
    })


@api_bp.route('/api/analytics/charts')
def charts_data():
    """Aggregated JSON dataset for Chart.js dashboard visualizations."""
    shelters = Shelter.query.filter(Shelter.status != 'Inactive').all()

    # Chart 1: Shelter Occupancy vs Available Capacity
    shelter_labels = [s.shelter_code for s in shelters]
    occupancy_data = [s.current_occupancy for s in shelters]
    reserved_data = [s.reserved_capacity for s in shelters]
    available_data = [s.available_capacity for s in shelters]

    # Chart 2: Requests by Status
    request_statuses = ['Submitted', 'Under Review', 'Recommended', 'Allocation Confirmed', 'Checked In', 'Completed']
    request_counts = [
        ShelterRequest.query.filter_by(status=st).count()
        for st in request_statuses
    ]

    # Chart 3: Forecasted Inflow (Top 5 shelters)
    top_shelters = shelters[:5]
    forecast_labels = [s.shelter_code for s in top_shelters]
    forecast_vals_3h = []
    forecast_vals_6h = []
    for s in top_shelters:
        f3 = ForecastingEngine.forecast_shelter_demand(s, horizon_hours=3)
        f6 = ForecastingEngine.forecast_shelter_demand(s, horizon_hours=6)
        forecast_vals_3h.append(f3['forecasted_incoming'])
        forecast_vals_6h.append(f6['forecasted_incoming'])

    return jsonify({
        'occupancy_chart': {
            'labels': shelter_labels,
            'occupancy': occupancy_data,
            'reserved': reserved_data,
            'available': available_data
        },
        'requests_chart': {
            'labels': request_statuses,
            'counts': request_counts
        },
        'forecast_chart': {
            'labels': forecast_labels,
            'horizon_3h': forecast_vals_3h,
            'horizon_6h': forecast_vals_6h
        }
    })
