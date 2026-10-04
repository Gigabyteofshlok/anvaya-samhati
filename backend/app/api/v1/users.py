from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.identity import User
from app.schemas.auth import UserOut, UserCreate
from app.api.deps import get_current_user, require_permission
from app.api.v1.auth import build_user_out
from app.services.audit_service import log_audit

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("", response_model=List[UserOut])
def get_users(
    role: Optional[str] = None,
    branch_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(User).filter(User.is_active == True)
    if role:
        query = query.filter(User.role == role)
    if branch_id:
        query = query.filter(User.branch_id == branch_id)
    users = query.order_by(User.full_name).all()
    return [build_user_out(u) for u in users]

@router.post("", response_model=UserOut)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.manage"))
):
    existing = db.query(User).filter(
        (User.username == user_in.username) | (User.email == user_in.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this username or email already exists."
        )

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        branch_id=user_in.branch_id,
        specialization=user_in.specialization,
        license_number=user_in.license_number,
        phone=user_in.phone
    )
    db.add(new_user)
    db.flush()

    log_audit(
        db=db,
        action="USER_CREATE",
        entity_type="USER",
        entity_id=new_user.id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        branch_id=new_user.branch_id,
        new_state={"username": new_user.username, "email": new_user.email, "role": new_user.role},
        notes=f"Admin created user {new_user.email}"
    )
    db.commit()
    db.refresh(new_user)
    return build_user_out(new_user)
