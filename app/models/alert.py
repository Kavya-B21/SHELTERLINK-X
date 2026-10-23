from datetime import datetime, timezone
from app.extensions import db


class OperationalAlert(db.Model):
    """Real-time operational advisory alert for coordinators and shelter managers."""
    __tablename__ = 'operational_alerts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    severity = db.Column(db.String(16), nullable=False, default='WARNING', index=True)
    # Severity: 'INFO', 'WARNING', 'CRITICAL'
    category = db.Column(db.String(32), nullable=False, default='CAPACITY', index=True)
    # Category: 'CAPACITY', 'DEMAND_SURGE', 'FACILITY_DEFICIT', 'UNMATCHED_REQUEST', 'STALE_DATA'
    
    shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id', ondelete='CASCADE'), nullable=True, index=True)
    affected_area = db.Column(db.String(128), nullable=True, index=True)
    
    message = db.Column(db.Text, nullable=False)
    suggested_action = db.Column(db.Text, nullable=False)
    
    is_acknowledged = db.Column(db.Boolean, default=False, nullable=False, index=True)
    acknowledged_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    acknowledged_by = db.relationship('User', foreign_keys=[acknowledged_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'severity': self.severity,
            'category': self.category,
            'shelter_id': self.shelter_id,
            'shelter_name': self.shelter.name if self.shelter else None,
            'affected_area': self.affected_area,
            'message': self.message,
            'suggested_action': self.suggested_action,
            'is_acknowledged': self.is_acknowledged,
            'acknowledged_by': self.acknowledged_by.full_name if self.acknowledged_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }

    def __repr__(self):
        return f'<OperationalAlert [{self.severity}] {self.title}>'
