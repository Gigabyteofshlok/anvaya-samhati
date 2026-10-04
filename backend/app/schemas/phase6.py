from datetime import date
from pydantic import BaseModel, Field


class LabComponentCreate(BaseModel):
    code: str
    name: str
    unit: str | None = None
    reference_low: float | None = None
    reference_high: float | None = None
    reference_text: str | None = None
    display_order: int = 0
    is_numeric: bool = True


class LabResultValueIn(BaseModel):
    component_id: str
    value_text: str
    numeric_value: float | None = None
    notes: str | None = None


class StructuredResultSave(BaseModel):
    values: list[LabResultValueIn] = Field(min_length=1)
    complete: bool = False
    comments: str | None = None


class ProviderCreate(BaseModel):
    name: str
    code: str
    tpa_name: str | None = None
    phone: str | None = None
    email: str | None = None


class PolicyCreate(BaseModel):
    patient_id: str
    provider_id: str
    policy_number: str
    member_id: str | None = None
    coverage_amount: float = Field(ge=0)
    valid_from: date
    valid_to: date


class PreAuthorizationCreate(BaseModel):
    policy_id: str
    patient_id: str
    admission_id: str | None = None
    requested_amount: float = Field(gt=0)
    notes: str | None = None


class ClaimItemIn(BaseModel):
    description: str
    claimed_amount: float = Field(gt=0)
    invoice_item_id: str | None = None


class ClaimCreate(BaseModel):
    policy_id: str
    patient_id: str
    invoice_id: str | None = None
    admission_id: str | None = None
    items: list[ClaimItemIn] = Field(min_length=1)


class StatusDecision(BaseModel):
    status: str
    approved_amount: float = Field(default=0, ge=0)
    rejected_amount: float = Field(default=0, ge=0)
    notes: str | None = None


class DischargeMedicationIn(BaseModel):
    medicine_name: str
    dosage: str | None = None
    frequency: str | None = None
    duration_days: int | None = None
    instructions: str | None = None


class DischargeInstructionIn(BaseModel):
    instruction_type: str
    content: str


class DischargeCreate(BaseModel):
    admission_id: str
    discharge_reason: str | None = None
    diagnosis_summary: str | None = None
    clinical_summary: str | None = None
    medications: list[DischargeMedicationIn] = []
    instructions: list[DischargeInstructionIn] = []


class DischargeComplete(BaseModel):
    clinical_cleared: bool
    pending_results_checked: bool
    billing_cleared: bool
    insurance_cleared: bool
