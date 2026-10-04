import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class PatientPortalLink(Base):
    __tablename__ = "patient_portal_links"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, unique=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    patient = relationship("Patient")
    user = relationship("User")


class LabTestComponent(Base):
    __tablename__ = "lab_test_components"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    test_id = Column(String(36), ForeignKey("lab_test_catalog.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    unit = Column(String(50), nullable=True)
    reference_low = Column(Float, nullable=True)
    reference_high = Column(Float, nullable=True)
    reference_text = Column(String(255), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_numeric = Column(Boolean, nullable=False, default=True)
    test = relationship("LabTestCatalog")


class LabOrderItem(Base):
    __tablename__ = "lab_order_items"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), ForeignKey("lab_orders.id"), nullable=False, index=True)
    test_id = Column(String(36), ForeignKey("lab_test_catalog.id"), nullable=False)
    status = Column(String(30), nullable=False, default="PENDING")
    created_at = Column(DateTime, nullable=False, default=now_utc)
    order = relationship("LabOrder")
    test = relationship("LabTestCatalog")


class LabResultValue(Base):
    __tablename__ = "lab_result_values"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    result_id = Column(String(36), ForeignKey("lab_results.id"), nullable=False, index=True)
    component_id = Column(String(36), ForeignKey("lab_test_components.id"), nullable=False)
    value_text = Column(String(255), nullable=False)
    numeric_value = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    reference_range = Column(String(255), nullable=True)
    flag = Column(String(30), nullable=False, default="NORMAL")
    notes = Column(Text, nullable=True)
    result = relationship("LabResult")
    component = relationship("LabTestComponent")


class InsuranceProvider(Base):
    __tablename__ = "insurance_providers"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    tpa_name = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(150), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)


class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    provider_id = Column(String(36), ForeignKey("insurance_providers.id"), nullable=False)
    policy_number = Column(String(100), nullable=False, unique=True, index=True)
    member_id = Column(String(100), nullable=True)
    coverage_amount = Column(Float, nullable=False, default=0)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=now_utc)
    patient = relationship("Patient")
    provider = relationship("InsuranceProvider")


class PreAuthorization(Base):
    __tablename__ = "preauthorizations"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_number = Column(String(50), nullable=False, unique=True, index=True)
    policy_id = Column(String(36), ForeignKey("insurance_policies.id"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    admission_id = Column(String(36), ForeignKey("admissions.id"), nullable=True)
    requested_amount = Column(Float, nullable=False)
    approved_amount = Column(Float, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="DRAFT", index=True)
    notes = Column(Text, nullable=True)
    requested_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewed_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    reviewed_at = Column(DateTime, nullable=True)
    policy = relationship("InsurancePolicy")
    patient = relationship("Patient")


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_number = Column(String(50), nullable=False, unique=True, index=True)
    policy_id = Column(String(36), ForeignKey("insurance_policies.id"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    admission_id = Column(String(36), ForeignKey("admissions.id"), nullable=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    status = Column(String(30), nullable=False, default="DRAFT", index=True)
    submitted_amount = Column(Float, nullable=False, default=0)
    approved_amount = Column(Float, nullable=False, default=0)
    rejected_amount = Column(Float, nullable=False, default=0)
    documents_json = Column(JSON, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewed_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)
    policy = relationship("InsurancePolicy")
    patient = relationship("Patient")
    invoice = relationship("Invoice")
    items = relationship("InsuranceClaimItem", back_populates="claim", cascade="all, delete-orphan")


class InsuranceClaimItem(Base):
    __tablename__ = "insurance_claim_items"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("insurance_claims.id"), nullable=False, index=True)
    invoice_item_id = Column(String(36), ForeignKey("invoice_items.id"), nullable=True)
    description = Column(String(255), nullable=False)
    claimed_amount = Column(Float, nullable=False)
    approved_amount = Column(Float, nullable=False, default=0)
    rejected_amount = Column(Float, nullable=False, default=0)
    claim = relationship("InsuranceClaim", back_populates="items")


class Discharge(Base):
    __tablename__ = "discharges"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    admission_id = Column(String(36), ForeignKey("admissions.id"), nullable=False, unique=True, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    attending_doctor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(40), nullable=False, default="DISCHARGE_INITIATED", index=True)
    discharge_reason = Column(String(255), nullable=True)
    diagnosis_summary = Column(Text, nullable=True)
    clinical_summary = Column(Text, nullable=True)
    clinical_cleared = Column(Boolean, nullable=False, default=False)
    pending_results_checked = Column(Boolean, nullable=False, default=False)
    billing_cleared = Column(Boolean, nullable=False, default=False)
    insurance_cleared = Column(Boolean, nullable=False, default=False)
    initiated_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    approved_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    initiated_at = Column(DateTime, nullable=False, default=now_utc)
    completed_at = Column(DateTime, nullable=True)
    admission = relationship("Admission")
    patient = relationship("Patient")
    medications = relationship("DischargeMedication", back_populates="discharge", cascade="all, delete-orphan")
    instructions = relationship("DischargeInstruction", back_populates="discharge", cascade="all, delete-orphan")


class DischargeMedication(Base):
    __tablename__ = "discharge_medications"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    discharge_id = Column(String(36), ForeignKey("discharges.id"), nullable=False, index=True)
    medicine_name = Column(String(200), nullable=False)
    dosage = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    duration_days = Column(Integer, nullable=True)
    instructions = Column(Text, nullable=True)
    discharge = relationship("Discharge", back_populates="medications")


class DischargeInstruction(Base):
    __tablename__ = "discharge_instructions"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    discharge_id = Column(String(36), ForeignKey("discharges.id"), nullable=False, index=True)
    instruction_type = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    discharge = relationship("Discharge", back_populates="instructions")
