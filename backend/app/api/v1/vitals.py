from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc
from app.core.database import get_db
from app.models.clinical import PatientVital, PatientEvent
from app.models.patient import Patient
from app.models.admission import Admission
from app.models.identity import User
from app.schemas.clinical import VitalCreate, VitalOut
from app.api.deps import assert_patient_scope, get_current_user, require_permission
from app.services.audit_service import log_audit

router = APIRouter(prefix="/patients", tags=["Vitals"])

def build_vital_out(v: PatientVital) -> VitalOut:
    return VitalOut(
        id=v.id,
        patient_id=v.patient_id,
        encounter_id=v.encounter_id,
        admission_id=v.admission_id,
        recorded_by=v.recorded_by,
        recorded_by_name=v.recorder.full_name if v.recorder else "Care Staff",
        timestamp=v.timestamp,
        heart_rate=v.heart_rate,
        bp_systolic=v.bp_systolic,
        bp_diastolic=v.bp_diastolic,
        respiratory_rate=v.respiratory_rate,
        spo2=v.spo2,
        temperature=v.temperature,
        weight_kg=v.weight_kg,
        notes=v.notes
    )

@router.get("/{patient_id}/vitals", response_model=List[VitalOut])
def get_patient_vitals(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("vitals.view"))
):
    assert_patient_scope(db, current_user, patient_id)
    vitals = db.query(PatientVital).filter(
        PatientVital.patient_id == patient_id
    ).options(joinedload(PatientVital.recorder)).order_by(asc(PatientVital.timestamp)).all()

    return [build_vital_out(v) for v in vitals]

@router.post("/{patient_id}/vitals", response_model=VitalOut)
def record_patient_vitals(
    patient_id: str,
    vital_in: VitalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("vitals.write"))
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    assert_patient_scope(db, current_user, patient.id)

    # Find active admission / encounter if not explicitly supplied
    enc_id = vital_in.encounter_id
    adm_id = vital_in.admission_id

    if not adm_id:
        active_adm = db.query(Admission).filter(
            Admission.patient_id == patient.id,
            Admission.status == "ACTIVE"
        ).first()
        if active_adm:
            adm_id = active_adm.id
            enc_id = active_adm.encounter_id

    vital = PatientVital(
        patient_id=patient.id,
        encounter_id=enc_id,
        admission_id=adm_id,
        recorded_by=current_user.id,
        heart_rate=vital_in.heart_rate,
        bp_systolic=vital_in.bp_systolic,
        bp_diastolic=vital_in.bp_diastolic,
        respiratory_rate=vital_in.respiratory_rate,
        spo2=vital_in.spo2,
        temperature=vital_in.temperature,
        weight_kg=vital_in.weight_kg,
        notes=vital_in.notes
    )
    db.add(vital)
    db.flush()

    # Timeline event
    bp_str = f"{vital.bp_systolic}/{vital.bp_diastolic}" if (vital.bp_systolic and vital.bp_diastolic) else "N/A"
    summary_desc = f"HR: {vital.heart_rate or 'N/A'} bpm | BP: {bp_str} | SpO₂: {vital.spo2 or 'N/A'}% | Temp: {vital.temperature or 'N/A'}°F"
    db.add(PatientEvent(
        patient_id=patient.id,
        encounter_id=enc_id,
        actor_id=current_user.id,
        event_type="VITAL_RECORDED",
        title="Vital Signs Recorded",
        description=summary_desc,
        source_module="NURSING",
        metadata_json={
            "heart_rate": vital.heart_rate,
            "bp_systolic": vital.bp_systolic,
            "bp_diastolic": vital.bp_diastolic,
            "spo2": vital.spo2,
            "temperature": vital.temperature
        }
    ))

    # Audit log
    log_audit(
        db=db,
        action="VITAL_RECORD",
        entity_type="VITAL",
        entity_id=vital.id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        branch_id=patient.registered_branch_id,
        notes=f"Recorded vitals for {patient.patient_id}: {summary_desc}"
    )

    db.commit()
    db.refresh(vital)
    return build_vital_out(vital)

@router.patch("/{patient_id}/vitals/{vital_id}", response_model=VitalOut)
def correct_patient_vitals(patient_id: str, vital_id: str, vital_in: VitalCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("vitals.write"))):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient: raise HTTPException(404, "Patient not found.")
    assert_patient_scope(db, current_user, patient.id)
    vital = db.query(PatientVital).filter(PatientVital.id == vital_id, PatientVital.patient_id == patient.id).first()
    if not vital: raise HTTPException(404, "Vital record not found.")
    editable = vital_in.model_dump(exclude_unset=True, exclude={"patient_id", "encounter_id", "admission_id"})
    if not editable: raise HTTPException(422, "Provide at least one vital value to correct.")
    for key, value in editable.items(): setattr(vital, key, value)
    db.add(PatientEvent(patient_id=patient.id, encounter_id=vital.encounter_id, actor_id=current_user.id, event_type="VITAL_CORRECTED", title="Vital signs corrected", description="A recorded vital-sign entry was amended.", source_module="NURSING"))
    log_audit(db, action="VITAL_CORRECT", entity_type="VITAL", entity_id=vital.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=patient.registered_branch_id, new_state=editable)
    db.commit(); db.refresh(vital); return build_vital_out(vital)
