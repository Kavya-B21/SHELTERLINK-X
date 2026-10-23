from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    """User account model with Role-Based Access Control (RBAC)."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='viewer')
    # Roles: 'admin', 'coordinator', 'manager', 'viewer'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    assigned_shelter_id = db.Column(db.Integer, db.ForeignKey('shelters.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def set_password(self, password: str):
        """Hash and store password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)

    # Permission helper methods
    def is_admin(self) -> bool:
        return self.role == 'admin'

    def is_coordinator(self) -> bool:
        return self.role in ('admin', 'coordinator')

    def is_shelter_manager(self) -> bool:
        return self.role in ('admin', 'coordinator', 'manager')

    def can_manage_shelters(self) -> bool:
        return self.role in ('admin', 'coordinator', 'manager')

    def can_confirm_allocation(self) -> bool:
        return self.role in ('admin', 'coordinator')

    def can_import_data(self) -> bool:
        return self.role in ('admin', 'coordinator')

    def can_view_audit_logs(self) -> bool:
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'assigned_shelter_id': self.assigned_shelter_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
