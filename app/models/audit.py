from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    """Audit log tracking critical actions, security events, and data modifications."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    username = db.Column(db.String(64), nullable=False, default='Anonymous/System')
    
    # Action type: LOGIN, LOGOUT, SHELTER_CREATE, SHELTER_UPDATE, OCCUPANCY_UPDATE, 
    # ALLOCATION_CONFIRM, DATA_IMPORT, UNAUTHORIZED_ACCESS, SYSTEM_ALERT
    action = db.Column(db.String(64), nullable=False, index=True)
    resource_type = db.Column(db.String(64), nullable=True)
    resource_id = db.Column(db.String(64), nullable=True)
    
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.username} at {self.created_at}>'
