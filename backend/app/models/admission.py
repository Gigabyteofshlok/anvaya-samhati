import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Admission(Base):
    __tablename__ = "admissions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    admission_number = Column(String(50), unique=True, nullable=False, index=True)  # Format: ADM-000001
    encounter_id = Column(String(36), ForeignKey("encounters.id"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    attending_doctor_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    assigned_bed_id = Column(String(36), ForeignKey("beds.id"), nullable=True, index=True)
    admission_type = Column(String(50), default="EMERGENCY", nullable=False)  # EMERGENCY, ELECTIVE, TRANSFER, OBSERVATION
    status = Column(String(50), default="ACTIVE", nullable=False, index=True)  # ACTIVE, DISCHARGED, TRANSFERRED, CANCELLED
    reason = Column(Text, nullable=False)
    diagnosis_notes = Column(Text, nullable=True)
    admitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    discharged_at = Column(DateTime, nullable=True)
    admitted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    encounter = relationship("Encounter", back_populates="admissions")
    patient = relationship("Patient", back_populates="admissions")
    branch = relationship("Branch")
    department = relationship("Department")
    attending_doctor = relationship("User", foreign_keys=[attending_doctor_id])
    admitting_user = relationship("User", foreign_keys=[admitted_by])
    bed = relationship("Bed", back_populates="admissions", foreign_keys=[assigned_bed_id])
    vitals = relationship("PatientVital", back_populates="admission")
    clinical_notes = relationship("ClinicalNote", back_populates="admission")
