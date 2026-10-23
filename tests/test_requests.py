import pytest
from app.models.request import ShelterRequest


def test_create_shelter_request(client, auth_client):
    """Test survivor intake request submission."""
    c = auth_client(username='coordinator')
    res = c.post('/requests/create', data={
        'household_alias': 'Household Alpha-Test',
        'people_count': '3',
        'affected_area': 'East River Basin',
        'accommodation_type': 'Family Unit',
        'requires_accessibility': '1',
        'requires_medical': '0',
        'requires_family_room': '1',
        'priority_level': 'High',
        'notes': 'Unit test registration'
    }, follow_redirects=True)
    assert res.status_code == 200

    req = ShelterRequest.query.filter_by(household_alias='Household Alpha-Test').first()
    assert req is not None
    assert req.people_count == 3
    assert req.requires_accessibility is True
    assert req.requires_medical is False
    assert req.requires_family_room is True
    assert req.priority_level == 'High'


def test_request_cancellation(client, auth_client):
    """Test cancellation of request."""
    c = auth_client(username='coordinator')
    req = ShelterRequest.query.filter_by(status='Submitted').first()
    assert req is not None

    res = c.post(f'/requests/{req.id}/cancel', follow_redirects=True)
    assert res.status_code == 200
    assert req.status == 'Cancelled'
