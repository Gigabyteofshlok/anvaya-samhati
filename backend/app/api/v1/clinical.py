from datetime import date, datetime, time, timedelta
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.core.database import get_db
from app.models.admission import Admission
from app.models.bed import Bed
from app.models.patient import Patient
from app.models.encounter import Encounter
from app.models.clinical import PatientVital, ClinicalNote
from app.models.identity import User
from app.api.deps import get_current_user, require_permission

router = APIRouter(prefix="/clinical", tags=["Clinical Workspace"])

@router.get("/overview")
def get_doctor_overview(
    branch_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clinical.view"))
) -> Any:
    # If doctor, prioritize their assigned patients; otherwise show active admissions
    query = db.query(Admission).filter(Admission.status == "ACTIVE").options(
        joinedload(Admission.patient).joinedload(Patient.allergies),
        joinedload(Admission.patient).joinedload(Patient.conditions),
        joinedload(Admission.bed).joinedload(Bed.ward),
        joinedload(Admission.attending_doctor)
    )

    if current_user.role == "DOCTOR":
        query = query.filter(Admission.attending_doctor_id == current_user.id)
    elif branch_id:
        query = query.filter(Admission.branch_id == branch_id)

    active_admissions = query.order_by(desc(Admission.admitted_at)).all()

    patient_rows = []
    for adm in active_admissions:
        p = adm.patient
        # Fetch latest vital
        latest_vital = db.query(PatientVital).filter(
            PatientVital.patient_id == p.id
        ).order_by(desc(PatientVital.timestamp)).first()

        vital_summary = None
        if latest_vital:
            vital_summary = {
                "heart_rate": latest_vital.heart_rate,
                "bp": f"{latest_vital.bp_systolic}/{latest_vital.bp_diastolic}" if latest_vital.bp_systolic and latest_vital.bp_diastolic else None,
                "spo2": latest_vital.spo2,
                "temperature": latest_vital.temperature,
                "timestamp": latest_vital.timestamp.isoformat()
            }

        # Latest note
        latest_note = db.query(ClinicalNote).filter(
            ClinicalNote.patient_id == p.id
        ).order_by(desc(ClinicalNote.created_at)).first()

        allergies_list = [a.allergen for a in p.allergies if a.status == "ACTIVE"] if p.allergies else []
        conditions_list = [c.condition_name for c in p.conditions if c.status == "ACTIVE"] if p.conditions else []

        patient_rows.append({
            "admission_id": adm.id,
            "admission_number": adm.admission_number,
            "patient_id": p.id,
            "patient_code": p.patient_id,
            "patient_name": f"{p.first_name} {p.last_name}",
            "gender": p.gender,
            "date_of_birth": p.date_of_birth.isoformat(),
            "blood_group": p.blood_group,
            "bed_number": adm.bed.bed_number if adm.bed else "Unassigned",
            "ward_name": adm.bed.ward.name if adm.bed and adm.bed.ward else "N/A",
            "admitted_at": adm.admitted_at.isoformat(),
            "admission_type": adm.admission_type,
            "reason": adm.reason,
            "attending_doctor": adm.attending_doctor.full_name if adm.attending_doctor else "N/A",
            "allergies": allergies_list,
            "conditions": conditions_list,
            "latest_vitals": vital_summary,
            "latest_note_type": latest_note.note_type if latest_note else None,
            "latest_note_date": latest_note.created_at.isoformat() if latest_note else None
        })

    today_start = datetime.combine(date.today(), time.min)
    today_scope = db.query(Encounter).filter(Encounter.started_at >= today_start)
    if current_user.role == "DOCTOR":
        today_scope = today_scope.filter(Encounter.attending_doctor_id == current_user.id)
    elif branch_id:
        today_scope = today_scope.filter(Encounter.branch_id == branch_id)

    return {
        "doctor_name": current_user.full_name,
        "specialization": current_user.specialization or "General Practice",
        "active_patient_count": len(patient_rows),
        "patients": patient_rows,
        "stats": {
            "active_admissions": len(patient_rows),
            "today_encounters": today_scope.count(),
            "patients_with_recent_vitals": sum(1 for patient in patient_rows if patient["latest_vitals"]),
        }
    }

@router.get("/nursing")
def get_nursing_station(
    branch_id: Optional[str] = None,
    ward_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clinical.view"))
) -> Any:
    # Query beds in ward or branch
    query = db.query(Bed).options(
        joinedload(Bed.ward),
        joinedload(Bed.room),
        joinedload(Bed.admissions).joinedload(Admission.patient),
        joinedload(Bed.admissions).joinedload(Admission.attending_doctor)
    )

    if ward_id:
        query = query.filter(Bed.ward_id == ward_id)
    elif branch_id:
        query = query.filter(Bed.branch_id == branch_id)
    elif current_user.branch_id:
        query = query.filter(Bed.branch_id == current_user.branch_id)

    beds = query.order_by(Bed.bed_number).all()

    bed_data = []
    stale_vital_cutoff = datetime.now() - timedelta(hours=4)
    pending_vitals_count = 0
    critical_alert_count = 0
    for b in beds:
        active_adm = next((a for a in b.admissions if a.status == "ACTIVE"), None)
        p = active_adm.patient if active_adm else None

        latest_vital = None
        if p:
            latest_vital_obj = db.query(PatientVital).filter(
                PatientVital.patient_id == p.id
            ).order_by(desc(PatientVital.timestamp)).first()
            if latest_vital_obj:
                latest_vital = {
                    "heart_rate": latest_vital_obj.heart_rate,
                    "bp": f"{latest_vital_obj.bp_systolic}/{latest_vital_obj.bp_diastolic}" if latest_vital_obj.bp_systolic else None,
                    "spo2": latest_vital_obj.spo2,
                    "temperature": latest_vital_obj.temperature,
                    "recorded_at": latest_vital_obj.timestamp.isoformat()
                }
                if latest_vital_obj.timestamp < stale_vital_cutoff:
                    pending_vitals_count += 1
                if (
                    (latest_vital_obj.spo2 is not None and latest_vital_obj.spo2 < 92)
                    or (latest_vital_obj.bp_systolic is not None and latest_vital_obj.bp_systolic >= 180)
                ):
                    critical_alert_count += 1
            else:
                pending_vitals_count += 1

        bed_data.append({
            "bed_id": b.id,
            "bed_number": b.bed_number,
            "bed_type": b.bed_type,
            "status": b.status,
            "is_isolation": b.is_isolation,
            "ward_name": b.ward.name if b.ward else "N/A",
            "room_number": b.room.room_number if b.room else "N/A",
            "admission_id": active_adm.id if active_adm else None,
            "patient_id": p.id if p else None,
            "patient_code": p.patient_id if p else None,
            "patient_name": f"{p.first_name} {p.last_name}" if p else None,
            "doctor_name": active_adm.attending_doctor.full_name if active_adm and active_adm.attending_doctor else None,
            "latest_vitals": latest_vital
        })

    shift_tasks = []
    for bed in bed_data:
        if bed["patient_id"] and (
            not bed["latest_vitals"]
            or datetime.fromisoformat(bed["latest_vitals"]["recorded_at"]) < stale_vital_cutoff
        ):
            shift_tasks.append({
                "type": "VITALS_DUE",
                "bed_number": bed["bed_number"],
                "patient_name": bed["patient_name"],
                "description": f"Record vitals for {bed['patient_name']} in {bed['bed_number']}.",
            })
        elif bed["status"] == "CLEANING":
            shift_tasks.append({
                "type": "BED_TURNOVER",
                "bed_number": bed["bed_number"],
                "patient_name": None,
                "description": f"Complete cleaning turnover for {bed['bed_number']}.",
            })

    return {
        "user_name": current_user.full_name,
        "total_station_beds": len(bed_data),
        "occupied_count": len([b for b in bed_data if b["status"] == "OCCUPIED"]),
        "cleaning_count": len([b for b in bed_data if b["status"] == "CLEANING"]),
        "pending_vitals_count": pending_vitals_count,
        "critical_alert_count": critical_alert_count,
        "shift_tasks": shift_tasks[:12],
        "beds": bed_data,
    }


@router.get("/reception")
def get_reception_overview(
    branch_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admission.view")),
) -> Any:
    """Database-backed registration and admission queue for reception."""
    selected_branch_id = branch_id or current_user.branch_id
    today_start = datetime.combine(date.today(), time.min)
    tomorrow_start = today_start + timedelta(days=1)

    patient_query = db.query(Patient)
    admission_query = db.query(Admission).options(
        joinedload(Admission.patient), joinedload(Admission.bed).joinedload(Bed.ward)
    )
    bed_query = db.query(Bed)
    if selected_branch_id:
        patient_query = patient_query.filter(Patient.registered_branch_id == selected_branch_id)
        admission_query = admission_query.filter(Admission.branch_id == selected_branch_id)
        bed_query = bed_query.filter(Bed.branch_id == selected_branch_id)

    today_admissions = admission_query.filter(
        Admission.admitted_at >= today_start, Admission.admitted_at < tomorrow_start
    ).order_by(desc(Admission.admitted_at)).limit(20).all()

    return {
        "today_registrations": patient_query.filter(
            Patient.created_at >= today_start, Patient.created_at < tomorrow_start
        ).count(),
        "today_admissions_count": len(today_admissions),
        "active_admissions_count": admission_query.filter(Admission.status == "ACTIVE").count(),
        "available_beds_count": bed_query.filter(Bed.status == "AVAILABLE").count(),
        "today_admissions": [{
            "id": admission.id,
            "admission_number": admission.admission_number,
            "patient_name": f"{admission.patient.first_name} {admission.patient.last_name}" if admission.patient else "Unknown",
            "patient_code": admission.patient.patient_id if admission.patient else "N/A",
            "reason": admission.reason,
            "bed_number": admission.bed.bed_number if admission.bed else "Unassigned",
            "ward_name": admission.bed.ward.name if admission.bed and admission.bed.ward else "N/A",
            "status": admission.status,
            "admitted_at": admission.admitted_at,
        } for admission in today_admissions],
    }
