"""Inference endpoints backed exclusively by explicit, versioned joblib artifacts."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import assert_patient_scope, require_permission
from app.core.database import get_db
from app.models.admission import Admission
from app.models.clinical import PatientEvent, PatientVital
from app.models.identity import User
from app.models.patient import Patient, PatientCondition
from app.models.phase5 import InventoryBatch, Medicine
from app.models.phase6 import LabResultValue
from app.services.audit_service import log_audit

try:
    from ml.inference.service import metadata, predict
except ImportError:  # normal package execution from backend root
    from backend.ml.inference.service import metadata, predict

router = APIRouter(prefix="/ai", tags=["AI decision support"])
SAFETY = "AI-generated decision support. Not a diagnosis. Human review required."


class PatientPredictionIn(BaseModel):
    patient_id: str


class BedForecastIn(BaseModel):
    branch_id: str
    ward_id: str | None = None
    day_offset: int = Field(default=1, ge=0, le=30)


def _bucket(value: str, count: int) -> int:
    return sum(value.encode("utf-8")) % count


def _patient_features(db: Session, user: User, requested_id: str) -> tuple[Patient, dict]:
    patient = db.query(Patient).filter((Patient.id == requested_id) | (Patient.patient_id == requested_id)).first()
    if not patient:
        raise HTTPException(404, "Patient not found.")
    assert_patient_scope(db, user, patient.id)
    latest = db.query(PatientVital).filter(PatientVital.patient_id == patient.id).order_by(PatientVital.timestamp.desc()).first()
    active = db.query(Admission).filter(Admission.patient_id == patient.id, Admission.status == "ACTIVE").first()
    values = db.query(LabResultValue).join(LabResultValue.component).filter(LabResultValue.numeric_value.is_not(None)).all()
    # Component IDs vary by tenant/catalog. The safely conservative defaults keep a model usable before a specific test is resulted.
    hemoglobin, wbc = 12.5, 7800.0
    for value in values:
        if value.result and value.result.order and value.result.order.patient_id == patient.id:
            name = value.component.name.upper()
            if "HEMOGLOBIN" in name: hemoglobin = value.numeric_value
            if "WBC" in name or "WHITE" in name: wbc = value.numeric_value
    age = date.today().year - patient.date_of_birth.year - ((date.today().month, date.today().day) < (patient.date_of_birth.month, patient.date_of_birth.day))
    return patient, {"age": age, "heart_rate": latest.heart_rate if latest and latest.heart_rate else 82,
        "systolic_bp": latest.bp_systolic if latest and latest.bp_systolic else 122,
        "temperature": (latest.temperature - 32) * 5 / 9 if latest and latest.temperature and latest.temperature > 45 else (latest.temperature if latest and latest.temperature else 37.0),
        "spo2": latest.spo2 if latest and latest.spo2 else 96, "respiratory_rate": latest.respiratory_rate if latest and latest.respiratory_rate else 18,
        "hemoglobin": hemoglobin, "wbc": wbc,
        "condition_count": db.query(PatientCondition).filter(PatientCondition.patient_id == patient.id, PatientCondition.status == "ACTIVE").count(),
        "admission_type": {"EMERGENCY": 2, "ELECTIVE": 1}.get(active.admission_type if active else "", 0)}


def _category(probability: float) -> str:
    return "HIGH" if probability >= .67 else "MODERATE" if probability >= .34 else "LOW"


def _record_prediction(db: Session, user: User, patient: Patient, model_name: str, value: float) -> None:
    db.add(PatientEvent(patient_id=patient.id, actor_id=user.id, event_type="AI_PREDICTION_GENERATED", title=f"AI decision support: {model_name}", description=f"Synthetic-demo model output: {value:.3f}", source_module="AI"))
    log_audit(db, action="AI_PREDICTION_GENERATED", entity_type="AI_MODEL", entity_id=model_name, actor_id=user.id, actor_email=user.email, new_state={"value": value, "model_version": "1.0.0"})
    db.commit()


@router.post("/patient-risk")
def patient_risk(data: PatientPredictionIn, db: Session = Depends(get_db), current_user: User = Depends(require_permission("ai.view"))):
    patient, features = _patient_features(db, current_user, data.patient_id)
    probability = predict("patient_risk", features); _record_prediction(db, current_user, patient, "patient_risk", probability)
    return {"patient_id": patient.id, "risk_probability": round(probability, 3), "risk_category": _category(probability), "model": metadata("patient_risk"), "safety": SAFETY}


@router.post("/length-of-stay")
def length_of_stay(data: PatientPredictionIn, db: Session = Depends(get_db), current_user: User = Depends(require_permission("ai.view"))):
    patient, features = _patient_features(db, current_user, data.patient_id)
    days = max(1.0, predict("length_of_stay", features)); _record_prediction(db, current_user, patient, "length_of_stay", days)
    return {"patient_id": patient.id, "estimated_days": round(days, 1), "model": metadata("length_of_stay"), "safety": SAFETY}


@router.post("/readmission-risk")
def readmission_risk(data: PatientPredictionIn, db: Session = Depends(get_db), current_user: User = Depends(require_permission("ai.view"))):
    patient, features = _patient_features(db, current_user, data.patient_id)
    probability = predict("readmission_risk", features); _record_prediction(db, current_user, patient, "readmission_risk", probability)
    return {"patient_id": patient.id, "readmission_probability": round(probability, 3), "risk_category": _category(probability), "model": metadata("readmission_risk"), "safety": SAFETY}


@router.get("/bed-forecast")
def bed_forecast(branch_id: str, ward_id: str | None = None, day_offset: int = 1, db: Session = Depends(get_db), current_user: User = Depends(require_permission("ai.view"))):
    if not 0 <= day_offset <= 30:
        raise HTTPException(422, "day_offset must be between 0 and 30.")
    predicted = min(100.0, max(0.0, predict("bed_occupancy", {"branch_index": _bucket(branch_id, 3), "ward_index": _bucket(ward_id or "all", 5), "day_of_week": (date.today().weekday() + day_offset) % 7, "day_offset": day_offset})))
    return {"branch_id": branch_id, "ward_id": ward_id, "day_offset": day_offset, "predicted_occupancy_percent": round(predicted, 1), "model": metadata("bed_occupancy"), "safety": SAFETY}


@router.get("/pharmacy-demand")
def pharmacy_demand(medicine_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_permission("ai.view"))):
    medicine = db.get(Medicine, medicine_id)
    if not medicine:
        raise HTTPException(404, "Medicine not found.")
    stock = sum(row.quantity_on_hand for row in db.query(InventoryBatch).filter(InventoryBatch.medicine_id == medicine_id).all())
    expected = max(0.0, predict("pharmacy_demand", {"medication_index": _bucket(medicine_id, 12), "day_of_week": date.today().weekday(), "current_stock": stock, "recent_dispenses": 0}))
    return {"medicine_id": medicine_id, "medicine_name": medicine.generic_name, "current_stock": stock, "expected_demand": round(expected, 1), "potential_low_stock": stock < expected, "reorder_priority": "HIGH" if stock < expected else "MONITOR", "model": metadata("pharmacy_demand"), "safety": SAFETY}
