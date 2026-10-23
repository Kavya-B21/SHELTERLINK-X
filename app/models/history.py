from datetime import datetime, timezone
from app.extensions import db


class ShelterHistory(db.Model):
    """Historical occupancy and incoming demand observation for telemetry & ML forecasting."""
    __tablename__ = 'shelter_history'

    id = db.Column(db.Integer, primary_key=True)
    shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id', ondelete='CASCADE'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    total_capacity = db.Column(db.Integer, nullable=False)
    current_occupancy = db.Column(db.Integer, nullable=False)
    incoming_requests = db.Column(db.Integer, nullable=False, default=0)
    departures = db.Column(db.Integer, nullable=False, default=0)
    affected_area = db.Column(db.String(128), nullable=False, index=True)
    shelter_status = db.Column(db.String(32), nullable=False, default='Active')
    is_synthetic = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.String(256), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'shelter_id': self.shelter_id,
            'shelter_code': self.shelter.shelter_code if self.shelter else None,
            'shelter_name': self.shelter.name if self.shelter else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'total_capacity': self.total_capacity,
            'current_occupancy': self.current_occupancy,
            'incoming_requests': self.incoming_requests,
            'departures': self.departures,
            'affected_area': self.affected_area,
            'shelter_status': self.shelter_status,
            'is_synthetic': self.is_synthetic
        }

    def __repr__(self):
        return f'<ShelterHistory shelter={self.shelter_id} time={self.timestamp} occ={self.current_occupancy}>'
