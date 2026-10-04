import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(50), unique=True, nullable=False, index=True)  # Format: ANV-000001
    first_name = Column(String(100), nullable=False, index=True)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False, index=True)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20), nullable=False)  # MALE, FEMALE, OTHER
    blood_group = Column(String(10), nullable=True)  # A+, B+, O+, AB+, etc.
    mobile = Column(String(30), nullable=False, index=True)
    email = Column(String(150), nullable=True)
    address = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    consent_status = Column(String(50), default="GRANTED")  # GRANTED, WITHDRAWN, PENDING
    registered_branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    registered_branch = relationship("Branch")
    contacts = relationship("PatientContact", back_populates="patient", cascade="all, delete-orphan")
    allergies = relationship("PatientAllergy", back_populates="patient", cascade="all, delete-orphan")
    conditions = relationship("PatientCondition", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("PatientMedication", back_populates="patient", cascade="all, delete-orphan")
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")
    admissions = relationship("Admission", back_populates="patient")
    vitals = relationship("PatientVital", back_populates="patient", cascade="all, delete-orphan")
    clinical_notes = relationship("ClinicalNote", back_populates="patient", cascade="all, delete-orphan")
    events = relationship("PatientEvent", back_populates="patient", cascade="all, delete-orphan")

class PatientContact(Base):
    __tablename__ = "patient_contacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # Spouse, Parent, Child, Sibling, Other
    phone = Column(String(30), nullable=False)
    is_primary = Column(Boolean, default=True)

    patient = relationship("Patient", back_populates="contacts")

class PatientAllergy(Base):
    __tablename__ = "patient_allergies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    allergen = Column(String(150), nullable=False)
    reaction = Column(String(255), nullable=True)
    severity = Column(String(50), default="MODERATE")  # MILD, MODERATE, SEVERE, LIFE_THREATENING
    status = Column(String(50), default="ACTIVE")  # ACTIVE, RESOLVED, INACTIVE
    recorded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="allergies")
    recorder = relationship("User")

class PatientCondition(Base):
    __tablename__ = "patient_conditions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    condition_name = Column(String(200), nullable=False)
    icd_code = Column(String(50), nullable=True)
    status = Column(String(50), default="ACTIVE")  # ACTIVE, RECURRENCE, RELAPSE, REMISSION, RESOLVED
    onset_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="conditions")
    recorder = relationship("User")

class PatientMedication(Base):
    __tablename__ = "patient_medications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    medication_name = Column(String(200), nullable=False)
    dose = Column(String(100), nullable=False)  # e.g., 500mg
    route = Column(String(50), default="ORAL")  # ORAL, IV, IM, TOPICAL, INHALATION
    frequency = Column(String(50), default="BID")  # OD, BID, TID, QID, PRN, STAT
    status = Column(String(50), default="ACTIVE")  # ACTIVE, DISCONTINUED, COMPLETED
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    recorded_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    patient = relationship("Patient", back_populates="medications")
    recorder = relationship("User")
