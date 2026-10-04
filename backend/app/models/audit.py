import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    actor_email = Column(String(150), nullable=True)
    action = Column(String(100), nullable=False, index=True)  # LOGIN, PATIENT_CREATE, BED_ASSIGN, BED_RELEASE, etc.
    entity_type = Column(String(100), nullable=False, index=True)  # PATIENT, ADMISSION, BED, etc.
    entity_id = Column(String(100), nullable=True, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    old_state_json = Column(JSON, nullable=True)
    new_state_json = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    actor = relationship("User")
    branch = relationship("Branch")
