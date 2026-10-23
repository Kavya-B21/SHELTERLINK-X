from flask import Blueprint, render_template, request
from app.services.forecasting_engine import ForecastingEngine
from app.utils.decorators import login_required

forecasting_bp = Blueprint('forecasting', __name__, url_prefix='/forecasting')


@forecasting_bp.route('/', strict_slashes=False)
@forecasting_bp.route('', strict_slashes=False)
@login_required
def index():
    horizon_hours = int(request.args.get('horizon', 6))
    if horizon_hours not in (1, 3, 6, 12):
        horizon_hours = 6

    pressure_results = ForecastingEngine.get_all_shelters_pressure(horizon_hours=horizon_hours)

    critical_count = sum(1 for r in pressure_results if r['risk_category'] == 'CRITICAL')
    high_count = sum(1 for r in pressure_results if r['risk_category'] == 'HIGH')
    moderate_count = sum(1 for r in pressure_results if r['risk_category'] == 'MODERATE')
    low_count = sum(1 for r in pressure_results if r['risk_category'] == 'LOW')

    return render_template(
        'forecasting/index.html',
        pressure_results=pressure_results,
        horizon_hours=horizon_hours,
        critical_count=critical_count,
        high_count=high_count,
        moderate_count=moderate_count,
        low_count=low_count
    )


@forecasting_bp.route('/evaluate')
@login_required
def evaluate():
    horizon_hours = int(request.args.get('horizon', 6))
    if horizon_hours not in (1, 3, 6, 12):
        horizon_hours = 6

    evaluation = ForecastingEngine.train_and_evaluate(horizon_hours=horizon_hours)

    return render_template(
        'forecasting/evaluation.html',
        eval_result=evaluation,
        horizon_hours=horizon_hours
    )
