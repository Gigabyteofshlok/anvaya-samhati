from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import assert_patient_scope, require_permission
from app.core.database import get_db
from app.models.admission import Admission
from app.models.bed import Bed, BedStatus
from app.models.clinical import PatientEvent
from app.models.identity import User
from app.models.phase5 import Invoice
from app.models.phase6 import Discharge, InsuranceClaim
from app.schemas.phase6 import DischargeComplete, DischargeCreate
from app.services.audit_service import log_audit
from app.services.bed_state_machine import BedStateMachine

router = APIRouter(prefix="/discharges", tags=["Structured discharge"])


def discharge_out(row: Discharge) -> dict:
    return {
        "id": row.id, "admission_id": row.admission_id, "patient_id": row.patient_id,
        "patient_name": f"{row.patient.first_name} {row.patient.last_name}", "status": row.status,
        "diagnosis_summary": row.diagnosis_summary, "clinical_summary": row.clinical_summary,
        "clinical_cleared": row.clinical_cleared, "pending_results_checked": row.pending_results_checked,
        "billing_cleared": row.billing_cleared, "insurance_cleared": row.insurance_cleared,
        "initiated_at": row.initiated_at, "completed_at": row.completed_at,
        "medications": [{"medicine_name": m.medicine_name, "dosage": m.dosage, "frequency": m.frequency, "duration_days": m.duration_days, "instructions": m.instructions} for m in row.medications],
        "instructions": [{"instruction_type": i.instruction_type, "content": i.content} for i in row.instructions],
    }


def _query(db: Session):
    return db.query(Discharge).options(joinedload(Discharge.patient), joinedload(Discharge.medications), joinedload(Discharge.instructions))


@router.get("")
def list_discharges(patient_id: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(require_permission("discharge.view"))):
    query = _query(db)
    if patient_id:
        assert_patient_scope(db, current_user, patient_id)
        query = query.filter(Discharge.patient_id == patient_id)
    elif current_user.role == "PATIENT":
        from app.models.phase6 import PatientPortalLink
        link = db.query(PatientPortalLink).filter(PatientPortalLink.user_id == current_user.id).first()
        if not link:
            return []
        query = query.filter(Discharge.patient_id == link.patient_id)
    return [discharge_out(row) for row in query.order_by(Discharge.initiated_at.desc()).all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def initiate_discharge(data: DischargeCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("discharge.manage"))):
    admission = db.query(Admission).filter(Admission.id == data.admission_id).with_for_update().first()
    if not admission or admission.status != "ACTIVE":
        raise HTTPException(409, "An active admission is required to start discharge.")
    if db.query(Discharge).filter(Discharge.admission_id == admission.id).first():
        raise HTTPException(409, "A discharge workflow already exists for this admission.")
    row = Discharge(admission_id=admission.id, patient_id=admission.patient_id, attending_doctor_id=admission.attending_doctor_id,
                    discharge_reason=data.discharge_reason, diagnosis_summary=data.diagnosis_summary, clinical_summary=data.clinical_summary,
                    initiated_by_id=current_user.id)
    db.add(row); db.flush()
    from app.models.phase6 import DischargeMedication, DischargeInstruction
    for medication in data.medications:
        db.add(DischargeMedication(discharge_id=row.id, **medication.model_dump()))
    for instruction in data.instructions:
        db.add(DischargeInstruction(discharge_id=row.id, **instruction.model_dump()))
    db.add(PatientEvent(patient_id=row.patient_id, encounter_id=admission.encounter_id, actor_id=current_user.id, event_type="DISCHARGE_INITIATED", title="Structured discharge initiated", description=admission.admission_number, source_module="DISCHARGE"))
    log_audit(db, action="DISCHARGE_INITIATED", entity_type="DISCHARGE", entity_id=row.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=admission.branch_id)
    db.commit()
    return discharge_out(_query(db).filter(Discharge.id == row.id).one())


@router.get("/{discharge_id}")
def get_discharge(discharge_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_permission("discharge.view"))):
    row = _query(db).filter(Discharge.id == discharge_id).first()
    if not row:
        raise HTTPException(404, "Discharge workflow not found.")
    assert_patient_scope(db, current_user, row.patient_id)
    return discharge_out(row)


@router.post("/{discharge_id}/clearance")
def clear_discharge(discharge_id: str, data: DischargeComplete, db: Session = Depends(get_db), current_user: User = Depends(require_permission("discharge.manage"))):
    row = db.query(Discharge).filter(Discharge.id == discharge_id).with_for_update().first()
    if not row or row.status == "DISCHARGED":
        raise HTTPException(409, "An open discharge workflow is required.")
    # Clearance attestations are persisted and cannot be used to conceal known open balances/claims.
    open_balance = db.query(Invoice).filter(Invoice.patient_id == row.patient_id, Invoice.total_amount > Invoice.paid_amount).first()
    unresolved_claim = db.query(InsuranceClaim).filter(InsuranceClaim.patient_id == row.patient_id, InsuranceClaim.status.in_(["SUBMITTED", "UNDER_REVIEW", "PREAUTHORIZED"])).first()
    if data.billing_cleared and open_balance:
        raise HTTPException(409, "Billing clearance cannot be recorded while an invoice remains outstanding.")
    if data.insurance_cleared and unresolved_claim:
        raise HTTPException(409, "Insurance clearance cannot be recorded while a claim is unresolved.")
    row.clinical_cleared = data.clinical_cleared
    row.pending_results_checked = data.pending_results_checked
    row.billing_cleared = data.billing_cleared
    row.insurance_cleared = data.insurance_cleared
    row.status = "DISCHARGE_APPROVED" if all((row.clinical_cleared, row.pending_results_checked, row.billing_cleared, row.insurance_cleared)) else "CLEARANCE_PENDING"
    log_audit(db, action="DISCHARGE_CLEARANCE_UPDATED", entity_type="DISCHARGE", entity_id=row.id, actor_id=current_user.id, actor_email=current_user.email, new_state={"status": row.status})
    db.commit()
    return discharge_out(_query(db).filter(Discharge.id == row.id).one())


@router.post("/{discharge_id}/complete")
def complete_discharge(discharge_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_permission("discharge.manage"))):
    row = db.query(Discharge).filter(Discharge.id == discharge_id).with_for_update().first()
    if not row or row.status != "DISCHARGE_APPROVED":
        raise HTTPException(409, "All controlled clearances must be approved before discharge.")
    admission = db.query(Admission).filter(Admission.id == row.admission_id).with_for_update().first()
    if not admission or admission.status != "ACTIVE":
        raise HTTPException(409, "The linked admission is not active.")
    now = datetime.now(timezone.utc)
    if admission.assigned_bed_id:
        bed = db.query(Bed).filter(Bed.id == admission.assigned_bed_id).with_for_update().first()
        if bed:
            BedStateMachine.transition_bed(db, bed, BedStatus.CLEANING.value, current_user, f"Structured discharge {admission.admission_number}; sanitation required.")
            bed.current_admission_id = None
            db.add(PatientEvent(patient_id=row.patient_id, encounter_id=admission.encounter_id, actor_id=current_user.id, event_type="BED_RELEASED", title=f"Bed released: {bed.bed_number}", description="Bed moved to cleaning after discharge.", source_module="DISCHARGE"))
    admission.status, admission.discharged_at = "DISCHARGED", now
    if admission.encounter:
        admission.encounter.status, admission.encounter.ended_at = "COMPLETED", now
    row.status, row.approved_by_id, row.completed_at = "DISCHARGED", current_user.id, now
    db.add(PatientEvent(patient_id=row.patient_id, encounter_id=admission.encounter_id, actor_id=current_user.id, event_type="PATIENT_DISCHARGED", title="Patient discharged", description=admission.admission_number, source_module="DISCHARGE"))
    log_audit(db, action="DISCHARGE_COMPLETED", entity_type="DISCHARGE", entity_id=row.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=admission.branch_id, new_state={"status": "DISCHARGED"})
    db.commit()
    return discharge_out(_query(db).filter(Discharge.id == row.id).one())
