from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class BranchOccupancyOut(BaseModel):
    branch_id: str
    branch_name: str
    branch_code: str
    total_beds: int
    occupied_beds: int
    available_beds: int
    cleaning_beds: int
    maintenance_beds: int
    occupancy_pct: float


class WardOccupancyOut(BaseModel):
    ward_id: str
    ward_name: str
    branch_name: str
    total_beds: int
    occupied_beds: int
    occupancy_pct: float


class AdmissionTrendOut(BaseModel):
    date: str
    label: str
    admissions: int
    discharges: int


class RecentAdmissionOut(BaseModel):
    id: str
    admission_number: str
    patient_name: str
    patient_code: str
    doctor_name: str
    bed_number: Optional[str] = None
    ward_name: Optional[str] = None
    branch_name: str
    admission_type: str
    status: str
    admitted_at: datetime


class RecentEventOut(BaseModel):
    id: str
    event_type: str
    title: str
    description: Optional[str] = None
    patient_name: Optional[str] = None
    timestamp: datetime


class DashboardSummaryOut(BaseModel):
    total_beds: int
    occupied_beds: int
    available_beds: int
    reserved_beds: int
    cleaning_beds: int
    maintenance_beds: int
    isolation_beds: int
    active_admissions: int
    today_admissions: int
    today_discharges: int
    today_registrations: int
    total_patients: int
    occupancy_rate_pct: float
    active_encounters: int = 0
    pending_lab_orders: int = 0
    pending_lab_results: int = 0
    low_stock_items: int = 0
    pending_prescriptions: int = 0
    bills: int = 0
    payments: int = 0
    outstanding_amount: float = 0.0
    insurance_claims: int = 0
    branches: List[BranchOccupancyOut] = []
    wards: List[WardOccupancyOut] = []
    admission_trend: List[AdmissionTrendOut] = []
    recent_admissions: List[RecentAdmissionOut] = []
    recent_events: List[RecentEventOut] = []
