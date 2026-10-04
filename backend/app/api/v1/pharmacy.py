from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import assert_patient_scope, require_permission
from app.core.database import get_db
from app.models.clinical import PatientEvent
from app.models.identity import User
from app.models.phase5 import InventoryBatch, Medicine, Prescription, PrescriptionItem, StockMovement
from app.schemas.phase5 import DispenseCreate, InventoryBatchCreate, MedicineCreate, PrescriptionCreate
from app.services.audit_service import log_audit
from app.services.billing_service import add_event_charge

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])


def prescription_out(item: Prescription) -> dict:
    return {"id": item.id, "prescription_number": item.prescription_number, "status": item.status,
        "patient_id": item.patient_id, "patient_name": f"{item.patient.first_name} {item.patient.last_name}",
        "patient_code": item.patient.patient_id, "prescribed_by": item.prescribed_by.full_name, "created_at": item.created_at,
        "items": [{"id": line.id, "medicine_id": line.medicine_id, "medicine_name": line.medicine.generic_name,
            "brand_name": line.medicine.brand_name, "quantity": line.quantity, "dispensed_quantity": line.dispensed_quantity,
            "status": line.status, "dosage": line.dosage, "frequency": line.frequency} for line in item.items]}


@router.get("/medicines")
def list_medicines(db: Session = Depends(get_db), current_user: User = Depends(require_permission("pharmacy.view"))):
    medicines = db.query(Medicine).filter(Medicine.is_active.is_(True)).order_by(Medicine.generic_name).all()
    return [{"id": med.id, "code": med.code, "generic_name": med.generic_name, "brand_name": med.brand_name,
        "category": med.category, "strength": med.strength, "dosage_form": med.dosage_form, "reorder_threshold": med.reorder_threshold,
        "stock_quantity": sum(batch.quantity_on_hand for batch in db.query(InventoryBatch).filter(InventoryBatch.medicine_id == med.id).all())} for med in medicines]


@router.post("/medicines", status_code=status.HTTP_201_CREATED)
def create_medicine(data: MedicineCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("pharmacy.manage"))):
    if db.query(Medicine).filter(Medicine.code == data.code).first(): raise HTTPException(409, "Medicine code already exists.")
    item = Medicine(**data.model_dump()); db.add(item); db.flush()
    log_audit(db, action="MEDICINE_CREATED", entity_type="MEDICINE", entity_id=item.id, actor_id=current_user.id, actor_email=current_user.email)
    db.commit(); db.refresh(item); return item


@router.get("/inventory")
def list_inventory(branch_id: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(require_permission("pharmacy.view"))):
    query = db.query(InventoryBatch).options(joinedload(InventoryBatch.medicine))
    if branch_id: query = query.filter(InventoryBatch.branch_id == branch_id)
    return [{"id": batch.id, "medicine_id": batch.medicine_id, "medicine_name": batch.medicine.generic_name, "batch_number": batch.batch_number,
        "expiry_date": batch.expiry_date, "quantity_on_hand": batch.quantity_on_hand, "unit_price": batch.unit_price,
        "supplier": batch.supplier, "is_expired": batch.expiry_date < date.today(), "near_expiry": 0 <= (batch.expiry_date - date.today()).days <= 90} for batch in query.order_by(InventoryBatch.expiry_date).all()]


@router.post("/inventory", status_code=status.HTTP_201_CREATED)
def add_inventory(data: InventoryBatchCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("pharmacy.manage"))):
    if not db.get(Medicine, data.medicine_id): raise HTTPException(404, "Medicine not found.")
    batch = InventoryBatch(**data.model_dump()); db.add(batch); db.flush()
    db.add(StockMovement(batch_id=batch.id, movement_type="RECEIPT", quantity=batch.quantity_on_hand, performed_by_id=current_user.id, notes="Initial inventory receipt"))
    log_audit(db, action="INVENTORY_RECEIVED", entity_type="INVENTORY_BATCH", entity_id=batch.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=batch.branch_id)
    db.commit(); return {"id": batch.id, "quantity_on_hand": batch.quantity_on_hand}


@router.get("/prescriptions")
def list_prescriptions(patient_id: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(require_permission("pharmacy.view"))):
    query = db.query(Prescription).options(joinedload(Prescription.patient), joinedload(Prescription.prescribed_by), joinedload(Prescription.items).joinedload(PrescriptionItem.medicine))
    if patient_id:
        assert_patient_scope(db, current_user, patient_id)
        query = query.filter(Prescription.patient_id == patient_id)
    elif current_user.role == "PATIENT":
        from app.models.phase6 import PatientPortalLink
        link = db.query(PatientPortalLink).filter(PatientPortalLink.user_id == current_user.id).first()
        if not link: return []
        query = query.filter(Prescription.patient_id == link.patient_id)
    return [prescription_out(row) for row in query.order_by(Prescription.created_at.desc()).limit(200).all()]


@router.post("/prescriptions", status_code=status.HTTP_201_CREATED)
def create_prescription(data: PrescriptionCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("pharmacy.manage"))):
    for line in data.items:
        if not db.get(Medicine, line.medicine_id): raise HTTPException(404, "Medicine not found.")
    prescription = Prescription(prescription_number=f"RX-{db.query(Prescription).count() + 1:06d}", patient_id=data.patient_id, branch_id=data.branch_id, encounter_id=data.encounter_id, admission_id=data.admission_id, prescribed_by_id=current_user.id, notes=data.notes)
    db.add(prescription); db.flush()
    for line in data.items: db.add(PrescriptionItem(prescription_id=prescription.id, **line.model_dump()))
    db.add(PatientEvent(patient_id=prescription.patient_id, encounter_id=prescription.encounter_id, actor_id=current_user.id, event_type="PRESCRIPTION_CREATED", title="Prescription created", description=prescription.prescription_number, source_module="PHARMACY"))
    db.commit()
    return prescription_out(db.query(Prescription).options(joinedload(Prescription.patient), joinedload(Prescription.prescribed_by), joinedload(Prescription.items).joinedload(PrescriptionItem.medicine)).filter(Prescription.id == prescription.id).one())


@router.post("/prescriptions/items/{item_id}/dispense")
def dispense(item_id: str, data: DispenseCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("pharmacy.manage"))):
    """Stock decrement, dispensing event and pharmacy charge commit together."""
    # Lock only the mutable prescription-item row. PostgreSQL rejects FOR UPDATE
    # over the nullable sides introduced by eager outer joins.
    item = db.query(PrescriptionItem).filter(PrescriptionItem.id == item_id).with_for_update().first()
    batch = db.query(InventoryBatch).filter(InventoryBatch.id == data.batch_id).with_for_update().first()
    if not item or not batch: raise HTTPException(404, "Prescription item or inventory batch not found.")
    if batch.medicine_id != item.medicine_id: raise HTTPException(409, "Selected batch does not match the prescribed medicine.")
    if batch.expiry_date < date.today(): raise HTTPException(409, "Expired inventory cannot be dispensed.")
    outstanding = item.quantity - item.dispensed_quantity
    if data.quantity > outstanding: raise HTTPException(409, "Dispense quantity exceeds prescribed quantity.")
    if data.quantity > batch.quantity_on_hand: raise HTTPException(409, "Insufficient stock in this batch.")
    batch.quantity_on_hand -= data.quantity; item.dispensed_quantity += data.quantity; item.status = "DISPENSED" if item.dispensed_quantity == item.quantity else "PARTIALLY_DISPENSED"
    prescription = item.prescription
    prescription.status = "DISPENSED" if all(x.dispensed_quantity == x.quantity for x in prescription.items) else "PARTIALLY_DISPENSED"
    db.add(StockMovement(batch_id=batch.id, prescription_item_id=item.id, movement_type="DISPENSE", quantity=-data.quantity, performed_by_id=current_user.id))
    add_event_charge(db, patient_id=prescription.patient_id, branch_id=prescription.branch_id, encounter_id=prescription.encounter_id, admission_id=prescription.admission_id, charge_type="PHARMACY", description=f"Medicine: {item.medicine.generic_name}", amount=round(batch.unit_price * data.quantity, 2), source_entity_type="PRESCRIPTION_ITEM", source_entity_id=item.id)
    db.add(PatientEvent(patient_id=prescription.patient_id, encounter_id=prescription.encounter_id, actor_id=current_user.id, event_type="MEDICINE_DISPENSED", title=f"Medication dispensed: {item.medicine.generic_name}", description=f"Quantity {data.quantity}", source_module="PHARMACY"))
    log_audit(db, action="MEDICINE_DISPENSED", entity_type="PRESCRIPTION_ITEM", entity_id=item.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=prescription.branch_id)
    db.commit(); return {"item_id": item.id, "status": item.status, "remaining_stock": batch.quantity_on_hand}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_permission("pharmacy.view"))):
    batches = db.query(InventoryBatch).options(joinedload(InventoryBatch.medicine)).all()
    return {"batches": len(batches), "low_stock": sum(1 for b in batches if b.quantity_on_hand <= b.medicine.reorder_threshold), "expired": sum(1 for b in batches if b.expiry_date < date.today()), "near_expiry": sum(1 for b in batches if 0 <= (b.expiry_date - date.today()).days <= 90), "pending_prescriptions": db.query(Prescription).filter(Prescription.status.in_(["PRESCRIBED", "PARTIALLY_DISPENSED"])).count()}
