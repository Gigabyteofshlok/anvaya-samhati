from typing import Optional, List
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    role: str
    branch_id: Optional[str] = None
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    phone: Optional[str] = None

class UserOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    is_active: bool
    permissions: List[str] = []

    class Config:
        from_attributes = True

TokenResponse.model_rebuild()
