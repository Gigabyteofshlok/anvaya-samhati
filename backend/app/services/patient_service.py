from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import Integer, cast, func, select
from fastapi import HTTPException, status
from app.models.patient import Patient, PatientContact, PatientAllergy, PatientCondition, PatientMedication
from app.models.clinical import PatientEvent
from app.models.identity import User
from app.schemas.patient import PatientCreate
from app.services.audit_service import log_audit

def generate_patient_id(db: Session) -> str:
    # IDs must advance from the greatest numeric suffix, not most recent creation
    # timestamp. Backfilled synthetic records can otherwise collide with an
    # existing ANV identifier.
    query = (
        select(Patient.patient_id)
        .filter(Patient.patient_id.like("ANV-%"))
        .order_by(cast(func.substr(Patient.patient_id, 5), Integer).desc())
        .limit(1)
    )
    last_id = db.execute(query).scalar_one_or_none()

    if not last_id or not last_id.startswith("ANV-"):
        # Query total count for safe start
        count = db.query(func.count(Patient.id)).scalar() or 0
        return f"ANV-{(count + 1):06d}"

    try:
        current_num = int(last_id.split("-")[1])
        next_num = current_num + 1
        return f"ANV-{next_num:06d}"
    except (ValueError, IndexError):
        count = db.query(func.count(Patient.id)).scalar() or 0
        return f"ANV-{(count + 1):06d}"

def register_patient(db: Session, patient_in: PatientCreate, user: User) -> Patient:
    # Check if active patient with same phone exists
    existing = db.query(Patient).filter(Patient.mobile == patient_in.mobile).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient with mobile number {patient_in.mobile} already exists ({existing.patient_id}: {existing.first_name} {existing.last_name})."
        )

    patient_id = generate_patient_id(db)

    patient = Patient(
        patient_id=patient_id,
        first_name=patient_in.first_name.strip(),
        middle_name=patient_in.middle_name.strip() if patient_in.middle_name else None,
        last_name=patient_in.last_name.strip(),
        date_of_birth=patient_in.date_of_birth,
        gender=patient_in.gender,
        blood_group=patient_in.blood_group,
        mobile=patient_in.mobile.strip(),
        email=patient_in.email.strip() if patient_in.email else None,
        address=patient_in.address,
        city=patient_in.city,
        state=patient_in.state,
        postal_code=patient_in.postal_code,
        consent_status=patient_in.consent_status,
        registered_branch_id=patient_in.registered_branch_id
    )
    db.add(patient)
    db.flush()

    # Add emergency contact if provided
    if patient_in.emergency_contact:
        contact = PatientContact(
            patient_id=patient.id,
            name=patient_in.emergency_contact.name,
            relationship_type=patient_in.emergency_contact.relationship_type,
            phone=patient_in.emergency_contact.phone,
            is_primary=patient_in.emergency_contact.is_primary
        )
        db.add(contact)

    # Add allergies
    for allergy in patient_in.allergies:
        db.add(PatientAllergy(
            patient_id=patient.id,
            allergen=allergy.allergen,
            reaction=allergy.reaction,
            severity=allergy.severity,
            status=allergy.status,
            recorded_by=user.id
        ))

    # Add conditions
    for cond in patient_in.conditions:
        db.add(PatientCondition(
            patient_id=patient.id,
            condition_name=cond.condition_name,
            icd_code=cond.icd_code,
            status=cond.status,
            onset_date=cond.onset_date,
            notes=cond.notes,
            recorded_by=user.id
        ))

    # Add medications
    for med in patient_in.medications:
        db.add(PatientMedication(
            patient_id=patient.id,
            medication_name=med.medication_name,
            dose=med.dose,
            route=med.route,
            frequency=med.frequency,
            status=med.status,
            start_date=med.start_date,
            end_date=med.end_date,
            recorded_by=user.id
        ))

    # Log Patient Timeline Event
    event = PatientEvent(
        patient_id=patient.id,
        actor_id=user.id,
        event_type="PATIENT_REGISTERED",
        title="Patient Registered",
        description=f"Registered at hospital with ID {patient.patient_id}",
        source_module="REGISTRATION",
        metadata_json={"patient_id": patient.patient_id, "branch_id": patient.registered_branch_id}
    )
    db.add(event)

    # Log Audit
    log_audit(
        db=db,
        action="PATIENT_CREATE",
        entity_type="PATIENT",
        entity_id=patient.id,
        actor_id=user.id,
        actor_email=user.email,
        branch_id=patient.registered_branch_id,
        new_state={"patient_id": patient.patient_id, "name": f"{patient.first_name} {patient.last_name}"},
        notes=f"Created patient {patient.patient_id}"
    )

    db.commit()
    db.refresh(patient)
    return patient
