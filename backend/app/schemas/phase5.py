from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field


class LabTestCreate(BaseModel):
    code: str
    name: str
    category: str
    specimen_type: str | None = None
    reference_range: str | None = None
    unit: str | None = None
    price: float = Field(ge=0)


class LabOrderCreate(BaseModel):
    patient_id: str
    branch_id: str
    test_id: str
    encounter_id: str | None = None
    admission_id: str | None = None
    priority: Literal["ROUTINE", "URGENT", "STAT"] = "ROUTINE"
    clinical_notes: str | None = None


class LabResultCreate(BaseModel):
    result_value: str
    unit: str | None = None
    reference_range: str | None = None
    flag: Literal["NORMAL", "LOW", "HIGH", "ABNORMAL", "CRITICAL"] = "NORMAL"
    comments: str | None = None


class MedicineCreate(BaseModel):
    code: str
    generic_name: str
    brand_name: str | None = None
    category: str | None = None
    strength: str | None = None
    dosage_form: str
    reorder_threshold: int = Field(default=10, ge=0)


class InventoryBatchCreate(BaseModel):
    medicine_id: str
    branch_id: str
    batch_number: str
    expiry_date: date
    quantity_on_hand: int = Field(ge=0)
    unit_price: float = Field(ge=0)
    supplier: str | None = None


class PrescriptionItemCreate(BaseModel):
    medicine_id: str
    quantity: int = Field(gt=0)
    dosage: str | None = None
    frequency: str | None = None
    duration_days: int | None = Field(default=None, gt=0)


class PrescriptionCreate(BaseModel):
    patient_id: str
    branch_id: str
    items: list[PrescriptionItemCreate] = Field(min_length=1)
    encounter_id: str | None = None
    admission_id: str | None = None
    notes: str | None = None


class DispenseCreate(BaseModel):
    batch_id: str
    quantity: int = Field(gt=0)


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    payment_method: Literal["CASH", "CARD", "UPI", "BANK_TRANSFER", "INSURANCE"]
    reference_number: str | None = None
