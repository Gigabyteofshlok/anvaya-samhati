import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Float, Text, Enum
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class BedStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    CLEANING = "CLEANING"
    MAINTENANCE = "MAINTENANCE"
    ISOLATION = "ISOLATION"

class Bed(Base):
    __tablename__ = "beds"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False, index=True)
    ward_id = Column(String(36), ForeignKey("wards.id"), nullable=False, index=True)
    room_id = Column(String(36), ForeignKey("rooms.id"), nullable=False, index=True)
    bed_number = Column(String(50), nullable=False)
    bed_type = Column(String(50), default="STANDARD")  # STANDARD, ICU, VENTILATOR, PEDIATRIC, DELUXE
    status = Column(String(30), default=BedStatus.AVAILABLE.value, nullable=False, index=True)
    is_isolation = Column(Boolean, default=False, nullable=False)
    maintenance_notes = Column(Text, nullable=True)
    tariff_rate = Column(Float, default=0.0)
    current_admission_id = Column(String(36), nullable=True)  # Will link to admission
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    room = relationship("Room", back_populates="beds")
    ward = relationship("Ward", back_populates="beds")
    branch = relationship("Branch")
    admissions = relationship("Admission", back_populates="bed", foreign_keys="Admission.assigned_bed_id")
