import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from config import config_by_name
from app.extensions import db, csrf
from app.utils.decorators import get_current_user


def create_app(config_name=None):
    """Application factory for SHELTERLINK X."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    config_cls = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_cls)

    # Ensure required runtime directories exist
    os.makedirs(app.config.get('INSTANCE_PATH', 'instance'), exist_ok=True)
    os.makedirs(app.config.get('LOG_DIR', 'logs'), exist_ok=True)
    os.makedirs(app.config.get('MODEL_CACHE_DIR', 'instance/models'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    # Exempt health check and API endpoints from CSRF
    from app.routes.api import api_bp
    csrf.exempt(api_bp)

    # Configure structured logging
    configure_logging(app)

    # Register blueprints
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

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(shelters_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(allocation_bp)
    app.register_blueprint(forecasting_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(api_bp)

    # Register error handlers
    register_error_handlers(app)

    # Context processors
    @app.context_processor
    def inject_user_context():
        user = get_current_user()
        return dict(
            current_user=user,
            app_name="SHELTERLINK X",
            app_version="1.0.0"
        )

    return app


def configure_logging(app):
    """Configure rotating file logging and stream logging."""
    if not app.debug or app.config.get('TESTING'):
        log_file = app.config.get('LOG_FILE', 'logs/shelterlink.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        ))
        log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(log_level)
        app.logger.info('SHELTERLINK X application logging initialized.')


def register_error_handlers(app):
    """Custom safe error handlers preventing stack trace leakage."""
    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"Internal server error: {error}")
        return render_template('errors/500.html'), 500
