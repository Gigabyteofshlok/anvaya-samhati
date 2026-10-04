"""A deliberately patient-scoped aggregate API for the portal home screen."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.admission import Admission
from app.models.clinical import PatientEvent
from app.models.identity import User
from app.models.phase5 import Invoice, LabOrder, Prescription
from app.models.phase6 import Discharge, InsuranceClaim, InsurancePolicy, PatientPortalLink

router = APIRouter(prefix="/portal", tags=["Patient portal"])


@router.get("/me")
def my_portal(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "PATIENT":
        raise HTTPException(403, "This endpoint is reserved for patient portal accounts.")
    link = db.query(PatientPortalLink).filter(PatientPortalLink.user_id == current_user.id).first()
    if not link:
        raise HTTPException(404, "No patient record is linked to this portal account.")
    patient = link.patient
    return {
        "patient": {"id": patient.id, "patient_id": patient.patient_id, "name": f"{patient.first_name} {patient.last_name}", "mobile": patient.mobile, "email": patient.email},
        "admissions": [{"id": x.id, "number": x.admission_number, "status": x.status, "admitted_at": x.admitted_at, "discharged_at": x.discharged_at} for x in db.query(Admission).filter(Admission.patient_id == patient.id).order_by(Admission.admitted_at.desc()).all()],
        "laboratory_orders": [{"id": x.id, "number": x.order_number, "test": x.test.name, "status": x.status} for x in db.query(LabOrder).filter(LabOrder.patient_id == patient.id).all()],
        "prescriptions": [{"id": x.id, "number": x.prescription_number, "status": x.status} for x in db.query(Prescription).filter(Prescription.patient_id == patient.id).all()],
        "invoices": [{"id": x.id, "number": x.invoice_number, "status": x.status, "total": x.total_amount, "paid": x.paid_amount} for x in db.query(Invoice).filter(Invoice.patient_id == patient.id).all()],
        "policies": [{"id": x.id, "number": x.policy_number, "status": x.status} for x in db.query(InsurancePolicy).filter(InsurancePolicy.patient_id == patient.id).all()],
        "claims": [{"id": x.id, "number": x.claim_number, "status": x.status} for x in db.query(InsuranceClaim).filter(InsuranceClaim.patient_id == patient.id).all()],
        "discharges": [{"id": x.id, "status": x.status, "summary": x.clinical_summary} for x in db.query(Discharge).filter(Discharge.patient_id == patient.id).all()],
        "timeline": [{"type": x.event_type, "title": x.title, "timestamp": x.timestamp} for x in db.query(PatientEvent).filter(PatientEvent.patient_id == patient.id).order_by(PatientEvent.timestamp.desc()).limit(50).all()],
    }
