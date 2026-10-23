from flask import request
from app.extensions import db
from app.models.audit import AuditLog


class AuditService:
    """Service for recording security, administrative, and operational events."""

    @staticmethod
    def log(action: str, resource_type: str = None, resource_id: str = None, details: str = None, user=None):
        """Create and commit an audit log entry."""
        try:
            ip_addr = None
            if request:
                ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            user_id = user.id if user else None
            username = user.username if user else 'System/Anonymous'

            entry = AuditLog(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                details=details,
                ip_address=ip_addr
            )
            db.session.add(entry)
            db.session.commit()
            return entry
        except Exception:
            db.session.rollback()
            # Silently fail so audit logging never crashes the primary transaction
            return None
