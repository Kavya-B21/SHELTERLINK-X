from datetime import datetime, timezone
from app.extensions import db


class ShelterRequest(db.Model):
    """Survivor and household shelter accommodation request."""
    __tablename__ = 'shelter_requests'

    id = db.Column(db.Integer, primary_key=True)
    request_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    household_alias = db.Column(db.String(64), nullable=False, index=True)
    people_count = db.Column(db.Integer, nullable=False, default=1)
    affected_area = db.Column(db.String(128), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Accommodation specifications
    accommodation_type = db.Column(db.String(64), nullable=False, default='Standard')
    # Types: 'Standard', 'Family Unit', 'Accessible Single Floor'
    requires_accessibility = db.Column(db.Boolean, nullable=False, default=False)
    requires_medical = db.Column(db.Boolean, nullable=False, default=False)
    requires_family_room = db.Column(db.Boolean, nullable=False, default=False)
    priority_level = db.Column(db.String(32), nullable=False, default='Standard')
    # Priorities: 'Standard', 'High', 'Urgent'
    
    # Status progression
    # 'Submitted', 'Under Review', 'Recommended', 'Allocation Confirmed', 'Checked In', 'Completed', 'Cancelled'
    status = db.Column(db.String(32), nullable=False, default='Submitted', index=True)
    
    # Assignment
    assigned_shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id', ondelete='SET NULL'), nullable=True, index=True)
    confirmed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Operational notes & metadata
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    recommendations = db.relationship('AllocationRecommendation', backref='request', lazy='dynamic', cascade='all, delete-orphan')
    confirmed_allocation = db.relationship('ConfirmedAllocation', backref='request', uselist=False, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'request_code': self.request_code,
            'household_alias': self.household_alias,
            'people_count': self.people_count,
            'affected_area': self.affected_area,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accommodation_type': self.accommodation_type,
            'requires_accessibility': self.requires_accessibility,
            'requires_medical': self.requires_medical,
            'requires_family_room': self.requires_family_room,
            'priority_level': self.priority_level,
            'status': self.status,
            'assigned_shelter_id': self.assigned_shelter_id,
            'assigned_shelter_name': self.assigned_shelter.name if self.assigned_shelter else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None
        }

    def __repr__(self):
        return f'<ShelterRequest {self.request_code}: {self.household_alias} ({self.people_count} pax, {self.status})>'
