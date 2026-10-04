from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel

class VitalCreate(BaseModel):
    # Patient identity comes from the URL; retaining an optional body field is
    # backward compatible with older API clients.
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    admission_id: Optional[str] = None
    heart_rate: Optional[int] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    respiratory_rate: Optional[int] = None
    spo2: Optional[float] = None
    temperature: Optional[float] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None

class VitalOut(BaseModel):
    id: str
    patient_id: str
    encounter_id: Optional[str] = None
    admission_id: Optional[str] = None
    recorded_by: str
    recorded_by_name: Optional[str] = None
    timestamp: datetime
    heart_rate: Optional[int] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    respiratory_rate: Optional[int] = None
    spo2: Optional[float] = None
    temperature: Optional[float] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class ClinicalNoteCreate(BaseModel):
    patient_id: Optional[str] = None
    encounter_id: Optional[str] = None
    admission_id: Optional[str] = None
    note_type: str  # PROGRESS_NOTE, NURSING_NOTE, INITIAL_ASSESSMENT, FOLLOW_UP, DISCHARGE_PLANNING
    title: str
    content: str

class ClinicalNoteUpdate(BaseModel):
    note_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None

class ClinicalNoteOut(BaseModel):
    id: str
    patient_id: str
    encounter_id: Optional[str] = None
    admission_id: Optional[str] = None
    author_id: str
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    note_type: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PatientEventOut(BaseModel):
    id: str
    patient_id: str
    encounter_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    event_type: str
    title: str
    description: Optional[str] = None
    source_module: str
    timestamp: datetime
    metadata_json: Optional[Any] = None

    class Config:
        from_attributes = True
