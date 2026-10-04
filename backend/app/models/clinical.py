import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class PatientVital(Base):
    __tablename__ = "patient_vitals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = Column(String(36), ForeignKey("encounters.id"), nullable=True, index=True)
    admission_id = Column(String(36), ForeignKey("admissions.id"), nullable=True, index=True)
    recorded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    heart_rate = Column(Integer, nullable=True)           # bpm
    bp_systolic = Column(Integer, nullable=True)          # mmHg
    bp_diastolic = Column(Integer, nullable=True)         # mmHg
    respiratory_rate = Column(Integer, nullable=True)      # breaths/min
    spo2 = Column(Float, nullable=True)                   # %
    temperature = Column(Float, nullable=True)            # Fahrenheit
    weight_kg = Column(Float, nullable=True)              # kg
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="vitals")
    encounter = relationship("Encounter", back_populates="vitals")
    admission = relationship("Admission", back_populates="vitals")
    recorder = relationship("User", back_populates="vitals_recorded")

class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = Column(String(36), ForeignKey("encounters.id"), nullable=True, index=True)
    admission_id = Column(String(36), ForeignKey("admissions.id"), nullable=True, index=True)
    author_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    note_type = Column(String(50), nullable=False)  # PROGRESS_NOTE, NURSING_NOTE, INITIAL_ASSESSMENT, FOLLOW_UP, DISCHARGE_PLANNING
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="clinical_notes")
    encounter = relationship("Encounter", back_populates="clinical_notes")
    admission = relationship("Admission", back_populates="clinical_notes")
    author = relationship("User", back_populates="clinical_notes")

class PatientEvent(Base):
    __tablename__ = "patient_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = Column(String(36), ForeignKey("encounters.id"), nullable=True, index=True)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    event_type = Column(String(100), nullable=False, index=True)  # PATIENT_REGISTERED, ENCOUNTER_CREATED, PATIENT_ADMITTED, BED_ASSIGNED, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    source_module = Column(String(100), default="CLINICAL")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)

    patient = relationship("Patient", back_populates="events")
    encounter = relationship("Encounter", back_populates="events")
    actor = relationship("User")
