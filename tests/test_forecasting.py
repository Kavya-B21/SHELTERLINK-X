import pytest
from app.models.shelter import Shelter
from app.services.forecasting_engine import ForecastingEngine


def test_forecasting_evaluation_metrics(app):
    """Test model training and evaluation metric generation."""
    eval_result = ForecastingEngine.train_and_evaluate(horizon_hours=6)
    assert eval_result['status'] == 'success'
    assert 'metrics_rf' in eval_result
    assert 'metrics_baseline' in eval_result
    assert eval_result['metrics_rf']['mae'] >= 0
    assert eval_result['metrics_rf']['rmse'] >= 0
    assert len(eval_result['feature_importances']) > 0


def test_shelter_demand_prediction_risk_categories(app):
    """Test capacity pressure estimation and risk categorization."""
    # Test on a shelter approaching capacity
    shelter = Shelter.query.filter_by(shelter_code='SHELTER-002').first() # 95% full
    pred = ForecastingEngine.forecast_shelter_demand(shelter, horizon_hours=6)

    assert pred['shelter_id'] == shelter.id
    assert pred['risk_category'] in ('HIGH', 'CRITICAL')
    assert pred['forecasted_incoming'] >= 0
    assert pred['projected_occupancy'] >= 0
    assert len(pred['key_factors']) > 0


def test_multi_horizon_forecasting(app):
    """Test forecasts across 1h, 3h, 6h, and 12h horizons."""
    shelter = Shelter.query.filter_by(shelter_code='SHELTER-001').first()
    for h in [1, 3, 6, 12]:
        res = ForecastingEngine.forecast_shelter_demand(shelter, horizon_hours=h)
        assert res['horizon_hours'] == h
        assert res['projected_occupancy'] >= 0
