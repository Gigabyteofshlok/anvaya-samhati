from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timezone
from app.core.database import get_db
from app.models.bed import Bed, BedStatus
from app.models.admission import Admission
from app.models.identity import User
from app.schemas.bed import BedOut, BedStatusUpdate, BedOccupancyStats
from app.api.deps import get_current_user, require_permission
from app.services.bed_state_machine import BedStateMachine

router = APIRouter(prefix="/beds", tags=["Beds"])

def build_bed_out(bed: Bed, active_admission: Optional[Admission] = None) -> BedOut:
    adm = active_admission
    if not adm and bed.current_admission_id and hasattr(bed, "admissions") and bed.admissions:
        adm = next((a for a in bed.admissions if a.id == bed.current_admission_id and a.status == "ACTIVE"), None)

    p_name = None
    p_id = None
    adm_num = None
    doc_name = None
    adm_time = None

    if adm:
        p_name = f"{adm.patient.first_name} {adm.patient.last_name}" if adm.patient else None
        p_id = adm.patient.patient_id if adm.patient else None
        adm_num = adm.admission_number
        doc_name = adm.attending_doctor.full_name if adm.attending_doctor else None
        adm_time = adm.admitted_at

    return BedOut(
        id=bed.id,
        bed_number=bed.bed_number,
        room_id=bed.room_id,
        ward_id=bed.ward_id,
        branch_id=bed.branch_id,
        bed_type=bed.bed_type,
        status=bed.status,
        is_isolation=bed.is_isolation,
        maintenance_notes=bed.maintenance_notes,
        tariff_rate=bed.tariff_rate,
        current_admission_id=bed.current_admission_id,
        created_at=bed.created_at,
        updated_at=bed.updated_at,
        branch_name=bed.branch.name if bed.branch else None,
        ward_name=bed.ward.name if bed.ward else None,
        room_number=bed.room.room_number if bed.room else None,
        current_patient_name=p_name,
        current_patient_id=p_id,
        current_admission_number=adm_num,
        current_doctor_name=doc_name,
        admitted_at=adm_time
    )

@router.get("", response_model=List[BedOut])
def get_beds(
    branch_id: Optional[str] = None,
    ward_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    bed_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("bed.view"))
):
    query = db.query(Bed).options(
        joinedload(Bed.branch),
        joinedload(Bed.ward),
        joinedload(Bed.room),
        joinedload(Bed.admissions).joinedload(Admission.patient),
        joinedload(Bed.admissions).joinedload(Admission.attending_doctor)
    )

    if branch_id:
        query = query.filter(Bed.branch_id == branch_id)
    if ward_id:
        query = query.filter(Bed.ward_id == ward_id)
    if status_filter:
        query = query.filter(Bed.status == status_filter)
    if bed_type:
        query = query.filter(Bed.bed_type == bed_type)
    if search:
        query = query.filter(Bed.bed_number.ilike(f"%{search.strip()}%"))

    beds = query.order_by(Bed.bed_number).all()
    return [build_bed_out(b) for b in beds]

@router.get("/stats", response_model=BedOccupancyStats)
def get_bed_stats(
    branch_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("bed.view"))
):
    query = db.query(Bed.status, func.count(Bed.id)).group_by(Bed.status)
    if branch_id:
        query = query.filter(Bed.branch_id == branch_id)
    
    rows = query.all()
    counts = {r[0]: r[1] for r in rows}

    total = sum(counts.values())
    occupied = counts.get(BedStatus.OCCUPIED.value, 0)
    available = counts.get(BedStatus.AVAILABLE.value, 0)
    reserved = counts.get(BedStatus.RESERVED.value, 0)
    cleaning = counts.get(BedStatus.CLEANING.value, 0)
    maintenance = counts.get(BedStatus.MAINTENANCE.value, 0)
    isolation = counts.get(BedStatus.ISOLATION.value, 0)

    rate = round((occupied / total * 100), 1) if total > 0 else 0.0

    return BedOccupancyStats(
        total_beds=total,
        occupied=occupied,
        available=available,
        reserved=reserved,
        cleaning=cleaning,
        maintenance=maintenance,
        isolation=isolation,
        occupancy_rate_pct=rate
    )

@router.get("/action-priorities")
def bed_action_priorities(branch_id: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(require_permission("bed.view"))):
    """Transparent queue: status and persisted operational timestamps drive rank."""
    query = db.query(Bed).options(joinedload(Bed.ward), joinedload(Bed.admissions))
    if branch_id: query = query.filter(Bed.branch_id == branch_id)
    now = datetime.now(timezone.utc)
    priorities = []
    for bed in query.all():
        active = next((admission for admission in bed.admissions if admission.status == "ACTIVE"), None)
        score, action, reason = 0, "Monitor", "No immediate operational action."
        if bed.status == BedStatus.CLEANING.value:
            latest_discharge = max((admission.discharged_at for admission in bed.admissions if admission.discharged_at), default=None)
            mins = int((now - latest_discharge).total_seconds() / 60) if latest_discharge else None
            score, action = 100 + (mins or 0), "Clean and release"
            reason = f"Patient discharge has left this bed in cleaning{f' for {mins} minutes' if mins is not None else ''}."
        elif bed.status == BedStatus.RESERVED.value:
            score, action, reason = 80, "Confirm or assign", "Reserved bed requires an active admission assignment decision."
        elif bed.status == BedStatus.MAINTENANCE.value:
            score, action, reason = 70, "Maintenance review", "Maintenance status is active; keep unavailable until cleared."
        elif bed.status == BedStatus.ISOLATION.value:
            score, action, reason = 60, "Isolation review", "Isolation bed must be allocated only under isolation protocol."
        elif bed.status == BedStatus.AVAILABLE.value:
            score, action, reason = 20, "Ready for assignment", "Available and ready for an authorised admission assignment."
        elif active:
            score, action, reason = 10, "Occupied", f"Assigned to active admission {active.admission_number}."
        priorities.append({"bed_id": bed.id, "bed_number": bed.bed_number, "ward_name": bed.ward.name if bed.ward else None, "status": bed.status, "priority_score": score, "recommended_action": action, "reason": reason})
    return sorted(priorities, key=lambda item: (-item["priority_score"], item["bed_number"]))[:25]

@router.get("/{bed_id}", response_model=BedOut)
def get_bed_details(
    bed_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("bed.view"))
):
    bed = db.query(Bed).filter(Bed.id == bed_id).options(
        joinedload(Bed.branch),
        joinedload(Bed.ward),
        joinedload(Bed.room),
        joinedload(Bed.admissions).joinedload(Admission.patient),
        joinedload(Bed.admissions).joinedload(Admission.attending_doctor)
    ).first()
    if not bed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found.")
    return build_bed_out(bed)

@router.post("/{bed_id}/status", response_model=BedOut)
def update_bed_status(
    bed_id: str,
    status_update: BedStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bed = db.query(Bed).filter(Bed.id == bed_id).with_for_update().first()
    if not bed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found.")

    from app.core.permissions import ROLE_PERMISSIONS, SystemRole
    user_perms = ROLE_PERMISSIONS.get(current_user.role, set())
    if current_user.role == SystemRole.SUPER_ADMIN.value:
        pass
    elif bed.status == BedStatus.CLEANING.value and status_update.new_status == BedStatus.AVAILABLE.value:
        if "bed.clean" not in user_perms and "bed.manage" not in user_perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires bed.clean or bed.manage permission.")
    else:
        if "bed.manage" not in user_perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires bed.manage permission.")

    BedStateMachine.transition_bed(
        db=db,
        bed=bed,
        target_status=status_update.new_status,
        user=current_user,
        notes=status_update.notes
    )
    db.commit()
    db.refresh(bed)
    return build_bed_out(bed)
