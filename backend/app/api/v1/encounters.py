from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.core.database import get_db
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.identity import User
from app.models.clinical import PatientEvent
from app.schemas.encounter import EncounterCreate, EncounterOut, EncounterUpdate
from app.api.deps import assert_patient_scope, get_current_user, require_permission
from app.services.audit_service import log_audit

router = APIRouter(prefix="/encounters", tags=["Encounters"])

@router.get("", response_model=List[EncounterOut])
def get_encounters(
    patient_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("encounter.view"))
):
    query = db.query(Encounter).options(
        joinedload(Encounter.attending_doctor),
        joinedload(Encounter.branch),
        joinedload(Encounter.department)
    )
    if current_user.role == "PATIENT":
        from app.models.phase6 import PatientPortalLink
        link = db.query(PatientPortalLink).filter(PatientPortalLink.user_id == current_user.id).first()
        if not link:
            return []
        if patient_id:
            assert_patient_scope(db, current_user, patient_id)
        query = query.filter(Encounter.patient_id == link.patient_id)
    if patient_id:
        query = query.filter(Encounter.patient_id == patient_id)
    if branch_id:
        query = query.filter(Encounter.branch_id == branch_id)
    if status:
        query = query.filter(Encounter.status == status)
    
    encounters = query.order_by(desc(Encounter.started_at)).all()
    return [
        EncounterOut(
            id=e.id,
            patient_id=e.patient_id,
            branch_id=e.branch_id,
            department_id=e.department_id,
            encounter_type=e.encounter_type,
            status=e.status,
            started_at=e.started_at,
            ended_at=e.ended_at,
            attending_doctor_id=e.attending_doctor_id,
            attending_doctor_name=e.attending_doctor.full_name if e.attending_doctor else None,
            branch_name=e.branch.name if e.branch else None,
            department_name=e.department.name if e.department else None,
            reason=e.reason,
            created_at=e.created_at
        ) for e in encounters
    ]

@router.post("", response_model=EncounterOut)
def create_encounter(
    encounter_in: EncounterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("encounter.create"))
):
    patient = db.query(Patient).filter(Patient.id == encounter_in.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    assert_patient_scope(db, current_user, patient.id)

    encounter = Encounter(
        patient_id=encounter_in.patient_id,
        branch_id=encounter_in.branch_id,
        department_id=encounter_in.department_id,
        encounter_type=encounter_in.encounter_type,
        attending_doctor_id=encounter_in.attending_doctor_id,
        reason=encounter_in.reason,
        status="ACTIVE"
    )
    db.add(encounter)
    db.flush()
    db.add(PatientEvent(
        patient_id=patient.id, encounter_id=encounter.id, actor_id=current_user.id,
        event_type="ENCOUNTER_CREATED", title="Encounter Started",
        description=f"{encounter.encounter_type} encounter created. {encounter.reason or ''}".strip(),
        source_module="ENCOUNTERS"
    ))
    log_audit(db, action="ENCOUNTER_CREATE", entity_type="ENCOUNTER", entity_id=encounter.id,
              actor_id=current_user.id, actor_email=current_user.email,
              branch_id=encounter.branch_id, new_state={"type": encounter.encounter_type, "status": encounter.status})
    db.commit()
    db.refresh(encounter)
    return EncounterOut(
        id=encounter.id,
        patient_id=encounter.patient_id,
        branch_id=encounter.branch_id,
        department_id=encounter.department_id,
        encounter_type=encounter.encounter_type,
        status=encounter.status,
        started_at=encounter.started_at,
        ended_at=encounter.ended_at,
        attending_doctor_id=encounter.attending_doctor_id,
        reason=encounter.reason,
        created_at=encounter.created_at
    )

@router.patch("/{encounter_id}", response_model=EncounterOut)
def update_encounter(encounter_id: str, encounter_in: EncounterUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("encounter.create"))):
    encounter = db.query(Encounter).options(joinedload(Encounter.attending_doctor), joinedload(Encounter.branch), joinedload(Encounter.department)).filter(Encounter.id == encounter_id).first()
    if not encounter: raise HTTPException(404, "Encounter not found.")
    assert_patient_scope(db, current_user, encounter.patient_id)
    changes = encounter_in.model_dump(exclude_unset=True)
    if not changes: raise HTTPException(422, "Provide at least one encounter field to update.")
    for key, value in changes.items(): setattr(encounter, key, value)
    db.add(PatientEvent(patient_id=encounter.patient_id, encounter_id=encounter.id, actor_id=current_user.id, event_type="ENCOUNTER_UPDATED", title="Encounter updated", description=encounter.status, source_module="ENCOUNTERS"))
    log_audit(db, action="ENCOUNTER_UPDATE", entity_type="ENCOUNTER", entity_id=encounter.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=encounter.branch_id, new_state=changes)
    db.commit(); db.refresh(encounter)
    return EncounterOut(id=encounter.id, patient_id=encounter.patient_id, branch_id=encounter.branch_id, department_id=encounter.department_id, encounter_type=encounter.encounter_type, status=encounter.status, started_at=encounter.started_at, ended_at=encounter.ended_at, attending_doctor_id=encounter.attending_doctor_id, attending_doctor_name=encounter.attending_doctor.full_name if encounter.attending_doctor else None, branch_name=encounter.branch.name if encounter.branch else None, department_name=encounter.department.name if encounter.department else None, reason=encounter.reason, created_at=encounter.created_at)
