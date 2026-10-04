from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.api.deps import assert_patient_scope, require_permission
from app.core.database import get_db
from app.models.clinical import PatientEvent
from app.models.identity import User
from app.models.phase5 import LabOrder, LabResult, LabTestCatalog
from app.models.phase6 import LabOrderItem, LabResultValue, LabTestComponent
from app.schemas.phase6 import LabComponentCreate, StructuredResultSave
from app.schemas.phase5 import LabOrderCreate, LabResultCreate, LabTestCreate
from app.services.audit_service import log_audit
from app.services.billing_service import add_event_charge

router = APIRouter(prefix="/laboratory", tags=["Laboratory"])


def _number(db: Session) -> str:
    return f"LAB-{db.query(LabOrder).count() + 1:06d}"


def order_out(order: LabOrder) -> dict:
    return {
        "id": order.id, "order_number": order.order_number, "status": order.status, "priority": order.priority,
        "patient_id": order.patient_id, "patient_name": f"{order.patient.first_name} {order.patient.last_name}",
        "patient_code": order.patient.patient_id, "test_id": order.test_id, "test_name": order.test.name,
        "test_code": order.test.code, "category": order.test.category, "ordering_doctor": order.ordering_doctor.full_name,
        "assigned_technician": order.assigned_technician.full_name if order.assigned_technician else None,
        "sample_collected_at": order.sample_collected_at, "created_at": order.created_at,
        "result": None if not order.result else {"id": order.result.id, "value": order.result.result_value, "unit": order.result.unit,
            "reference_range": order.result.reference_range, "flag": order.result.flag, "report_status": order.result.report_status,
            "verified_at": order.result.verified_at},
    }


@router.get("/catalog")
def list_catalog(db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.view"))):
    return db.query(LabTestCatalog).filter(LabTestCatalog.is_active.is_(True)).order_by(LabTestCatalog.category, LabTestCatalog.name).all()


@router.get("/catalog/{test_id}/components")
def list_components(test_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.view"))):
    if not db.get(LabTestCatalog, test_id): raise HTTPException(404, "Lab test not found.")
    return db.query(LabTestComponent).filter(LabTestComponent.test_id == test_id).order_by(LabTestComponent.display_order).all()


@router.post("/catalog/{test_id}/components", status_code=status.HTTP_201_CREATED)
def create_component(test_id: str, data: LabComponentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.manage"))):
    if not db.get(LabTestCatalog, test_id): raise HTTPException(404, "Lab test not found.")
    if db.query(LabTestComponent).filter(LabTestComponent.test_id == test_id, LabTestComponent.code == data.code).first(): raise HTTPException(409, "Component code already exists for this test.")
    row = LabTestComponent(test_id=test_id, **data.model_dump()); db.add(row); db.flush()
    log_audit(db, action="LAB_COMPONENT_CREATED", entity_type="LAB_TEST_COMPONENT", entity_id=row.id, actor_id=current_user.id, actor_email=current_user.email)
    db.commit(); db.refresh(row); return row


@router.post("/catalog", status_code=status.HTTP_201_CREATED)
def create_catalog_item(data: LabTestCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.manage"))):
    if db.query(LabTestCatalog).filter(LabTestCatalog.code == data.code).first():
        raise HTTPException(409, "A laboratory test with this code already exists.")
    test = LabTestCatalog(**data.model_dump())
    db.add(test); db.flush()
    log_audit(db, action="LAB_TEST_CREATED", entity_type="LAB_TEST", entity_id=test.id, actor_id=current_user.id, actor_email=current_user.email, notes=f"Created lab test {test.code}")
    db.commit(); db.refresh(test)
    return test


@router.get("/orders")
def list_orders(patient_id: str | None = None, order_status: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.view"))):
    query = db.query(LabOrder).options(joinedload(LabOrder.patient), joinedload(LabOrder.test), joinedload(LabOrder.ordering_doctor), joinedload(LabOrder.assigned_technician), joinedload(LabOrder.result))
    if patient_id:
        assert_patient_scope(db, current_user, patient_id)
        query = query.filter(LabOrder.patient_id == patient_id)
    elif current_user.role == "PATIENT":
        # A patient never receives an unscoped laboratory queue.
        from app.models.phase6 import PatientPortalLink
        link = db.query(PatientPortalLink).filter(PatientPortalLink.user_id == current_user.id).first()
        if not link: return []
        query = query.filter(LabOrder.patient_id == link.patient_id)
    if order_status: query = query.filter(LabOrder.status == order_status)
    return [order_out(item) for item in query.order_by(desc(LabOrder.created_at)).limit(200).all()]


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(data: LabOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.manage"))):
    test = db.get(LabTestCatalog, data.test_id)
    if not test or not test.is_active: raise HTTPException(404, "Active lab test not found.")
    order = LabOrder(order_number=_number(db), ordering_doctor_id=current_user.id, **data.model_dump())
    db.add(order); db.flush(); db.add(LabOrderItem(order_id=order.id, test_id=order.test_id))
    add_event_charge(db, patient_id=order.patient_id, branch_id=order.branch_id, encounter_id=order.encounter_id, admission_id=order.admission_id, charge_type="LABORATORY", description=f"Laboratory test: {test.name}", amount=test.price, source_entity_type="LAB_ORDER", source_entity_id=order.id)
    db.add(PatientEvent(patient_id=order.patient_id, encounter_id=order.encounter_id, actor_id=current_user.id, event_type="LAB_ORDERED", title=f"Lab ordered: {test.name}", description=f"{order.order_number} ({order.priority})", source_module="LABORATORY"))
    log_audit(db, action="LAB_ORDER_CREATED", entity_type="LAB_ORDER", entity_id=order.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=order.branch_id)
    db.commit()
    return order_out(db.query(LabOrder).filter(LabOrder.id == order.id).options(joinedload(LabOrder.patient), joinedload(LabOrder.test), joinedload(LabOrder.ordering_doctor), joinedload(LabOrder.assigned_technician), joinedload(LabOrder.result)).one())


@router.post("/orders/{order_id}/collect")
def collect_sample(order_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.manage"))):
    order = db.get(LabOrder, order_id)
    if not order: raise HTTPException(404, "Lab order not found.")
    if order.status not in {"LAB_ORDERED", "SAMPLE_PENDING"}: raise HTTPException(409, f"Sample cannot be collected from {order.status}.")
    order.status, order.sample_collected_at, order.sample_collected_by_id, order.assigned_technician_id = "SAMPLE_COLLECTED", datetime.now(timezone.utc), current_user.id, current_user.id
    db.add(PatientEvent(patient_id=order.patient_id, encounter_id=order.encounter_id, actor_id=current_user.id, event_type="LAB_SAMPLE_COLLECTED", title="Laboratory sample collected", description=order.order_number, source_module="LABORATORY"))
    db.commit(); return {"id": order.id, "status": order.status, "sample_collected_at": order.sample_collected_at}


@router.post("/orders/{order_id}/result", status_code=status.HTTP_201_CREATED)
def enter_result(order_id: str, data: LabResultCreate, db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.manage"))):
    order = db.get(LabOrder, order_id)
    if not order: raise HTTPException(404, "Lab order not found.")
    if order.result: raise HTTPException(409, "Result already exists; results are immutable after entry.")
    if order.status not in {"SAMPLE_COLLECTED", "PROCESSING"}: raise HTTPException(409, "Collect the sample before entering a result.")
    result = LabResult(order_id=order.id, entered_by_id=current_user.id, reference_range=data.reference_range or order.test.reference_range, unit=data.unit or order.test.unit, **data.model_dump(exclude={"reference_range", "unit"}))
    order.status = "RESULT_READY"; db.add(result)
    db.add(PatientEvent(patient_id=order.patient_id, encounter_id=order.encounter_id, actor_id=current_user.id, event_type="LAB_RESULT_READY", title=f"Lab result ready: {order.test.name}", description=f"Flag: {result.flag}", source_module="LABORATORY"))
    db.commit(); return {"id": result.id, "order_id": order.id, "status": order.status, "flag": result.flag}


@router.post("/orders/{order_id}/verify")
def verify_result(order_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.manage"))):
    order = db.query(LabOrder).options(joinedload(LabOrder.result)).filter(LabOrder.id == order_id).first()
    if not order or not order.result: raise HTTPException(404, "Lab result not found.")
    if order.status != "RESULT_READY": raise HTTPException(409, "Only ready results can be verified.")
    order.status, order.result.report_status, order.result.verified_by_id, order.result.verified_at = "VERIFIED", "VERIFIED", current_user.id, datetime.now(timezone.utc)
    log_audit(db, action="LAB_RESULT_VERIFIED", entity_type="LAB_RESULT", entity_id=order.result.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=order.branch_id)
    db.commit(); return {"order_id": order.id, "status": order.status}


@router.get("/orders/{order_id}/workspace")
def structured_workspace(order_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.view"))):
    order = db.query(LabOrder).options(joinedload(LabOrder.patient), joinedload(LabOrder.test), joinedload(LabOrder.result)).filter(LabOrder.id == order_id).first()
    if not order: raise HTTPException(404, "Lab order not found.")
    assert_patient_scope(db, current_user, order.patient_id)
    components = db.query(LabTestComponent).filter(LabTestComponent.test_id == order.test_id).order_by(LabTestComponent.display_order).all()
    existing = {item.component_id: item for item in db.query(LabResultValue).filter(LabResultValue.result_id == order.result.id).all()} if order.result else {}
    return {"order": order_out(order), "components": [{"id": c.id, "code": c.code, "name": c.name, "unit": c.unit, "reference_low": c.reference_low, "reference_high": c.reference_high, "reference_text": c.reference_text, "is_numeric": c.is_numeric, "value": existing[c.id].value_text if c.id in existing else None, "flag": existing[c.id].flag if c.id in existing else None} for c in components]}


@router.post("/orders/{order_id}/structured-result")
def save_structured_result(order_id: str, data: StructuredResultSave, db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.manage"))):
    order = db.query(LabOrder).filter(LabOrder.id == order_id).with_for_update().first()
    if not order: raise HTTPException(404, "Lab order not found.")
    if order.status not in {"SAMPLE_COLLECTED", "PROCESSING", "RESULT_READY"}: raise HTTPException(409, "Collect the sample before entering structured results.")
    component_ids = {item.id: item for item in db.query(LabTestComponent).filter(LabTestComponent.test_id == order.test_id).all()}
    if any(value.component_id not in component_ids for value in data.values): raise HTTPException(422, "All values must belong to the ordered test.")
    result = order.result
    if not result:
        result = LabResult(order_id=order.id, result_value="Structured component result", reference_range=order.test.reference_range, unit=order.test.unit, entered_by_id=current_user.id, report_status="DRAFT")
        db.add(result); db.flush()
    db.query(LabResultValue).filter(LabResultValue.result_id == result.id).delete()
    flags = []
    for value in data.values:
        component = component_ids[value.component_id]
        numeric = value.numeric_value
        if numeric is None and component.is_numeric:
            try: numeric = float(value.value_text)
            except ValueError: raise HTTPException(422, f"{component.name} requires a numeric value.")
        flag = "NORMAL"
        if numeric is not None and component.reference_low is not None and numeric < component.reference_low: flag = "LOW"
        if numeric is not None and component.reference_high is not None and numeric > component.reference_high: flag = "HIGH"
        flags.append(flag)
        reference = component.reference_text or (f"{component.reference_low}–{component.reference_high}" if component.reference_low is not None or component.reference_high is not None else None)
        db.add(LabResultValue(result_id=result.id, component_id=component.id, value_text=value.value_text, numeric_value=numeric, unit=component.unit, reference_range=reference, flag=flag, notes=value.notes))
    result.flag = "ABNORMAL" if any(flag != "NORMAL" for flag in flags) else "NORMAL"; result.comments = data.comments
    result.report_status = "RESULT_READY" if data.complete else "DRAFT"; order.status = "RESULT_READY" if data.complete else "PROCESSING"
    event_type = "LAB_RESULT_READY" if data.complete else "LAB_RESULT_DRAFT_SAVED"
    db.add(PatientEvent(patient_id=order.patient_id, encounter_id=order.encounter_id, actor_id=current_user.id, event_type=event_type, title=f"Structured lab result {'completed' if data.complete else 'saved'}: {order.test.name}", description=f"{len(data.values)} components recorded.", source_module="LABORATORY"))
    log_audit(db, action="LAB_STRUCTURED_RESULT_SAVED", entity_type="LAB_RESULT", entity_id=result.id, actor_id=current_user.id, actor_email=current_user.email, branch_id=order.branch_id, new_state={"component_count": len(data.values), "completed": data.complete})
    db.commit(); return {"order_id": order.id, "result_id": result.id, "status": order.status, "flag": result.flag}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_permission("lab.view"))):
    q = db.query(LabOrder)
    return {"ordered": q.filter(LabOrder.status == "LAB_ORDERED").count(), "processing": q.filter(LabOrder.status.in_(["SAMPLE_COLLECTED", "PROCESSING"])).count(), "result_ready": q.filter(LabOrder.status == "RESULT_READY").count(), "verified": q.filter(LabOrder.status == "VERIFIED").count()}
