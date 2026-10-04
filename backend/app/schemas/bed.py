from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class BedOut(BaseModel):
    id: str
    bed_number: str
    room_id: str
    ward_id: str
    branch_id: str
    bed_type: str
    status: str
    is_isolation: bool
    maintenance_notes: Optional[str] = None
    tariff_rate: float
    current_admission_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Denormalized / enriched display fields
    branch_name: Optional[str] = None
    ward_name: Optional[str] = None
    room_number: Optional[str] = None
    current_patient_name: Optional[str] = None
    current_patient_id: Optional[str] = None
    current_admission_number: Optional[str] = None
    current_doctor_name: Optional[str] = None
    admitted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BedCreate(BaseModel):
    branch_id: str
    ward_id: str
    room_id: str
    bed_number: str
    bed_type: str = "STANDARD"
    is_isolation: bool = False
    tariff_rate: float = 0.0

class BedStatusUpdate(BaseModel):
    new_status: str
    notes: Optional[str] = None

class BedAssignRequest(BaseModel):
    admission_id: str
    notes: Optional[str] = None

class BedOccupancyStats(BaseModel):
    total_beds: int
    occupied: int
    available: int
    reserved: int
    cleaning: int
    maintenance: int
    isolation: int
    occupancy_rate_pct: float
