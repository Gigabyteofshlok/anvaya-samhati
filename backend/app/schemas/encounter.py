from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class EncounterCreate(BaseModel):
    patient_id: str
    branch_id: str
    department_id: Optional[str] = None
    encounter_type: str = "IPD"  # OPD, IPD, EMERGENCY, FOLLOW_UP, OBSERVATION
    attending_doctor_id: Optional[str] = None
    reason: Optional[str] = None

class EncounterUpdate(BaseModel):
    status: Optional[str] = None  # ACTIVE, COMPLETED, CANCELLED
    ended_at: Optional[datetime] = None
    attending_doctor_id: Optional[str] = None
    reason: Optional[str] = None

class EncounterOut(BaseModel):
    id: str
    patient_id: str
    branch_id: str
    department_id: Optional[str] = None
    encounter_type: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    attending_doctor_id: Optional[str] = None
    attending_doctor_name: Optional[str] = None
    branch_name: Optional[str] = None
    department_name: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
