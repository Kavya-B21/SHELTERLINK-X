from datetime import datetime, timezone
from app.extensions import db
from app.models.shelter import Shelter
from app.models.history import ShelterHistory
from app.services.audit_service import AuditService


class ShelterService:
    """Business logic service for shelter administration and occupancy tracking."""

    @staticmethod
    def get_all_shelters(status=None, area=None, search=None, min_available=None,
                         has_accessibility=False, has_medical=False, has_family=False):
        """Query shelters with flexible operational filtering."""
        query = Shelter.query

        if status:
            query = query.filter(Shelter.status == status)
        if area:
            query = query.filter(Shelter.location_name.ilike(f'%{area}%'))
        if search:
            query = query.filter(
                (Shelter.name.ilike(f'%{search}%')) |
                (Shelter.shelter_code.ilike(f'%{search}%')) |
                (Shelter.location_name.ilike(f'%{search}%'))
            )
        if has_accessibility:
            query = query.filter(Shelter.has_accessibility_ramps.is_(True))
        if has_medical:
            query = query.filter(Shelter.has_medical_support.is_(True))
        if has_family:
            query = query.filter(Shelter.has_family_rooms.is_(True))

        shelters = query.order_by(Shelter.name.asc()).all()

        if min_available is not None and min_available > 0:
            shelters = [s for s in shelters if s.available_capacity >= min_available]

        return shelters

    @staticmethod
    def get_shelter_by_id(shelter_id: int) -> Shelter | None:
        return Shelter.query.get(shelter_id)

    @staticmethod
    def get_shelter_by_code(shelter_code: str) -> Shelter | None:
        return Shelter.query.filter_by(shelter_code=shelter_code).first()

    @staticmethod
    def create_shelter(data: dict, user=None) -> tuple[Shelter | None, str]:
        """Register a new shelter with capacity validation."""
        code = data.get('shelter_code', '').strip().upper()
        if not code:
            return None, "Shelter code is required."

        if Shelter.query.filter_by(shelter_code=code).first():
            return None, f"Shelter with code '{code}' already exists."

        name = data.get('name', '').strip()
        location_name = data.get('location_name', '').strip()
        if not name or not location_name:
            return None, "Shelter name and location area are required."

        try:
            total_cap = int(data.get('total_capacity', 100))
            current_occ = int(data.get('current_occupancy', 0))
            reserved_cap = int(data.get('reserved_capacity', 0))
        except (ValueError, TypeError):
            return None, "Capacity and occupancy must be integers."

        if total_cap <= 0:
            return None, "Total capacity must be greater than zero."
        if current_occ < 0 or reserved_cap < 0:
            return None, "Occupancy and reservations cannot be negative."
        if (current_occ + reserved_cap) > total_cap:
            return None, f"Initial occupancy + reserved ({current_occ + reserved_cap}) cannot exceed total capacity ({total_cap})."

        lat = data.get('latitude')
        lon = data.get('longitude')
        try:
            lat = float(lat) if lat not in (None, '') else None
            lon = float(lon) if lon not in (None, '') else None
        except (ValueError, TypeError):
            return None, "Latitude and longitude must be valid floating numbers."

        shelter = Shelter(
            shelter_code=code,
            name=name,
            location_name=location_name,
            latitude=lat,
            longitude=lon,
            total_capacity=total_cap,
            current_occupancy=current_occ,
            reserved_capacity=reserved_cap,
            status=data.get('status', 'Active'),
            has_accessibility_ramps=bool(data.get('has_accessibility_ramps', False)),
            has_drinking_water=bool(data.get('has_drinking_water', True)),
            has_food_supply=bool(data.get('has_food_supply', True)),
            has_medical_support=bool(data.get('has_medical_support', False)),
            has_sanitation=bool(data.get('has_sanitation', True)),
            has_family_rooms=bool(data.get('has_family_rooms', False)),
            has_power_backup=bool(data.get('has_power_backup', False)),
            contact_person=data.get('contact_person', ''),
            contact_phone=data.get('contact_phone', ''),
            notes=data.get('notes', ''),
            last_updated_by=user.username if user else 'System'
        )
        shelter.update_status_based_on_capacity()

        db.session.add(shelter)
        db.session.flush()

        # Record initial occupancy in telemetry
        history = ShelterHistory(
            shelter_id=shelter.id,
            timestamp=datetime.now(timezone.utc),
            total_capacity=shelter.total_capacity,
            current_occupancy=shelter.current_occupancy,
            incoming_requests=0,
            departures=0,
            affected_area=shelter.location_name,
            shelter_status=shelter.status,
            notes='Initial shelter registration'
        )
        db.session.add(history)
        db.session.commit()

        AuditService.log(
            action='SHELTER_CREATE',
            resource_type='Shelter',
            resource_id=shelter.shelter_code,
            details=f"Created shelter '{shelter.name}' with capacity {shelter.total_capacity}",
            user=user
        )

        return shelter, "Shelter created successfully."

    @staticmethod
    def update_shelter(shelter: Shelter, data: dict, user=None) -> tuple[bool, str]:
        """Update shelter metadata and facilities."""
        try:
            total_cap = int(data.get('total_capacity', shelter.total_capacity))
            reserved_cap = int(data.get('reserved_capacity', shelter.reserved_capacity))
        except (ValueError, TypeError):
            return False, "Capacity numbers must be valid integers."

        if total_cap <= 0:
            return False, "Total capacity must be greater than zero."
        
        # Check if reduction violates current occupancy
        if shelter.current_occupancy + reserved_cap > total_cap:
            return False, f"Cannot set total capacity ({total_cap}) lower than current occupancy + reservations ({shelter.current_occupancy + reserved_cap})."

        shelter.name = data.get('name', shelter.name)
        shelter.location_name = data.get('location_name', shelter.location_name)
        
        lat = data.get('latitude')
        lon = data.get('longitude')
        try:
            shelter.latitude = float(lat) if lat not in (None, '') else None
            shelter.longitude = float(lon) if lon not in (None, '') else None
        except (ValueError, TypeError):
            pass

        shelter.total_capacity = total_cap
        shelter.reserved_capacity = reserved_cap
        shelter.status = data.get('status', shelter.status)
        
        shelter.has_accessibility_ramps = bool(data.get('has_accessibility_ramps', False))
        shelter.has_drinking_water = bool(data.get('has_drinking_water', False))
        shelter.has_food_supply = bool(data.get('has_food_supply', False))
        shelter.has_medical_support = bool(data.get('has_medical_support', False))
        shelter.has_sanitation = bool(data.get('has_sanitation', False))
        shelter.has_family_rooms = bool(data.get('has_family_rooms', False))
        shelter.has_power_backup = bool(data.get('has_power_backup', False))
        
        shelter.contact_person = data.get('contact_person', shelter.contact_person)
        shelter.contact_phone = data.get('contact_phone', shelter.contact_phone)
        shelter.notes = data.get('notes', shelter.notes)
        shelter.last_updated_by = user.username if user else 'System'
        
        shelter.update_status_based_on_capacity()
        db.session.commit()

        AuditService.log(
            action='SHELTER_UPDATE',
            resource_type='Shelter',
            resource_id=shelter.shelter_code,
            details=f"Updated details for shelter '{shelter.name}'",
            user=user
        )

        return True, "Shelter updated successfully."

    @staticmethod
    def update_occupancy(shelter: Shelter, count_change: int, change_type: str, 
                         reason: str = None, user=None, allow_override: bool = False) -> tuple[bool, str]:
        """
        Safely update current occupancy (arrivals or departures).
        change_type: 'arrival' (+), 'departure' (-), or 'set' (direct absolute value)
        """
        old_occupancy = shelter.current_occupancy
        
        if change_type == 'arrival':
            new_occupancy = old_occupancy + count_change
            incoming_inc = count_change
            departure_inc = 0
        elif change_type == 'departure':
            new_occupancy = max(0, old_occupancy - count_change)
            incoming_inc = 0
            departure_inc = count_change
        elif change_type == 'set':
            new_occupancy = count_change
            incoming_inc = max(0, new_occupancy - old_occupancy)
            departure_inc = max(0, old_occupancy - new_occupancy)
        else:
            return False, "Invalid change type."

        if new_occupancy < 0:
            return False, "Occupancy cannot become negative."

        used_capacity = new_occupancy + shelter.reserved_capacity
        if used_capacity > shelter.total_capacity and not allow_override:
            return False, (f"Action rejected: Resulting occupancy + reservations ({used_capacity}) "
                           f"would exceed total capacity ({shelter.total_capacity}). "
                           "Requires an explicit authorized coordinator override with justification.")

        shelter.current_occupancy = new_occupancy
        shelter.last_updated_by = user.username if user else 'System'
        shelter.update_status_based_on_capacity()

        # Telemetry log
        history_entry = ShelterHistory(
            shelter_id=shelter.id,
            timestamp=datetime.now(timezone.utc),
            total_capacity=shelter.total_capacity,
            current_occupancy=shelter.current_occupancy,
            incoming_requests=incoming_inc,
            departures=departure_inc,
            affected_area=shelter.location_name,
            shelter_status=shelter.status,
            notes=f"Occupancy change: {change_type} ({count_change}). Reason: {reason or 'Regular operational update'}"
        )
        db.session.add(history_entry)
        db.session.commit()

        AuditService.log(
            action='OCCUPANCY_UPDATE',
            resource_type='Shelter',
            resource_id=shelter.shelter_code,
            details=f"Occupancy changed from {old_occupancy} to {new_occupancy} ({change_type} {count_change}). Override: {allow_override}. Reason: {reason}",
            user=user
        )

        return True, f"Occupancy updated from {old_occupancy} to {new_occupancy}."
