import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class LabTestCatalog(Base):
    __tablename__ = "lab_test_catalog"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    specimen_type = Column(String(100), nullable=True)
    reference_range = Column(String(255), nullable=True)
    unit = Column(String(50), nullable=True)
    price = Column(Float, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)


class LabOrder(Base):
    __tablename__ = "lab_orders"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = Column(String(36), ForeignKey("encounters.id"), nullable=True, index=True)
    admission_id = Column(String(36), ForeignKey("admissions.id"), nullable=True, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False, index=True)
    test_id = Column(String(36), ForeignKey("lab_test_catalog.id"), nullable=False)
    ordering_doctor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    assigned_technician_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    status = Column(String(50), nullable=False, default="LAB_ORDERED", index=True)
    priority = Column(String(30), nullable=False, default="ROUTINE")
    clinical_notes = Column(Text, nullable=True)
    sample_collected_at = Column(DateTime, nullable=True)
    sample_collected_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)
    patient = relationship("Patient")
    test = relationship("LabTestCatalog")
    ordering_doctor = relationship("User", foreign_keys=[ordering_doctor_id])
    assigned_technician = relationship("User", foreign_keys=[assigned_technician_id])
    result = relationship("LabResult", back_populates="order", uselist=False, cascade="all, delete-orphan")


class LabResult(Base):
    __tablename__ = "lab_results"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), ForeignKey("lab_orders.id"), nullable=False, unique=True, index=True)
    result_value = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=True)
    reference_range = Column(String(255), nullable=True)
    flag = Column(String(30), nullable=False, default="NORMAL")
    comments = Column(Text, nullable=True)
    entered_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    verified_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    entered_at = Column(DateTime, nullable=False, default=now_utc)
    verified_at = Column(DateTime, nullable=True)
    report_status = Column(String(30), nullable=False, default="RESULT_READY")
    order = relationship("LabOrder", back_populates="result")
    entered_by = relationship("User", foreign_keys=[entered_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])


class Medicine(Base):
    __tablename__ = "medicines"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), nullable=False, unique=True, index=True)
    generic_name = Column(String(200), nullable=False, index=True)
    brand_name = Column(String(200), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    strength = Column(String(100), nullable=True)
    dosage_form = Column(String(100), nullable=False)
    reorder_threshold = Column(Integer, nullable=False, default=10)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)


class InventoryBatch(Base):
    __tablename__ = "inventory_batches"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    medicine_id = Column(String(36), ForeignKey("medicines.id"), nullable=False, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False, index=True)
    batch_number = Column(String(100), nullable=False, index=True)
    expiry_date = Column(Date, nullable=False, index=True)
    quantity_on_hand = Column(Integer, nullable=False, default=0)
    unit_price = Column(Float, nullable=False, default=0)
    supplier = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    medicine = relationship("Medicine")


class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    prescription_number = Column(String(50), nullable=False, unique=True, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = Column(String(36), ForeignKey("encounters.id"), nullable=True, index=True)
    admission_id = Column(String(36), ForeignKey("admissions.id"), nullable=True, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False, index=True)
    prescribed_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(30), nullable=False, default="PRESCRIBED", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    patient = relationship("Patient")
    prescribed_by = relationship("User", foreign_keys=[prescribed_by_id])
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    prescription_id = Column(String(36), ForeignKey("prescriptions.id"), nullable=False, index=True)
    medicine_id = Column(String(36), ForeignKey("medicines.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    dosage = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    duration_days = Column(Integer, nullable=True)
    status = Column(String(30), nullable=False, default="PENDING")
    dispensed_quantity = Column(Integer, nullable=False, default=0)
    prescription = relationship("Prescription", back_populates="items")
    medicine = relationship("Medicine")


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    batch_id = Column(String(36), ForeignKey("inventory_batches.id"), nullable=False, index=True)
    prescription_item_id = Column(String(36), ForeignKey("prescription_items.id"), nullable=True, index=True)
    movement_type = Column(String(30), nullable=False)
    quantity = Column(Integer, nullable=False)
    performed_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    occurred_at = Column(DateTime, nullable=False, default=now_utc)
    notes = Column(Text, nullable=True)
    batch = relationship("InventoryBatch")


class PatientAccount(Base):
    __tablename__ = "patient_accounts"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, unique=True, index=True)
    balance = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    patient = relationship("Patient")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_number = Column(String(50), nullable=False, unique=True, index=True)
    patient_account_id = Column(String(36), ForeignKey("patient_accounts.id"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    encounter_id = Column(String(36), ForeignKey("encounters.id"), nullable=True)
    admission_id = Column(String(36), ForeignKey("admissions.id"), nullable=True)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="OPEN", index=True)
    subtotal = Column(Float, nullable=False, default=0)
    discount_amount = Column(Float, nullable=False, default=0)
    tax_amount = Column(Float, nullable=False, default=0)
    total_amount = Column(Float, nullable=False, default=0)
    paid_amount = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    patient = relationship("Patient")
    account = relationship("PatientAccount")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False, index=True)
    charge_type = Column(String(50), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    source_entity_type = Column(String(100), nullable=True)
    source_entity_id = Column(String(36), nullable=True, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    invoice = relationship("Invoice", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=False)
    reference_number = Column(String(100), nullable=True)
    received_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    received_at = Column(DateTime, nullable=False, default=now_utc)
    status = Column(String(30), nullable=False, default="COMPLETED")
    invoice = relationship("Invoice", back_populates="payments")
