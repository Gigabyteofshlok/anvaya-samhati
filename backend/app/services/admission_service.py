from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.models.admission import Admission
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.bed import Bed, BedStatus
from app.models.identity import User
from app.models.clinical import PatientEvent
from app.schemas.admission import AdmissionCreate, AdmissionDischarge
from app.services.audit_service import log_audit
from app.services.bed_state_machine import BedStateMachine

def generate_admission_number(db: Session) -> str:
    query = select(Admission.admission_number).order_by(Admission.created_at.desc()).limit(1)
    last_num = db.execute(query).scalar_one_or_none()
    if not last_num or not last_num.startswith("ADM-"):
        count = db.query(func.count(Admission.id)).scalar() or 0
        return f"ADM-{(count + 1):06d}"
    try:
        current_num = int(last_num.split("-")[1])
        return f"ADM-{(current_num + 1):06d}"
    except (ValueError, IndexError):
        count = db.query(func.count(Admission.id)).scalar() or 0
        return f"ADM-{(count + 1):06d}"

def create_admission_transactional(db: Session, admission_in: AdmissionCreate, user: User) -> Admission:
    # 1. Verify patient exists
    patient = db.query(Patient).filter(Patient.id == admission_in.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")

    # 2. Verify patient doesn't already have an active admission
    existing_active = db.query(Admission).filter(
        Admission.patient_id == patient.id,
        Admission.status == "ACTIVE"
    ).first()
    if existing_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient already has an active admission ({existing_active.admission_number}). Discharge patient before new admission."
        )

    # 3. Check and lock bed if assigned
    bed = None
    if admission_in.assigned_bed_id:
        bed = db.query(Bed).filter(Bed.id == admission_in.assigned_bed_id).with_for_update().first()
        if not bed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned bed not found.")
        
        # Check bed belongs to correct branch
        if bed.branch_id != admission_in.branch_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bed does not belong to the selected branch.")

        # Bed must be AVAILABLE or RESERVED
        if bed.status not in [BedStatus.AVAILABLE.value, BedStatus.RESERVED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bed {bed.bed_number} is currently {bed.status} and cannot be assigned."
            )

    # 4. Create Encounter
    encounter = Encounter(
        patient_id=patient.id,
        branch_id=admission_in.branch_id,
        department_id=admission_in.department_id,
        encounter_type="IPD" if admission_in.admission_type != "EMERGENCY" else "EMERGENCY",
        status="ACTIVE",
        attending_doctor_id=admission_in.attending_doctor_id,
        reason=admission_in.reason
    )
    db.add(encounter)
    db.flush()

    # 5. Create Admission
    adm_num = generate_admission_number(db)
    admission = Admission(
        admission_number=adm_num,
        encounter_id=encounter.id,
        patient_id=patient.id,
        branch_id=admission_in.branch_id,
        department_id=admission_in.department_id,
        attending_doctor_id=admission_in.attending_doctor_id,
        assigned_bed_id=bed.id if bed else None,
        admission_type=admission_in.admission_type,
        status="ACTIVE",
        reason=admission_in.reason,
        diagnosis_notes=admission_in.diagnosis_notes,
        admitted_by=user.id
    )
    db.add(admission)
    db.flush()

    # 6. Update Bed status to OCCUPIED and link admission
    if bed:
        BedStateMachine.transition_bed(
            db=db,
            bed=bed,
            target_status=BedStatus.OCCUPIED.value,
            user=user,
            notes=f"Assigned to admission {admission.admission_number}"
        )
        bed.current_admission_id = admission.id

    # 7. Record Timeline Events
    db.add(PatientEvent(
        patient_id=patient.id,
        encounter_id=encounter.id,
        actor_id=user.id,
        event_type="ENCOUNTER_CREATED",
        title="Encounter Started",
        description=f"Encounter started: {encounter.encounter_type}",
        source_module="CLINICAL"
    ))

    db.add(PatientEvent(
        patient_id=patient.id,
        encounter_id=encounter.id,
        actor_id=user.id,
        event_type="PATIENT_ADMITTED",
        title="Patient Admitted",
        description=f"Admitted via {admission.admission_type} ({admission.admission_number}). Reason: {admission.reason}",
        source_module="ADMISSIONS"
    ))

    if bed:
        db.add(PatientEvent(
            patient_id=patient.id,
            encounter_id=encounter.id,
            actor_id=user.id,
            event_type="BED_ASSIGNED",
            title=f"Bed Assigned: {bed.bed_number}",
            description=f"Assigned to Bed {bed.bed_number} in Ward.",
            source_module="BED_MANAGEMENT",
            metadata_json={"bed_id": bed.id, "bed_number": bed.bed_number}
        ))

    # 8. Audit Log
    log_audit(
        db=db,
        action="ADMISSION_CREATE",
        entity_type="ADMISSION",
        entity_id=admission.id,
        actor_id=user.id,
        actor_email=user.email,
        branch_id=admission.branch_id,
        new_state={
            "admission_number": admission.admission_number,
            "patient_id": patient.patient_id,
            "bed_id": bed.id if bed else None
        },
        notes=f"Admitted patient {patient.patient_id} with admission {admission.admission_number}"
    )

    db.commit()
    db.refresh(admission)
    return admission

def discharge_admission_transactional(
    db: Session,
    admission_id: str,
    discharge_in: AdmissionDischarge,
    user: User
) -> Admission:
    admission = db.query(Admission).filter(Admission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found.")

    if admission.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only ACTIVE admissions can be discharged.")

    now = datetime.now(timezone.utc)
    admission.status = "DISCHARGED"
    admission.discharged_at = now
    if discharge_in.discharge_notes:
        admission.diagnosis_notes = (admission.diagnosis_notes or "") + f"\nDischarge Note: {discharge_in.discharge_notes}"

    # Handle linked bed - MANDATORY TRANSITION TO CLEANING
    if admission.assigned_bed_id:
        bed = db.query(Bed).filter(Bed.id == admission.assigned_bed_id).with_for_update().first()
        if bed:
            BedStateMachine.transition_bed(
                db=db,
                bed=bed,
                target_status=BedStatus.CLEANING.value,
                user=user,
                notes=f"Discharge from admission {admission.admission_number}. Set for sanitization."
            )
            bed.current_admission_id = None

            db.add(PatientEvent(
                patient_id=admission.patient_id,
                encounter_id=admission.encounter_id,
                actor_id=user.id,
                event_type="BED_RELEASED",
                title=f"Bed Released: {bed.bed_number}",
                description=f"Bed {bed.bed_number} released and marked for CLEANING.",
                source_module="BED_MANAGEMENT"
            ))

    # Complete Encounter
    if admission.encounter:
        admission.encounter.status = "COMPLETED"
        admission.encounter.ended_at = now

    # Patient Timeline Event
    db.add(PatientEvent(
        patient_id=admission.patient_id,
        encounter_id=admission.encounter_id,
        actor_id=user.id,
        event_type="ADMISSION_DISCHARGED",
        title="Admission Discharged",
        description=f"Discharged from admission {admission.admission_number}. {discharge_in.discharge_notes or ''}".strip(),
        source_module="ADMISSIONS"
    ))

    # Audit Log
    log_audit(
        db=db,
        action="ADMISSION_DISCHARGE",
        entity_type="ADMISSION",
        entity_id=admission.id,
        actor_id=user.id,
        actor_email=user.email,
        branch_id=admission.branch_id,
        new_state={"status": "DISCHARGED", "discharged_at": now.isoformat()},
        notes=f"Discharged admission {admission.admission_number}"
    )

    db.commit()
    db.refresh(admission)
    return admission
