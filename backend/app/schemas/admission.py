from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class AdmissionCreate(BaseModel):
    patient_id: str
    branch_id: str
    department_id: Optional[str] = None
    attending_doctor_id: str
    assigned_bed_id: Optional[str] = None
    admission_type: str = "EMERGENCY"  # EMERGENCY, ELECTIVE, TRANSFER, OBSERVATION
    reason: str
    diagnosis_notes: Optional[str] = None

class AdmissionDischarge(BaseModel):
    discharge_notes: Optional[str] = None

class AdmissionOut(BaseModel):
    id: str
    admission_number: str
    encounter_id: str
    patient_id: str
    branch_id: str
    department_id: Optional[str] = None
    attending_doctor_id: str
    assigned_bed_id: Optional[str] = None
    admission_type: str
    status: str
    reason: str
    diagnosis_notes: Optional[str] = None
    admitted_at: datetime
    discharged_at: Optional[datetime] = None
    admitted_by: str
    created_at: datetime

    # Enriched fields
    patient_name: Optional[str] = None
    patient_code: Optional[str] = None
    doctor_name: Optional[str] = None
    bed_number: Optional[str] = None
    ward_name: Optional[str] = None
    branch_name: Optional[str] = None

    class Config:
        from_attributes = True
