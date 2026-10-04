from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.identity import User
from app.schemas.audit import AuditLogOut
from app.api.deps import get_current_user, require_permission

router = APIRouter(prefix="/audit-logs", tags=["Audit"])

@router.get("", response_model=List[AuditLogOut])
def get_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit.view"))
):
    query = db.query(AuditLog).options(
        joinedload(AuditLog.actor),
        joinedload(AuditLog.branch)
    )

    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if branch_id:
        query = query.filter(AuditLog.branch_id == branch_id)

    logs = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit).all()

    return [
        AuditLogOut(
            id=log.id,
            actor_id=log.actor_id,
            actor_name=log.actor.full_name if log.actor else "System",
            actor_email=log.actor_email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            branch_id=log.branch_id,
            branch_name=log.branch.name if log.branch else None,
            timestamp=log.timestamp,
            old_state_json=log.old_state_json,
            new_state_json=log.new_state_json,
            ip_address=log.ip_address,
            notes=log.notes
        ) for log in logs
    ]
