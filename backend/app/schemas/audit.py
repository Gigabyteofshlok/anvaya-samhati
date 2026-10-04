from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel

class AuditLogOut(BaseModel):
    id: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    timestamp: datetime
    old_state_json: Optional[Any] = None
    new_state_json: Optional[Any] = None
    ip_address: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True
