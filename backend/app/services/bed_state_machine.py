from typing import Dict, Set, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.bed import Bed, BedStatus
from app.models.identity import User
from app.services.audit_service import log_audit

# Permitted state transitions
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    BedStatus.AVAILABLE.value: {
        BedStatus.RESERVED.value,
        BedStatus.OCCUPIED.value,
        BedStatus.MAINTENANCE.value,
        BedStatus.ISOLATION.value
    },
    BedStatus.RESERVED.value: {
        BedStatus.OCCUPIED.value,
        BedStatus.AVAILABLE.value
    },
    BedStatus.OCCUPIED.value: {
        BedStatus.CLEANING.value  # Beds must go to cleaning before available
    },
    BedStatus.CLEANING.value: {
        BedStatus.AVAILABLE.value
    },
    BedStatus.MAINTENANCE.value: {
        BedStatus.AVAILABLE.value
    },
    BedStatus.ISOLATION.value: {
        BedStatus.AVAILABLE.value
    }
}

class BedStateMachine:
    @staticmethod
    def can_transition(current_status: str, target_status: str) -> bool:
        if current_status == target_status:
            return True
        allowed = VALID_TRANSITIONS.get(current_status, set())
        return target_status in allowed

    @staticmethod
    def transition_bed(
        db: Session,
        bed: Bed,
        target_status: str,
        user: User,
        notes: Optional[str] = None
    ) -> Bed:
        current_status = bed.status
        if current_status == target_status:
            return bed

        if not BedStateMachine.can_transition(current_status, target_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Illegal bed status transition from '{current_status}' to '{target_status}'. Allowed transitions: {list(VALID_TRANSITIONS.get(current_status, []))}"
            )

        # Role-based restriction checks on bed actions
        if target_status == BedStatus.AVAILABLE.value and current_status == BedStatus.CLEANING.value:
            # Cleaning to available can be done by Nurse, Admin, Super Admin
            if user.role not in ["NURSE", "HOSPITAL_ADMIN", "SUPER_ADMIN", "RECEPTION"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permission to certify bed cleanliness."
                )

        old_state = {"status": current_status, "admission_id": bed.current_admission_id}
        bed.status = target_status
        if notes:
            bed.maintenance_notes = notes

        new_state = {"status": target_status, "admission_id": bed.current_admission_id}

        log_audit(
            db=db,
            action="BED_STATUS_CHANGE",
            entity_type="BED",
            entity_id=bed.id,
            actor_id=user.id,
            actor_email=user.email,
            branch_id=bed.branch_id,
            old_state=old_state,
            new_state=new_state,
            notes=f"Transitioned from {current_status} to {target_status}. Notes: {notes or 'N/A'}"
        )

        return bed
