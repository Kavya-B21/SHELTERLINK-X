import pytest
from app.models.user import User


def test_user_password_hashing(app):
    """Test password hashing and verification."""
    user = User(username='testuser', email='test@test.com', full_name='Test User', role='viewer')
    user.set_password('Secret@123')
    assert user.check_password('Secret@123') is True
    assert user.check_password('WrongPass') is False


def test_login_success(client):
    """Test successful login redirect to dashboard."""
    response = client.post('/auth/login', data={
        'username': 'admin',
        'password': 'Admin@12345'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Disaster Operations Intelligence' in response.data


def test_login_invalid_password(client):
    """Test failed login with incorrect password."""
    response = client.post('/auth/login', data={
        'username': 'admin',
        'password': 'WrongPassword123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid username or password' in response.data


def test_role_based_access_admin_route(client, auth_client):
    """Test RBAC restriction: viewer cannot access audit trail."""
    c = auth_client(username='viewer')
    res = c.get('/audit', follow_redirects=False)
    # Viewer must be denied with 403 Forbidden
    assert res.status_code == 403


def test_role_based_access_admin_permitted(client, auth_client):
    """Test RBAC permission: admin can access audit trail."""
    c = auth_client(username='admin')
    res = c.get('/audit')
    assert res.status_code == 200
    assert b'Security & Operational Audit Trail' in res.data
