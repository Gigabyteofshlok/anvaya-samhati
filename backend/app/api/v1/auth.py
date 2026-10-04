from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.permissions import ROLE_PERMISSIONS, SystemRole
from app.models.identity import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.api.deps import get_current_user
from app.services.audit_service import log_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])

def build_user_out(user: User) -> UserOut:
    perms = list(ROLE_PERMISSIONS.get(user.role, set()))
    if user.role == SystemRole.SUPER_ADMIN.value:
        perms = list(ROLE_PERMISSIONS[SystemRole.SUPER_ADMIN.value])
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        branch_id=user.branch_id,
        branch_name=user.branch.name if user.branch else None,
        specialization=user.specialization,
        license_number=user.license_number,
        is_active=user.is_active,
        permissions=perms
    )

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)) -> Any:
    user = db.query(User).filter(
        (User.username == login_data.username_or_email) | (User.email == login_data.username_or_email)
    ).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled."
        )

    access_token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email, "name": user.full_name}
    )

    log_audit(
        db=db,
        action="LOGIN",
        entity_type="USER",
        entity_id=user.id,
        actor_id=user.id,
        actor_email=user.email,
        branch_id=user.branch_id,
        notes=f"User {user.email} logged in successfully."
    )
    db.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=build_user_out(user)
    )

# OAuth2 form support for Swagger UI interactive login
@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email, "name": user.full_name}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)) -> Any:
    return build_user_out(current_user)

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log_audit(
        db=db,
        action="LOGOUT",
        entity_type="USER",
        entity_id=current_user.id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        branch_id=current_user.branch_id,
        notes=f"User {current_user.email} logged out."
    )
    db.commit()
    return {"message": "Logged out successfully."}
