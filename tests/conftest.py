import os
import sys
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.shelter import Shelter
from app.models.history import ShelterHistory
from app.models.request import ShelterRequest
from app.utils.seed_data import seed_database


@pytest.fixture
def app():
    """Create test application instance with in-memory database."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Seed test users
        seed_database()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """Factory fixture for authenticated clients by role."""
    def _login(username='admin', password='Admin@12345'):
        with client.session_transaction() as sess:
            user = User.query.filter_by(username=username).first()
            if user:
                sess['user_id'] = user.id
                sess['username'] = user.username
                sess['role'] = user.role
        return client
    return _login
