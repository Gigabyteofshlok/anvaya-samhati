from typing import Generator, List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.core.permissions import ROLE_PERMISSIONS, SystemRole
from app.models.identity import User
from app.models.phase6 import PatientPortalLink

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account.",
        )
    return user

def require_permission(permission: str) -> Callable:
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == SystemRole.SUPER_ADMIN.value:
            return current_user
        
        user_perms = ROLE_PERMISSIONS.get(current_user.role, set())
        if permission not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required permission: '{permission}'."
            )
        return current_user
    return permission_checker

def require_role(roles: List[str]) -> Callable:
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == SystemRole.SUPER_ADMIN.value or current_user.role in roles:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation restricted to roles: {', '.join(roles)}."
        )
    return role_checker


def assert_patient_scope(db: Session, current_user: User, patient_id: str) -> None:
    """Block a patient-role account from reading or altering another patient's records."""
    if current_user.role != SystemRole.PATIENT.value:
        return
    link = db.query(PatientPortalLink).filter(PatientPortalLink.user_id == current_user.id).first()
    if not link or link.patient_id != patient_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient accounts may access only their own records.")
