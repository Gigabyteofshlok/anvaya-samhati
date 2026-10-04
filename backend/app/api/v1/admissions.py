from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_
from app.core.database import get_db
from app.models.admission import Admission
from app.models.bed import Bed
from app.models.patient import Patient
from app.models.identity import User
from app.schemas.admission import AdmissionCreate, AdmissionOut, AdmissionDischarge
from app.api.deps import assert_patient_scope, get_current_user, require_permission
from app.services.admission_service import create_admission_transactional, discharge_admission_transactional

router = APIRouter(prefix="/admissions", tags=["Admissions"])

def build_admission_out(adm: Admission) -> AdmissionOut:
    return AdmissionOut(
        id=adm.id,
        admission_number=adm.admission_number,
        encounter_id=adm.encounter_id,
        patient_id=adm.patient_id,
        branch_id=adm.branch_id,
        department_id=adm.department_id,
        attending_doctor_id=adm.attending_doctor_id,
        assigned_bed_id=adm.assigned_bed_id,
        admission_type=adm.admission_type,
        status=adm.status,
        reason=adm.reason,
        diagnosis_notes=adm.diagnosis_notes,
        admitted_at=adm.admitted_at,
        discharged_at=adm.discharged_at,
        admitted_by=adm.admitted_by,
        created_at=adm.created_at,
        patient_name=f"{adm.patient.first_name} {adm.patient.last_name}" if adm.patient else None,
        patient_code=adm.patient.patient_id if adm.patient else None,
        doctor_name=adm.attending_doctor.full_name if adm.attending_doctor else None,
        bed_number=adm.bed.bed_number if adm.bed else None,
        ward_name=adm.bed.ward.name if adm.bed and adm.bed.ward else None,
        branch_name=adm.branch.name if adm.branch else None
    )

@router.get("", response_model=List[AdmissionOut])
def get_admissions(
    branch_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    doctor_id: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admission.view"))
):
    query = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.attending_doctor),
        joinedload(Admission.branch),
        joinedload(Admission.bed).joinedload(Bed.ward)
    )

    if current_user.role == "PATIENT":
        from app.models.phase6 import PatientPortalLink
        link = db.query(PatientPortalLink).filter(PatientPortalLink.user_id == current_user.id).first()
        if not link:
            return []
        query = query.filter(Admission.patient_id == link.patient_id)

    if branch_id:
        query = query.filter(Admission.branch_id == branch_id)
    if status_filter:
        query = query.filter(Admission.status == status_filter)
    if doctor_id:
        query = query.filter(Admission.attending_doctor_id == doctor_id)
    if q:
        search = f"%{q.strip()}%"
        query = query.join(Patient).filter(
            or_(
                Admission.admission_number.ilike(search),
                Patient.patient_id.ilike(search),
                Patient.first_name.ilike(search),
                Patient.last_name.ilike(search)
            )
        )

    admissions = query.order_by(desc(Admission.admitted_at)).offset(offset).limit(limit).all()
    return [build_admission_out(a) for a in admissions]

@router.post("", response_model=AdmissionOut)
def create_admission(
    admission_in: AdmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admission.create"))
):
    admission = create_admission_transactional(db, admission_in, current_user)
    # Reload with relationships
    admission = db.query(Admission).filter(Admission.id == admission.id).options(
        joinedload(Admission.patient),
        joinedload(Admission.attending_doctor),
        joinedload(Admission.branch),
        joinedload(Admission.bed).joinedload(Bed.ward)
    ).first()
    return build_admission_out(admission)

@router.get("/{admission_id}", response_model=AdmissionOut)
def get_admission(
    admission_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admission.view"))
):
    adm = db.query(Admission).filter(Admission.id == admission_id).options(
        joinedload(Admission.patient),
        joinedload(Admission.attending_doctor),
        joinedload(Admission.branch),
        joinedload(Admission.bed).joinedload(Bed.ward)
    ).first()
    if not adm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found.")
    assert_patient_scope(db, current_user, adm.patient_id)
    return build_admission_out(adm)

@router.post("/{admission_id}/discharge", response_model=AdmissionOut)
def discharge_admission(
    admission_id: str,
    discharge_in: AdmissionDischarge,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admission.discharge"))
):
    adm = discharge_admission_transactional(db, admission_id, discharge_in, current_user)
    adm = db.query(Admission).filter(Admission.id == adm.id).options(
        joinedload(Admission.patient),
        joinedload(Admission.attending_doctor),
        joinedload(Admission.branch),
        joinedload(Admission.bed).joinedload(Bed.ward)
    ).first()
    return build_admission_out(adm)
