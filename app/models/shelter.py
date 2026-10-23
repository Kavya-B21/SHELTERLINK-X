from datetime import datetime, timezone
from app.extensions import db


class Shelter(db.Model):
    """Emergency disaster shelter model."""
    __tablename__ = 'shelters'

    id = db.Column(db.Integer, primary_key=True)
    shelter_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    location_name = db.Column(db.String(128), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Capacity numbers
    total_capacity = db.Column(db.Integer, nullable=False, default=100)
    current_occupancy = db.Column(db.Integer, nullable=False, default=0)
    reserved_capacity = db.Column(db.Integer, nullable=False, default=0)
    
    # Status: 'Active', 'Approaching Capacity', 'Full', 'Temporarily Closed', 'Inactive'
    status = db.Column(db.String(32), nullable=False, default='Active', index=True)
    
    # Facilities and capabilities
    has_accessibility_ramps = db.Column(db.Boolean, nullable=False, default=False)
    has_drinking_water = db.Column(db.Boolean, nullable=False, default=True)
    has_food_supply = db.Column(db.Boolean, nullable=False, default=True)
    has_medical_support = db.Column(db.Boolean, nullable=False, default=False)
    has_sanitation = db.Column(db.Boolean, nullable=False, default=True)
    has_family_rooms = db.Column(db.Boolean, nullable=False, default=False)
    has_power_backup = db.Column(db.Boolean, nullable=False, default=False)
    
    # Operational contacts
    contact_person = db.Column(db.String(128), nullable=True)
    contact_phone = db.Column(db.String(32), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Timestamps & auditing
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_updated_by = db.Column(db.String(64), nullable=True)

    # Relationships
    occupancy_logs = db.relationship('ShelterHistory', backref='shelter', lazy='dynamic', cascade='all, delete-orphan')
    requests = db.relationship('ShelterRequest', backref='assigned_shelter', lazy='dynamic')
    allocations = db.relationship('ConfirmedAllocation', backref='shelter', lazy='dynamic')
    alerts = db.relationship('OperationalAlert', backref='shelter', lazy='dynamic')

    @property
    def available_capacity(self) -> int:
        """Formula: Total capacity - Current occupancy - Reserved capacity."""
        calc = self.total_capacity - self.current_occupancy - self.reserved_capacity
        return max(0, calc)

    @property
    def utilization_percentage(self) -> float:
        """Calculate percentage of capacity occupied or reserved."""
        if not self.total_capacity or self.total_capacity <= 0:
            return 0.0
        pct = ((self.current_occupancy + self.reserved_capacity) / self.total_capacity) * 100.0
        return round(min(100.0, max(0.0, pct)), 1)

    @property
    def is_active(self) -> bool:
        return self.status in ('Active', 'Approaching Capacity')

    def update_status_based_on_capacity(self):
        """Auto-adjust status flag if shelter is active."""
        if self.status in ('Temporarily Closed', 'Inactive'):
            return
        
        utilization = self.utilization_percentage
        if utilization >= 100.0 or self.available_capacity <= 0:
            self.status = 'Full'
        elif utilization >= 85.0:
            self.status = 'Approaching Capacity'
        else:
            self.status = 'Active'

    def validate_capacity(self, allow_override: bool = False, override_reason: str = None) -> tuple[bool, str]:
        """Validate capacity values."""
        if self.total_capacity < 0:
            return False, "Total capacity cannot be negative."
        if self.current_occupancy < 0:
            return False, "Current occupancy cannot be negative."
        if self.reserved_capacity < 0:
            return False, "Reserved capacity cannot be negative."
        
        used = self.current_occupancy + self.reserved_capacity
        if used > self.total_capacity and not allow_override:
            return False, f"Occupancy and reservations ({used}) exceed total capacity ({self.total_capacity})."
        
        return True, "Valid capacity"

    def to_dict(self):
        return {
            'id': self.id,
            'shelter_code': self.shelter_code,
            'name': self.name,
            'location_name': self.location_name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'total_capacity': self.total_capacity,
            'current_occupancy': self.current_occupancy,
            'reserved_capacity': self.reserved_capacity,
            'available_capacity': self.available_capacity,
            'utilization_percentage': self.utilization_percentage,
            'status': self.status,
            'has_accessibility_ramps': self.has_accessibility_ramps,
            'has_drinking_water': self.has_drinking_water,
            'has_food_supply': self.has_food_supply,
            'has_medical_support': self.has_medical_support,
            'has_sanitation': self.has_sanitation,
            'has_family_rooms': self.has_family_rooms,
            'has_power_backup': self.has_power_backup,
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Shelter {self.shelter_code}: {self.name} ({self.available_capacity}/{self.total_capacity} available)>'
