import pytest
from app.models.shelter import Shelter
from app.services.shelter_service import ShelterService


def test_capacity_formula_and_available(app):
    """Test available capacity calculation formula."""
    shelter = Shelter(
        shelter_code='TEST-001',
        name='Test Shelter',
        location_name='North Sector',
        total_capacity=100,
        current_occupancy=40,
        reserved_capacity=10
    )
    # Available = 100 - 40 - 10 = 50
    assert shelter.available_capacity == 50
    assert shelter.utilization_percentage == 50.0


def test_create_shelter_validation_negative_capacity(app):
    """Test validation: cannot create shelter with negative capacity."""
    bad_data = {
        'shelter_code': 'BAD-001',
        'name': 'Bad Shelter',
        'location_name': 'Sector X',
        'total_capacity': -50,
        'current_occupancy': 0
    }
    shelter, msg = ShelterService.create_shelter(bad_data)
    assert shelter is None
    assert "greater than zero" in msg


def test_create_shelter_exceeding_capacity(app):
    """Test validation: cannot initialize occupancy > total capacity."""
    bad_data = {
        'shelter_code': 'BAD-002',
        'name': 'Overbooked Shelter',
        'location_name': 'Sector Y',
        'total_capacity': 50,
        'current_occupancy': 60
    }
    shelter, msg = ShelterService.create_shelter(bad_data)
    assert shelter is None
    assert "cannot exceed total capacity" in msg


def test_update_occupancy_arrival_and_departure(app):
    """Test arrival increment and departure decrement."""
    shelter = Shelter.query.filter_by(shelter_code='SHELTER-001').first()
    initial_occ = shelter.current_occupancy

    # Add 5 arrivals
    success, msg = ShelterService.update_occupancy(
        shelter=shelter,
        count_change=5,
        change_type='arrival',
        reason='Family bus arrival'
    )
    assert success is True
    assert shelter.current_occupancy == initial_occ + 5

    # Subtract 3 departures
    success, msg = ShelterService.update_occupancy(
        shelter=shelter,
        count_change=3,
        change_type='departure',
        reason='Re-housing transfer'
    )
    assert success is True
    assert shelter.current_occupancy == initial_occ + 2


def test_update_occupancy_overbooking_prevented_without_override(app):
    """Test overbooking prevention without explicit override."""
    shelter = Shelter.query.filter_by(shelter_code='SHELTER-001').first()
    # Try adding 500 arrivals to a 250 capacity shelter
    success, msg = ShelterService.update_occupancy(
        shelter=shelter,
        count_change=500,
        change_type='arrival',
        allow_override=False
    )
    assert success is False
    assert "exceed total capacity" in msg
