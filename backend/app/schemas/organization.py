from typing import Optional, List
from pydantic import BaseModel

class DepartmentOut(BaseModel):
    id: str
    branch_id: str
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

class RoomOut(BaseModel):
    id: str
    ward_id: str
    room_number: str
    room_type: str

    class Config:
        from_attributes = True

class WardOut(BaseModel):
    id: str
    branch_id: str
    floor_id: Optional[str] = None
    name: str
    ward_type: str
    gender_spec: str
    is_active: bool
    rooms: List[RoomOut] = []

    class Config:
        from_attributes = True

class FloorOut(BaseModel):
    id: str
    building_id: str
    floor_number: int
    name: str
    wards: List[WardOut] = []

    class Config:
        from_attributes = True

class BuildingOut(BaseModel):
    id: str
    branch_id: str
    name: str
    code: str
    floors: List[FloorOut] = []

    class Config:
        from_attributes = True

class BranchOut(BaseModel):
    id: str
    group_id: str
    name: str
    code: str
    address: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    buildings: List[BuildingOut] = []
    departments: List[DepartmentOut] = []

    class Config:
        from_attributes = True

class HospitalGroupOut(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    branches: List[BranchOut] = []

    class Config:
        from_attributes = True
