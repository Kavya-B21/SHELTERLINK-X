from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.shelters import shelters_bp
from app.routes.requests import requests_bp
from app.routes.allocation import allocation_bp
from app.routes.forecasting import forecasting_bp
from app.routes.data_pipeline import data_bp
from app.routes.alerts import alerts_bp
from app.routes.reports import reports_bp
from app.routes.audit import audit_bp
from app.routes.api import api_bp

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'shelters_bp',
    'requests_bp',
    'allocation_bp',
    'forecasting_bp',
    'data_bp',
    'alerts_bp',
    'reports_bp',
    'audit_bp',
    'api_bp'
]
