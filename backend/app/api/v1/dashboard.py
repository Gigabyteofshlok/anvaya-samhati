from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.admission import Admission
from app.models.bed import Bed, BedStatus
from app.models.clinical import PatientEvent
from app.models.identity import User
from app.models.organization import Branch
from app.models.patient import Patient
from app.models.encounter import Encounter
from app.models.phase5 import InventoryBatch, Invoice, LabOrder, Payment, Prescription
from app.models.phase6 import InsuranceClaim
from app.schemas.dashboard import (
    AdmissionTrendOut, BranchOccupancyOut, DashboardSummaryOut,
    RecentAdmissionOut, RecentEventOut, WardOccupancyOut,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _bed_status_counts(db: Session, branch_id: Optional[str] = None) -> dict[str, int]:
    query = db.query(Bed.status, func.count(Bed.id)).group_by(Bed.status)
    if branch_id:
        query = query.filter(Bed.branch_id == branch_id)
    return {status: count for status, count in query.all()}


@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    branch_id: Optional[str] = Query(None, description="Limit operational metrics to a branch."),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard.view")),
):
    """Return database-backed operational indicators for the Command Center."""
    today = date.today()
    today_start = datetime.combine(today, time.min)
    tomorrow_start = today_start + timedelta(days=1)

    status_map = _bed_status_counts(db, branch_id)
    total_beds = sum(status_map.values())
    occupied_beds = status_map.get(BedStatus.OCCUPIED.value, 0)
    available_beds = status_map.get(BedStatus.AVAILABLE.value, 0)
    reserved_beds = status_map.get(BedStatus.RESERVED.value, 0)
    cleaning_beds = status_map.get(BedStatus.CLEANING.value, 0)
    maintenance_beds = status_map.get(BedStatus.MAINTENANCE.value, 0)
    isolation_beds = status_map.get(BedStatus.ISOLATION.value, 0)

    admission_scope = db.query(Admission)
    patient_scope = db.query(Patient)
    if branch_id:
        admission_scope = admission_scope.filter(Admission.branch_id == branch_id)
        patient_scope = patient_scope.filter(Patient.registered_branch_id == branch_id)

    active_admissions = admission_scope.filter(Admission.status == "ACTIVE").count()
    today_admissions = admission_scope.filter(
        Admission.admitted_at >= today_start, Admission.admitted_at < tomorrow_start
    ).count()
    today_discharges = admission_scope.filter(
        Admission.discharged_at >= today_start, Admission.discharged_at < tomorrow_start
    ).count()
    today_registrations = patient_scope.filter(
        Patient.created_at >= today_start, Patient.created_at < tomorrow_start
    ).count()
    total_patients = patient_scope.count()
    occupancy_pct = round((occupied_beds / total_beds * 100), 1) if total_beds else 0.0
    active_encounters = db.query(Encounter).filter(Encounter.status == "ACTIVE").count()
    lab_scope = db.query(LabOrder)
    if branch_id: lab_scope = lab_scope.filter(LabOrder.branch_id == branch_id)
    pending_lab_orders = lab_scope.filter(LabOrder.status.in_(["LAB_ORDERED", "SAMPLE_PENDING"])).count()
    pending_lab_results = lab_scope.filter(LabOrder.status.in_(["SAMPLE_COLLECTED", "PROCESSING", "RESULT_READY"])).count()
    inventory_scope = db.query(InventoryBatch)
    if branch_id: inventory_scope = inventory_scope.filter(InventoryBatch.branch_id == branch_id)
    low_stock_items = sum(1 for batch in inventory_scope.all() if batch.quantity_on_hand <= batch.medicine.reorder_threshold)
    prescription_scope = db.query(Prescription)
    if branch_id: prescription_scope = prescription_scope.filter(Prescription.branch_id == branch_id)
    pending_prescriptions = prescription_scope.filter(Prescription.status.in_(["PRESCRIBED", "PARTIALLY_DISPENSED"])).count()
    invoice_scope = db.query(Invoice)
    if branch_id: invoice_scope = invoice_scope.filter(Invoice.branch_id == branch_id)
    invoices = invoice_scope.all()
    bills = len(invoices)
    outstanding_amount = round(sum(float(item.total_amount) - float(item.paid_amount) for item in invoices), 2)
    payment_scope = db.query(Payment)
    payments = payment_scope.count()
    insurance_claims = db.query(InsuranceClaim).count()

    branch_query = db.query(Branch).filter(Branch.is_active.is_(True)).order_by(Branch.name)
    if branch_id:
        branch_query = branch_query.filter(Branch.id == branch_id)
    branch_stats = []
    for branch in branch_query.all():
        counts = _bed_status_counts(db, branch.id)
        branch_total = sum(counts.values())
        branch_occupied = counts.get(BedStatus.OCCUPIED.value, 0)
        branch_stats.append(BranchOccupancyOut(
            branch_id=branch.id, branch_name=branch.name, branch_code=branch.code,
            total_beds=branch_total, occupied_beds=branch_occupied,
            available_beds=counts.get(BedStatus.AVAILABLE.value, 0),
            cleaning_beds=counts.get(BedStatus.CLEANING.value, 0),
            maintenance_beds=counts.get(BedStatus.MAINTENANCE.value, 0),
            occupancy_pct=round((branch_occupied / branch_total * 100), 1) if branch_total else 0.0,
        ))

    ward_query = db.query(Bed).options(joinedload(Bed.ward), joinedload(Bed.branch))
    if branch_id:
        ward_query = ward_query.filter(Bed.branch_id == branch_id)
    ward_counts: dict[str, dict] = {}
    for bed in ward_query.all():
        if not bed.ward:
            continue
        entry = ward_counts.setdefault(bed.ward_id, {
            "ward_id": bed.ward_id, "ward_name": bed.ward.name,
            "branch_name": bed.branch.name if bed.branch else "Unknown",
            "total_beds": 0, "occupied_beds": 0,
        })
        entry["total_beds"] += 1
        if bed.status == BedStatus.OCCUPIED.value:
            entry["occupied_beds"] += 1
    wards = [WardOccupancyOut(
        **entry,
        occupancy_pct=round((entry["occupied_beds"] / entry["total_beds"] * 100), 1)
        if entry["total_beds"] else 0.0,
    ) for entry in ward_counts.values()]
    wards.sort(key=lambda ward: (-ward.occupancy_pct, ward.ward_name))

    trend = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=1)
        daily_admissions = admission_scope.filter(
            Admission.admitted_at >= day_start, Admission.admitted_at < day_end
        ).count()
        daily_discharges = admission_scope.filter(
            Admission.discharged_at >= day_start, Admission.discharged_at < day_end
        ).count()
        trend.append(AdmissionTrendOut(
            date=day.isoformat(), label=day.strftime("%a"),
            admissions=daily_admissions, discharges=daily_discharges,
        ))

    recent_query = db.query(Admission).filter(Admission.status == "ACTIVE").options(
        joinedload(Admission.patient), joinedload(Admission.attending_doctor),
        joinedload(Admission.branch), joinedload(Admission.bed).joinedload(Bed.ward),
    )
    if branch_id:
        recent_query = recent_query.filter(Admission.branch_id == branch_id)
    recent_admissions = [RecentAdmissionOut(
        id=admission.id, admission_number=admission.admission_number,
        patient_name=f"{admission.patient.first_name} {admission.patient.last_name}" if admission.patient else "Unknown",
        patient_code=admission.patient.patient_id if admission.patient else "N/A",
        doctor_name=admission.attending_doctor.full_name if admission.attending_doctor else "Unassigned",
        bed_number=admission.bed.bed_number if admission.bed else "Unassigned",
        ward_name=admission.bed.ward.name if admission.bed and admission.bed.ward else "N/A",
        branch_name=admission.branch.name if admission.branch else "N/A",
        admission_type=admission.admission_type, status=admission.status,
        admitted_at=admission.admitted_at,
    ) for admission in recent_query.order_by(Admission.admitted_at.desc()).limit(8).all()]

    event_query = db.query(PatientEvent).options(joinedload(PatientEvent.patient))
    if branch_id:
        event_query = event_query.join(Patient).filter(Patient.registered_branch_id == branch_id)
    recent_events = [RecentEventOut(
        id=event.id, event_type=event.event_type, title=event.title,
        description=event.description,
        patient_name=f"{event.patient.first_name} {event.patient.last_name}" if event.patient else None,
        timestamp=event.timestamp,
    ) for event in event_query.order_by(PatientEvent.timestamp.desc()).limit(8).all()]

    return DashboardSummaryOut(
        total_beds=total_beds, occupied_beds=occupied_beds, available_beds=available_beds,
        reserved_beds=reserved_beds, cleaning_beds=cleaning_beds,
        maintenance_beds=maintenance_beds, isolation_beds=isolation_beds,
        active_admissions=active_admissions, today_admissions=today_admissions,
        today_discharges=today_discharges, today_registrations=today_registrations,
        total_patients=total_patients, occupancy_rate_pct=occupancy_pct,
        active_encounters=active_encounters, pending_lab_orders=pending_lab_orders,
        pending_lab_results=pending_lab_results, low_stock_items=low_stock_items,
        pending_prescriptions=pending_prescriptions, bills=bills, payments=payments,
        outstanding_amount=outstanding_amount, insurance_claims=insurance_claims,
        branches=branch_stats, wards=wards, admission_trend=trend,
        recent_admissions=recent_admissions, recent_events=recent_events,
    )
