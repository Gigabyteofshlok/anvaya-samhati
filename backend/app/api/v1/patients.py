from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc
from app.core.database import get_db
from app.models.patient import Patient, PatientContact, PatientAllergy, PatientCondition, PatientMedication
from app.models.admission import Admission
from app.models.bed import Bed
from app.models.clinical import PatientEvent
from app.models.phase5 import Invoice, LabOrder, LabResult, Prescription, PrescriptionItem
from app.models.phase6 import Discharge, InsuranceClaim, InsurancePolicy, LabResultValue
from app.models.identity import User
from app.schemas.patient import (
    PatientCreate, PatientUpdate, PatientSummaryOut, PatientOut,
    PatientAllergyIn, PatientAllergyOut,
    PatientConditionIn, PatientConditionOut,
    PatientMedicationIn, PatientMedicationOut,
    PatientAllergyUpdate, PatientConditionUpdate, PatientMedicationUpdate,
)
from app.schemas.clinical import PatientEventOut
from app.api.deps import assert_patient_scope, get_current_user, require_permission
from app.services.patient_service import register_patient
from app.services.audit_service import log_audit

router = APIRouter(prefix="/patients", tags=["Patients"])

def calculate_age(born: date) -> int:
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def build_patient_summary(p: Patient, active_admissions_map: dict) -> PatientSummaryOut:
    active_adm = active_admissions_map.get(p.id)
    cur_status = "ADMITTED" if active_adm else "OUTPATIENT"
    bed_num = active_adm.bed.bed_number if active_adm and active_adm.bed else None
    ward_name = active_adm.bed.ward.name if active_adm and active_adm.bed and active_adm.bed.ward else None
    adm_id = active_adm.id if active_adm else None

    return PatientSummaryOut(
        id=p.id,
        patient_id=p.patient_id,
        first_name=p.first_name,
        last_name=p.last_name,
        full_name=f"{p.first_name} {p.last_name}",
        date_of_birth=p.date_of_birth,
        age=calculate_age(p.date_of_birth),
        gender=p.gender,
        blood_group=p.blood_group,
        mobile=p.mobile,
        registered_branch_id=p.registered_branch_id,
        registered_branch_name=p.registered_branch.name if p.registered_branch else None,
        current_status=cur_status,
        current_admission_id=adm_id,
        current_bed_number=bed_num,
        current_ward_name=ward_name,
        created_at=p.created_at
    )

@router.get("", response_model=List[PatientSummaryOut])
def get_patients(
    q: Optional[str] = Query(None, description="Search by Patient ID, Name, or Mobile"),
    branch_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, description="ALL, ADMITTED, OUTPATIENT"),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("patient.view"))
):
    query = db.query(Patient).options(joinedload(Patient.registered_branch))

    # A portal account is never permitted to enumerate the hospital directory.
    if current_user.role == "PATIENT":
        from app.models.phase6 import PatientPortalLink
        link = db.query(PatientPortalLink).filter(PatientPortalLink.user_id == current_user.id).first()
        if not link:
            return []
        query = query.filter(Patient.id == link.patient_id)

    if q:
        search = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Patient.patient_id.ilike(search),
                Patient.first_name.ilike(search),
                Patient.last_name.ilike(search),
                Patient.mobile.ilike(search)
            )
        )

    if branch_id:
        query = query.filter(Patient.registered_branch_id == branch_id)

    patients = query.order_by(desc(Patient.created_at)).offset(offset).limit(limit).all()
    patient_ids = [p.id for p in patients]

    # Pre-fetch active admissions for these patients
    active_adms = db.query(Admission).filter(
        Admission.patient_id.in_(patient_ids),
        Admission.status == "ACTIVE"
    ).options(joinedload(Admission.bed).joinedload(Bed.ward)).all()
    active_map = {adm.patient_id: adm for adm in active_adms}

    results = []
    for p in patients:
        summary = build_patient_summary(p, active_map)
        if status_filter:
            if status_filter == "ADMITTED" and summary.current_status != "ADMITTED":
                continue
            if status_filter == "OUTPATIENT" and summary.current_status != "OUTPATIENT":
                continue
        results.append(summary)

    return results

@router.post("", response_model=PatientOut)
def create_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("patient.create"))
):
    patient = register_patient(db, patient_in, current_user)
    return get_patient_360(patient.id, db, current_user)

@router.get("/{patient_id}", response_model=PatientOut)
def get_patient_360(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("patient.view"))
):
    patient = db.query(Patient).filter(
        (Patient.id == patient_id) | (Patient.patient_id == patient_id)
    ).options(
        joinedload(Patient.registered_branch),
        joinedload(Patient.contacts),
        joinedload(Patient.allergies),
        joinedload(Patient.conditions),
        joinedload(Patient.medications)
    ).first()

    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    assert_patient_scope(db, current_user, patient.id)

    # Check active admission
    active_adm = db.query(Admission).filter(
        Admission.patient_id == patient.id,
        Admission.status == "ACTIVE"
    ).options(
        joinedload(Admission.bed).joinedload(Bed.ward),
        joinedload(Admission.attending_doctor)
    ).first()

    adm_dict = None
    if active_adm:
        adm_dict = {
            "id": active_adm.id,
            "admission_number": active_adm.admission_number,
            "admitted_at": active_adm.admitted_at.isoformat(),
            "reason": active_adm.reason,
            "admission_type": active_adm.admission_type,
            "doctor_name": active_adm.attending_doctor.full_name if active_adm.attending_doctor else "N/A",
            "bed_number": active_adm.bed.bed_number if active_adm.bed else None,
            "ward_name": active_adm.bed.ward.name if active_adm.bed and active_adm.bed.ward else None,
            "branch_id": active_adm.branch_id
        }

    return PatientOut(
        id=patient.id,
        patient_id=patient.patient_id,
        first_name=patient.first_name,
        middle_name=patient.middle_name,
        last_name=patient.last_name,
        full_name=f"{patient.first_name} {patient.last_name}",
        date_of_birth=patient.date_of_birth,
        age=calculate_age(patient.date_of_birth),
        gender=patient.gender,
        blood_group=patient.blood_group,
        mobile=patient.mobile,
        email=patient.email,
        address=patient.address,
        city=patient.city,
        state=patient.state,
        postal_code=patient.postal_code,
        consent_status=patient.consent_status,
        registered_branch_id=patient.registered_branch_id,
        registered_branch_name=patient.registered_branch.name if patient.registered_branch else None,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
        contacts=patient.contacts,
        allergies=patient.allergies,
        conditions=patient.conditions,
        medications=patient.medications,
        active_admission=adm_dict
    )

@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: str,
    patient_in: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("patient.update"))
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    assert_patient_scope(db, current_user, patient.id)

    update_data = patient_in.model_dump(exclude_unset=True)
    old_state = {k: getattr(patient, k) for k in update_data.keys() if hasattr(patient, k)}

    for field, val in update_data.items():
        setattr(patient, field, val)

    # Log audit
    log_audit(
        db=db,
        action="PATIENT_UPDATE",
        entity_type="PATIENT",
        entity_id=patient.id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        branch_id=patient.registered_branch_id,
        old_state=old_state,
        new_state=update_data,
        notes=f"Updated patient details for {patient.patient_id}"
    )

    db.add(PatientEvent(
        patient_id=patient.id,
        actor_id=current_user.id,
        event_type="PATIENT_UPDATED",
        title="Patient Details Updated",
        description="Patient demographic or contact details were modified.",
        source_module="PATIENTS"
    ))

    db.commit()
    return get_patient_360(patient.id, db, current_user)

@router.get("/{patient_id}/timeline", response_model=List[PatientEventOut])
def get_patient_timeline(
    patient_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("patient.view"))
):
    patient = db.query(Patient).filter((Patient.id == patient_id) | (Patient.patient_id == patient_id)).first()
    if not patient: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    assert_patient_scope(db, current_user, patient.id)
    events = db.query(PatientEvent).filter(
        PatientEvent.patient_id == patient.id
    ).options(joinedload(PatientEvent.actor)).order_by(desc(PatientEvent.timestamp)).limit(limit).all()

    return [
        PatientEventOut(
            id=e.id,
            patient_id=e.patient_id,
            encounter_id=e.encounter_id,
            actor_id=e.actor_id,
            actor_name=e.actor.full_name if e.actor else "System",
            event_type=e.event_type,
            title=e.title,
            description=e.description,
            source_module=e.source_module,
            timestamp=e.timestamp,
            metadata_json=e.metadata_json
        ) for e in events
    ]


@router.get("/{patient_id}/care-summary")
def get_patient_care_summary(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("patient.view")),
):
    """One patient-scoped, read-only view across existing Phase 3–6 records.

    This deliberately follows the persisted patient_id (and retained encounter/admission
    references) instead of copying operational records into patient-owned JSON.
    """
    patient = db.query(Patient).filter((Patient.id == patient_id) | (Patient.patient_id == patient_id)).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    assert_patient_scope(db, current_user, patient.id)

    labs = db.query(LabOrder).options(
        joinedload(LabOrder.test), joinedload(LabOrder.result)
    ).filter(LabOrder.patient_id == patient.id).order_by(desc(LabOrder.created_at)).all()
    lab_rows = []
    for order in labs:
        values = []
        if order.result:
            values = db.query(LabResultValue).options(joinedload(LabResultValue.component)).filter(
                LabResultValue.result_id == order.result.id
            ).order_by(LabResultValue.id).all()
        lab_rows.append({
            "id": order.id, "order_number": order.order_number, "encounter_id": order.encounter_id,
            "admission_id": order.admission_id, "test_name": order.test.name if order.test else "Unknown test",
            "status": order.status, "priority": order.priority, "created_at": order.created_at,
            "result": None if not order.result else {
                "id": order.result.id, "report_status": order.result.report_status,
                "flag": order.result.flag, "comments": order.result.comments,
                "entered_at": order.result.entered_at, "verified_at": order.result.verified_at,
                "components": [{"name": value.component.name if value.component else "Component", "value": value.value_text,
                                "unit": value.unit, "reference_range": value.reference_range, "flag": value.flag}
                               for value in values],
            },
        })

    prescriptions = db.query(Prescription).options(
        joinedload(Prescription.items).joinedload(PrescriptionItem.medicine)
    ).filter(Prescription.patient_id == patient.id).order_by(desc(Prescription.created_at)).all()
    prescription_rows = [{
        "id": row.id, "prescription_number": row.prescription_number, "encounter_id": row.encounter_id,
        "admission_id": row.admission_id, "status": row.status, "created_at": row.created_at,
        "items": [{"id": item.id, "medicine_name": item.medicine.generic_name if item.medicine else "Unknown medicine",
                   "dosage": item.dosage, "frequency": item.frequency, "duration_days": item.duration_days,
                   "quantity": item.quantity, "dispensed_quantity": item.dispensed_quantity, "status": item.status}
                  for item in row.items],
    } for row in prescriptions]

    invoices = db.query(Invoice).options(joinedload(Invoice.items), joinedload(Invoice.payments)).filter(
        Invoice.patient_id == patient.id
    ).order_by(desc(Invoice.created_at)).all()
    invoice_rows = [{
        "id": row.id, "invoice_number": row.invoice_number, "encounter_id": row.encounter_id,
        "admission_id": row.admission_id, "status": row.status, "total_amount": row.total_amount,
        "paid_amount": row.paid_amount, "outstanding_balance": round(row.total_amount - row.paid_amount, 2),
        "items": [{"charge_type": item.charge_type, "description": item.description, "amount": item.amount}
                  for item in row.items],
        "payments": [{"amount": payment.amount, "method": payment.payment_method, "received_at": payment.received_at}
                     for payment in row.payments],
    } for row in invoices]

    policies = db.query(InsurancePolicy).options(joinedload(InsurancePolicy.provider)).filter(
        InsurancePolicy.patient_id == patient.id
    ).order_by(desc(InsurancePolicy.created_at)).all()
    claims = db.query(InsuranceClaim).filter(InsuranceClaim.patient_id == patient.id).order_by(desc(InsuranceClaim.created_at)).all()
    discharges = db.query(Discharge).filter(Discharge.patient_id == patient.id).order_by(desc(Discharge.initiated_at)).all()
    admissions = db.query(Admission).options(joinedload(Admission.bed)).filter(Admission.patient_id == patient.id).order_by(desc(Admission.admitted_at)).all()

    return {
        "labs": lab_rows, "prescriptions": prescription_rows, "billing": invoice_rows,
        "insurance": {
            "policies": [{"policy_number": row.policy_number, "provider": row.provider.name if row.provider else None,
                          "coverage_amount": row.coverage_amount, "status": row.status, "valid_to": row.valid_to} for row in policies],
            "claims": [{"claim_number": row.claim_number, "status": row.status, "submitted_amount": row.submitted_amount,
                        "approved_amount": row.approved_amount} for row in claims],
        },
        "admissions": [{"admission_number": row.admission_number, "status": row.status, "reason": row.reason,
                        "bed_number": row.bed.bed_number if row.bed else None, "admitted_at": row.admitted_at,
                        "discharged_at": row.discharged_at} for row in admissions],
        "discharges": [{"status": row.status, "diagnosis_summary": row.diagnosis_summary,
                        "clinical_summary": row.clinical_summary, "initiated_at": row.initiated_at,
                        "completed_at": row.completed_at} for row in discharges],
    }

@router.post("/{patient_id}/allergies", response_model=PatientAllergyOut)
def add_patient_allergy(
    patient_id: str,
    allergy_in: PatientAllergyIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clinical.write"))
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")

    allergy = PatientAllergy(
        patient_id=patient.id,
        allergen=allergy_in.allergen,
        reaction=allergy_in.reaction,
        severity=allergy_in.severity,
        status=allergy_in.status,
        recorded_by=current_user.id
    )
    db.add(allergy)
    db.add(PatientEvent(
        patient_id=patient.id,
        actor_id=current_user.id,
        event_type="CLINICAL_ALERT",
        title=f"Allergy Recorded: {allergy.allergen}",
        description=f"Severity: {allergy.severity}. Reaction: {allergy.reaction or 'N/A'}",
        source_module="CLINICAL"
    ))
    db.commit()
    db.refresh(allergy)
    return allergy

def _patient_or_404(db: Session, patient_id: str) -> Patient:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    return patient

def _clinical_event(db: Session, patient: Patient, user: User, event_type: str, title: str, description: str) -> None:
    db.add(PatientEvent(patient_id=patient.id, actor_id=user.id, event_type=event_type,
                        title=title, description=description, source_module="CLINICAL"))

@router.post("/{patient_id}/conditions", response_model=PatientConditionOut)
def add_patient_condition(patient_id: str, payload: PatientConditionIn, db: Session = Depends(get_db), current_user: User = Depends(require_permission("clinical.write"))):
    patient = _patient_or_404(db, patient_id); assert_patient_scope(db, current_user, patient.id)
    item = PatientCondition(patient_id=patient.id, recorded_by=current_user.id, **payload.model_dump())
    db.add(item); db.flush()
    _clinical_event(db, patient, current_user, "CONDITION_RECORDED", f"Condition recorded: {item.condition_name}", item.status)
    log_audit(db, action="PATIENT_CONDITION_CREATE", entity_type="PATIENT_CONDITION", entity_id=item.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=patient.registered_branch_id)
    db.commit(); db.refresh(item); return item

@router.patch("/{patient_id}/conditions/{condition_id}", response_model=PatientConditionOut)
def update_patient_condition(patient_id: str, condition_id: str, payload: PatientConditionUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("clinical.write"))):
    patient = _patient_or_404(db, patient_id); assert_patient_scope(db, current_user, patient.id)
    item = db.query(PatientCondition).filter(PatientCondition.id == condition_id, PatientCondition.patient_id == patient.id).first()
    if not item: raise HTTPException(404, "Condition not found.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes: raise HTTPException(422, "Provide at least one condition field to update.")
    for key, value in changes.items(): setattr(item, key, value)
    _clinical_event(db, patient, current_user, "CONDITION_UPDATED", f"Condition updated: {item.condition_name}", item.status)
    log_audit(db, action="PATIENT_CONDITION_UPDATE", entity_type="PATIENT_CONDITION", entity_id=item.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=patient.registered_branch_id, new_state=changes)
    db.commit(); db.refresh(item); return item

@router.post("/{patient_id}/medications", response_model=PatientMedicationOut)
def add_patient_medication(patient_id: str, payload: PatientMedicationIn, db: Session = Depends(get_db), current_user: User = Depends(require_permission("clinical.write"))):
    patient = _patient_or_404(db, patient_id); assert_patient_scope(db, current_user, patient.id)
    item = PatientMedication(patient_id=patient.id, recorded_by=current_user.id, **payload.model_dump())
    db.add(item); db.flush()
    _clinical_event(db, patient, current_user, "PATIENT_MEDICATION_RECORDED", f"Medication recorded: {item.medication_name}", f"{item.dose} {item.frequency}")
    log_audit(db, action="PATIENT_MEDICATION_CREATE", entity_type="PATIENT_MEDICATION", entity_id=item.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=patient.registered_branch_id)
    db.commit(); db.refresh(item); return item

@router.patch("/{patient_id}/medications/{medication_id}", response_model=PatientMedicationOut)
def update_patient_medication(patient_id: str, medication_id: str, payload: PatientMedicationUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("clinical.write"))):
    patient = _patient_or_404(db, patient_id); assert_patient_scope(db, current_user, patient.id)
    item = db.query(PatientMedication).filter(PatientMedication.id == medication_id, PatientMedication.patient_id == patient.id).first()
    if not item: raise HTTPException(404, "Medication not found.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes: raise HTTPException(422, "Provide at least one medication field to update.")
    for key, value in changes.items(): setattr(item, key, value)
    _clinical_event(db, patient, current_user, "PATIENT_MEDICATION_UPDATED", f"Medication updated: {item.medication_name}", item.status)
    log_audit(db, action="PATIENT_MEDICATION_UPDATE", entity_type="PATIENT_MEDICATION", entity_id=item.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=patient.registered_branch_id, new_state=changes)
    db.commit(); db.refresh(item); return item

@router.patch("/{patient_id}/allergies/{allergy_id}", response_model=PatientAllergyOut)
def update_patient_allergy(patient_id: str, allergy_id: str, payload: PatientAllergyUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("clinical.write"))):
    patient = _patient_or_404(db, patient_id); assert_patient_scope(db, current_user, patient.id)
    item = db.query(PatientAllergy).filter(PatientAllergy.id == allergy_id, PatientAllergy.patient_id == patient.id).first()
    if not item: raise HTTPException(404, "Allergy not found.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes: raise HTTPException(422, "Provide at least one allergy field to update.")
    for key, value in changes.items(): setattr(item, key, value)
    _clinical_event(db, patient, current_user, "ALLERGY_UPDATED", f"Allergy updated: {item.allergen}", item.status)
    log_audit(db, action="PATIENT_ALLERGY_UPDATE", entity_type="PATIENT_ALLERGY", entity_id=item.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=patient.registered_branch_id, new_state=changes)
    db.commit(); db.refresh(item); return item
