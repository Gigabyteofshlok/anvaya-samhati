from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.organization import HospitalGroup, Branch, Department, Building, Floor, Ward, Room
from app.schemas.organization import HospitalGroupOut, BranchOut, DepartmentOut, WardOut
from app.api.deps import get_current_user
from app.models.identity import User

router = APIRouter(prefix="/organization", tags=["Organization"])

@router.get("/groups", response_model=List[HospitalGroupOut])
def get_hospital_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(HospitalGroup).all()

@router.get("/branches", response_model=List[BranchOut])
def get_branches(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Branch).filter(Branch.is_active == True).order_by(Branch.name).all()

@router.get("/branches/{branch_id}/wards", response_model=List[WardOut])
def get_branch_wards(branch_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Ward).filter(Ward.branch_id == branch_id, Ward.is_active == True).options(joinedload(Ward.rooms)).all()

@router.get("/departments", response_model=List[DepartmentOut])
def get_departments(
    branch_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Department).filter(Department.is_active == True)
    if branch_id:
        query = query.filter(Department.branch_id == branch_id)
    return query.order_by(Department.name).all()
