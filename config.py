import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env if present
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'shelterlink-x-dev-secret-key-2026')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        # Fix for Heroku/Render postgres:// -> postgresql://
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    elif not db_url or 'sqlite:///' in db_url:
        instance_dir = os.path.join(basedir, 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        db_path = os.path.join(instance_dir, 'shelterlink.db').replace('\\', '/')
        db_url = f"sqlite:///{db_path}"
    SQLALCHEMY_DATABASE_URI = db_url
    
    # Session & Security
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get('PERMANENT_SESSION_LIFETIME_MINUTES', 120)))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')
    
    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 7200  # 2 hours
    
    # File Upload limits (max 10MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'csv'}
    
    # Application Paths
    INSTANCE_PATH = os.path.join(basedir, 'instance')
    MODEL_CACHE_DIR = os.path.join(basedir, 'instance', 'models')
    LOG_DIR = os.path.join(basedir, 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'shelterlink.log')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False  # Ease form testing in unit tests
    SECRET_KEY = 'test-secret-key-for-unit-testing'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app) if hasattr(Config, 'init_app') else None
        # Verify secret key
        if os.environ.get('SECRET_KEY') == 'shelterlink-x-dev-secret-key-2026':
            raise ValueError("SECRET_KEY must be configured securely in production!")


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
