from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.core.database import get_db
from app.models.clinical import ClinicalNote, PatientEvent
from app.models.patient import Patient
from app.models.admission import Admission
from app.models.identity import User
from app.schemas.clinical import ClinicalNoteCreate, ClinicalNoteOut, ClinicalNoteUpdate
from app.api.deps import assert_patient_scope, get_current_user, require_permission
from app.services.audit_service import log_audit

router = APIRouter(prefix="/patients", tags=["Clinical Notes"])

def build_note_out(n: ClinicalNote) -> ClinicalNoteOut:
    return ClinicalNoteOut(
        id=n.id,
        patient_id=n.patient_id,
        encounter_id=n.encounter_id,
        admission_id=n.admission_id,
        author_id=n.author_id,
        author_name=n.author.full_name if n.author else "Care Provider",
        author_role=n.author.role if n.author else "STAFF",
        note_type=n.note_type,
        title=n.title,
        content=n.content,
        created_at=n.created_at,
        updated_at=n.updated_at
    )

@router.get("/{patient_id}/notes", response_model=List[ClinicalNoteOut])
def get_patient_notes(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clinical.view"))
):
    assert_patient_scope(db, current_user, patient_id)
    notes = db.query(ClinicalNote).filter(
        ClinicalNote.patient_id == patient_id
    ).options(joinedload(ClinicalNote.author)).order_by(desc(ClinicalNote.created_at)).all()

    return [build_note_out(n) for n in notes]

@router.post("/{patient_id}/notes", response_model=ClinicalNoteOut)
def create_clinical_note(
    patient_id: str,
    note_in: ClinicalNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clinical.write"))
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    assert_patient_scope(db, current_user, patient.id)

    enc_id = note_in.encounter_id
    adm_id = note_in.admission_id

    if not adm_id:
        active_adm = db.query(Admission).filter(
            Admission.patient_id == patient.id,
            Admission.status == "ACTIVE"
        ).first()
        if active_adm:
            adm_id = active_adm.id
            enc_id = active_adm.encounter_id

    note = ClinicalNote(
        patient_id=patient.id,
        encounter_id=enc_id,
        admission_id=adm_id,
        author_id=current_user.id,
        note_type=note_in.note_type,
        title=note_in.title.strip(),
        content=note_in.content.strip()
    )
    db.add(note)
    db.flush()

    # Add timeline event
    db.add(PatientEvent(
        patient_id=patient.id,
        encounter_id=enc_id,
        actor_id=current_user.id,
        event_type="CLINICAL_NOTE_CREATED",
        title=f"Note: {note.title} ({note.note_type})",
        description=note.content[:200] + ("..." if len(note.content) > 200 else ""),
        source_module="CLINICAL"
    ))

    # Audit log
    log_audit(
        db=db,
        action="CLINICAL_NOTE_CREATE",
        entity_type="CLINICAL_NOTE",
        entity_id=note.id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        branch_id=patient.registered_branch_id,
        notes=f"Added note '{note.title}' ({note.note_type}) for patient {patient.patient_id}"
    )

    db.commit()
    db.refresh(note)
    return build_note_out(note)

@router.patch("/{patient_id}/notes/{note_id}", response_model=ClinicalNoteOut)
def update_clinical_note(patient_id: str, note_id: str, note_in: ClinicalNoteUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("clinical.write"))):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient: raise HTTPException(404, "Patient not found.")
    assert_patient_scope(db, current_user, patient.id)
    note = db.query(ClinicalNote).filter(ClinicalNote.id == note_id, ClinicalNote.patient_id == patient.id).first()
    if not note: raise HTTPException(404, "Clinical note not found.")
    # Authors can correct their own note; broader clinical amendment authority
    # is intentionally not inferred here.
    if note.author_id != current_user.id and current_user.role not in {"ADMIN", "SUPER_ADMIN"}:
        raise HTTPException(403, "Only the author or an administrator may amend this note.")
    changes = note_in.model_dump(exclude_unset=True)
    if not changes: raise HTTPException(422, "Provide at least one note field to update.")
    for key, value in changes.items(): setattr(note, key, value.strip() if isinstance(value, str) else value)
    db.add(PatientEvent(patient_id=patient.id, encounter_id=note.encounter_id, actor_id=current_user.id, event_type="CLINICAL_NOTE_UPDATED", title=f"Note amended: {note.title}", description="Clinical note updated.", source_module="CLINICAL"))
    log_audit(db, action="CLINICAL_NOTE_UPDATE", entity_type="CLINICAL_NOTE", entity_id=note.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=patient.registered_branch_id, new_state=changes)
    db.commit(); db.refresh(note); return build_note_out(note)
