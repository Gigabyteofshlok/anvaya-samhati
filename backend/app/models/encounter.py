import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Encounter(Base):
    __tablename__ = "encounters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    encounter_type = Column(String(50), nullable=False, default="IPD")  # OPD, IPD, EMERGENCY, FOLLOW_UP, OBSERVATION
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, COMPLETED, CANCELLED
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    attending_doctor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="encounters")
    branch = relationship("Branch")
    department = relationship("Department")
    attending_doctor = relationship("User", foreign_keys=[attending_doctor_id])
    admissions = relationship("Admission", back_populates="encounter", cascade="all, delete-orphan")
    vitals = relationship("PatientVital", back_populates="encounter", cascade="all, delete-orphan")
    clinical_notes = relationship("ClinicalNote", back_populates="encounter", cascade="all, delete-orphan")
    events = relationship("PatientEvent", back_populates="encounter", cascade="all, delete-orphan")
