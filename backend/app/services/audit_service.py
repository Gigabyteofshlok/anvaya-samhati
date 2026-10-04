from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

def log_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    branch_id: Optional[str] = None,
    old_state: Optional[Any] = None,
    new_state: Optional[Any] = None,
    ip_address: Optional[str] = None,
    notes: Optional[str] = None
) -> AuditLog:
    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        actor_email=actor_email,
        branch_id=branch_id,
        old_state_json=old_state,
        new_state_json=new_state,
        ip_address=ip_address,
        notes=notes
    )
    db.add(entry)
    # Flushed as part of transaction
    return entry
