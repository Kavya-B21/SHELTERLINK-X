import pytest
from app.models.shelter import Shelter
from app.models.request import ShelterRequest
from app.models.allocation import ConfirmedAllocation
from app.models.user import User
from app.services.allocation_engine import AllocationEngine


def test_allocation_filtering_accessibility_and_capacity(app):
    """Test that allocation engine strictly excludes shelters lacking mandatory accessibility."""
    # REQ-2026-001 requires accessibility, medical, and family room for 4 people
    req = ShelterRequest.query.filter_by(request_code='REQ-2026-001').first()
    assert req is not None

    candidates = AllocationEngine.evaluate_and_rank_shelters(req)
    eligible = [c for c in candidates if c['is_eligible']]
    ineligible = [c for c in candidates if not c['is_eligible']]

    # All eligible shelters must have accessibility ramps and available_capacity >= 4
    for c in eligible:
        assert c['has_accessibility_ramps'] is True
        assert c['has_medical_support'] is True
        assert c['has_family_rooms'] is True
        assert c['available_capacity'] >= req.people_count

    # Ineligible shelters must have an explanation of unmet criteria
    for c in ineligible:
        assert len(c['unmet_criteria']) > 0


def test_family_preservation_large_group(app):
    """Test family preservation rule: a household of 12 must not be split into a shelter with only 5 beds."""
    req = ShelterRequest.query.filter_by(request_code='REQ-2026-006').first() # 12 pax
    candidates = AllocationEngine.evaluate_and_rank_shelters(req)

    for c in candidates:
        if c['available_capacity'] < 12:
            assert c['is_eligible'] is False
            assert any('Insufficient available beds' in reason for reason in c['unmet_criteria'])


def test_transactional_allocation_confirmation_and_reservation(app):
    """Test atomic capacity reservation upon coordinator confirmation."""
    req = ShelterRequest.query.filter_by(request_code='REQ-2026-002').first() # 2 pax, Submitted
    shelter = Shelter.query.filter_by(shelter_code='SHELTER-003').first() # Sports arena, ample space

    initial_reserved = shelter.reserved_capacity
    initial_avail = shelter.available_capacity
    user = User.query.filter_by(username='coordinator').first()

    success, msg, confirmed = AllocationEngine.confirm_allocation(
        request_id=req.id,
        shelter_id=shelter.id,
        user=user
    )

    assert success is True
    assert confirmed is not None
    assert req.status == 'Allocation Confirmed'
    assert shelter.reserved_capacity == initial_reserved + req.people_count
    assert shelter.available_capacity == initial_avail - req.people_count

    # Prevent double allocation
    success2, msg2, _ = AllocationEngine.confirm_allocation(
        request_id=req.id,
        shelter_id=shelter.id,
        user=user
    )
    assert success2 is False
    assert "already confirmed" in msg2


def test_check_in_lifecycle_transition(app):
    """Test check-in moves beds from reserved_capacity to current_occupancy."""
    req = ShelterRequest.query.filter_by(request_code='REQ-2026-005').first()
    assert req is not None
    shelter = req.assigned_shelter
    assert shelter is not None
    alloc = ConfirmedAllocation.query.filter_by(request_id=req.id).first()
    assert alloc is not None
    user = User.query.filter_by(username='manager').first()

    initial_occ = shelter.current_occupancy
    initial_res = shelter.reserved_capacity

    success, msg = AllocationEngine.update_check_in_status(
        confirmed_id=alloc.id,
        new_status='Checked In',
        user=user
    )
    assert success is True
    assert alloc.check_in_status == 'Checked In'
    assert req.status == 'Checked In'
    # Reserved capacity decrements, current occupancy increments
    assert shelter.current_occupancy == initial_occ + alloc.people_count
    assert shelter.reserved_capacity == initial_res - alloc.people_count
