from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import assert_patient_scope, require_permission
from app.core.database import get_db
from app.models.clinical import PatientEvent
from app.models.identity import User
from app.models.phase6 import InsuranceClaim, InsuranceClaimItem, InsurancePolicy, InsuranceProvider, PreAuthorization
from app.schemas.phase6 import ClaimCreate, PolicyCreate, PreAuthorizationCreate, ProviderCreate, StatusDecision
from app.services.audit_service import log_audit

router = APIRouter(prefix="/insurance", tags=["Insurance / TPA"])
TERMINAL = {"SETTLED", "CANCELLED", "REJECTED"}


def policy_out(row: InsurancePolicy) -> dict:
    return {"id": row.id, "patient_id": row.patient_id, "patient_name": f"{row.patient.first_name} {row.patient.last_name}", "provider": row.provider.name, "policy_number": row.policy_number, "member_id": row.member_id, "coverage_amount": row.coverage_amount, "valid_from": row.valid_from, "valid_to": row.valid_to, "status": row.status}


def claim_out(row: InsuranceClaim) -> dict:
    return {"id": row.id, "claim_number": row.claim_number, "patient_id": row.patient_id, "patient_name": f"{row.patient.first_name} {row.patient.last_name}", "policy_number": row.policy.policy_number, "invoice_id": row.invoice_id, "status": row.status, "submitted_amount": row.submitted_amount, "approved_amount": row.approved_amount, "rejected_amount": row.rejected_amount, "items": [{"id": item.id, "description": item.description, "claimed_amount": item.claimed_amount, "approved_amount": item.approved_amount, "rejected_amount": item.rejected_amount} for item in row.items]}


@router.get("/providers")
def providers(db: Session = Depends(get_db), current_user: User = Depends(require_permission("insurance.view"))):
    return db.query(InsuranceProvider).filter(InsuranceProvider.is_active.is_(True)).order_by(InsuranceProvider.name).all()


@router.post("/providers", status_code=status.HTTP_201_CREATED)
def create_provider(data: ProviderCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("insurance.manage"))):
    if db.query(InsuranceProvider).filter((InsuranceProvider.code == data.code) | (InsuranceProvider.name == data.name)).first(): raise HTTPException(409, "Insurance provider already exists.")
    row = InsuranceProvider(**data.model_dump()); db.add(row); db.flush(); log_audit(db, action="INSURANCE_PROVIDER_CREATED", entity_type="INSURANCE_PROVIDER", entity_id=row.id, actor_id=current_user.id, actor_email=current_user.email); db.commit(); return row


@router.get("/policies")
def policies(patient_id: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(require_permission("insurance.view"))):
    query = db.query(InsurancePolicy).options(joinedload(InsurancePolicy.patient), joinedload(InsurancePolicy.provider))
    if patient_id:
        assert_patient_scope(db, current_user, patient_id); query = query.filter(InsurancePolicy.patient_id == patient_id)
    elif current_user.role == "PATIENT":
        from app.models.phase6 import PatientPortalLink
        link = db.query(PatientPortalLink).filter(PatientPortalLink.user_id == current_user.id).first()
        if not link: return []
        query = query.filter(InsurancePolicy.patient_id == link.patient_id)
    return [policy_out(row) for row in query.order_by(InsurancePolicy.created_at.desc()).all()]


@router.post("/policies", status_code=status.HTTP_201_CREATED)
def create_policy(data: PolicyCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("insurance.manage"))):
    if data.valid_to < data.valid_from: raise HTTPException(422, "Policy expiry must follow policy start.")
    if db.query(InsurancePolicy).filter(InsurancePolicy.policy_number == data.policy_number).first(): raise HTTPException(409, "Policy number already exists.")
    row = InsurancePolicy(**data.model_dump()); db.add(row); db.flush(); db.add(PatientEvent(patient_id=row.patient_id, actor_id=current_user.id, event_type="INSURANCE_POLICY_ADDED", title="Insurance policy added", description=row.policy_number, source_module="INSURANCE")); log_audit(db, action="INSURANCE_POLICY_CREATED", entity_type="INSURANCE_POLICY", entity_id=row.id, actor_id=current_user.id, actor_email=current_user.email); db.commit(); return policy_out(db.query(InsurancePolicy).options(joinedload(InsurancePolicy.patient), joinedload(InsurancePolicy.provider)).filter(InsurancePolicy.id == row.id).one())


@router.post("/preauthorizations", status_code=status.HTTP_201_CREATED)
def create_preauth(data: PreAuthorizationCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("insurance.manage"))):
    policy = db.get(InsurancePolicy, data.policy_id)
    if not policy or policy.patient_id != data.patient_id: raise HTTPException(422, "Policy must belong to the selected patient.")
    row = PreAuthorization(request_number=f"PA-{db.query(PreAuthorization).count() + 1:06d}", requested_by_id=current_user.id, **data.model_dump()); db.add(row); db.flush(); db.add(PatientEvent(patient_id=row.patient_id, actor_id=current_user.id, event_type="PREAUTHORIZATION_REQUESTED", title="Preauthorization requested", description=row.request_number, source_module="INSURANCE")); log_audit(db, action="PREAUTH_CREATED", entity_type="PREAUTHORIZATION", entity_id=row.id, actor_id=current_user.id, actor_email=current_user.email); db.commit(); return {"id": row.id, "request_number": row.request_number, "status": row.status}


@router.post("/claims", status_code=status.HTTP_201_CREATED)
def create_claim(data: ClaimCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("insurance.manage"))):
    policy = db.get(InsurancePolicy, data.policy_id)
    if not policy or policy.patient_id != data.patient_id: raise HTTPException(422, "Policy must belong to the selected patient.")
    row = InsuranceClaim(claim_number=f"CLM-{db.query(InsuranceClaim).count() + 1:06d}", created_by_id=current_user.id, policy_id=data.policy_id, patient_id=data.patient_id, invoice_id=data.invoice_id, admission_id=data.admission_id, submitted_amount=sum(item.claimed_amount for item in data.items))
    db.add(row); db.flush()
    for item in data.items: db.add(InsuranceClaimItem(claim_id=row.id, **item.model_dump()))
    db.add(PatientEvent(patient_id=row.patient_id, actor_id=current_user.id, event_type="INSURANCE_CLAIM_CREATED", title="Insurance claim created", description=row.claim_number, source_module="INSURANCE")); log_audit(db, action="INSURANCE_CLAIM_CREATED", entity_type="INSURANCE_CLAIM", entity_id=row.id, actor_id=current_user.id, actor_email=current_user.email); db.commit()
    return claim_out(db.query(InsuranceClaim).options(joinedload(InsuranceClaim.patient), joinedload(InsuranceClaim.policy), joinedload(InsuranceClaim.items)).filter(InsuranceClaim.id == row.id).one())


@router.get("/claims")
def claims(patient_id: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(require_permission("insurance.view"))):
    query = db.query(InsuranceClaim).options(joinedload(InsuranceClaim.patient), joinedload(InsuranceClaim.policy), joinedload(InsuranceClaim.items))
    if patient_id:
        assert_patient_scope(db, current_user, patient_id); query = query.filter(InsuranceClaim.patient_id == patient_id)
    elif current_user.role == "PATIENT":
        from app.models.phase6 import PatientPortalLink
        link = db.query(PatientPortalLink).filter(PatientPortalLink.user_id == current_user.id).first()
        if not link: return []
        query = query.filter(InsuranceClaim.patient_id == link.patient_id)
    return [claim_out(row) for row in query.order_by(InsuranceClaim.created_at.desc()).all()]


@router.get("/claims/{claim_id}")
def claim(claim_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_permission("insurance.view"))):
    row = db.query(InsuranceClaim).options(joinedload(InsuranceClaim.patient), joinedload(InsuranceClaim.policy), joinedload(InsuranceClaim.items)).filter(InsuranceClaim.id == claim_id).first()
    if not row: raise HTTPException(404, "Claim not found.")
    assert_patient_scope(db, current_user, row.patient_id); return claim_out(row)


@router.post("/claims/{claim_id}/decision")
def decide_claim(claim_id: str, data: StatusDecision, db: Session = Depends(get_db), current_user: User = Depends(require_permission("insurance.manage"))):
    row = db.query(InsuranceClaim).filter(InsuranceClaim.id == claim_id).with_for_update().first()
    if not row: raise HTTPException(404, "Claim not found.")
    allowed = {"SUBMITTED", "UNDER_REVIEW", "APPROVED", "PARTIALLY_APPROVED", "REJECTED", "SETTLED", "CANCELLED"}
    if data.status not in allowed: raise HTTPException(422, "Invalid claim status.")
    row.status, row.approved_amount, row.rejected_amount, row.reviewed_by_id = data.status, data.approved_amount, data.rejected_amount, current_user.id
    db.add(PatientEvent(patient_id=row.patient_id, actor_id=current_user.id, event_type="INSURANCE_CLAIM_STATUS_CHANGED", title="Insurance claim updated", description=f"{row.claim_number}: {data.status}", source_module="INSURANCE")); log_audit(db, action="INSURANCE_CLAIM_DECISION", entity_type="INSURANCE_CLAIM", entity_id=row.id, actor_id=current_user.id, actor_email=current_user.email, new_state={"status": data.status, "approved_amount": data.approved_amount}); db.commit(); return {"id": row.id, "status": row.status}
