import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class HospitalGroup(Base):
    __tablename__ = "hospital_groups"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    branches = relationship("Branch", back_populates="group", cascade="all, delete-orphan")

class Branch(Base):
    __tablename__ = "branches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    group_id = Column(String(36), ForeignKey("hospital_groups.id"), nullable=False)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    address = Column(String(300), nullable=True)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    group = relationship("HospitalGroup", back_populates="branches")
    buildings = relationship("Building", back_populates="branch", cascade="all, delete-orphan")
    wards = relationship("Ward", back_populates="branch", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="branch", cascade="all, delete-orphan")
    users = relationship("User", back_populates="branch")

class Department(Base):
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False)
    name = Column(String(150), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    branch = relationship("Branch", back_populates="departments")

class Building(Base):
    __tablename__ = "buildings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False)
    name = Column(String(150), nullable=False)
    code = Column(String(50), nullable=False)

    branch = relationship("Branch", back_populates="buildings")
    floors = relationship("Floor", back_populates="building", cascade="all, delete-orphan")

class Floor(Base):
    __tablename__ = "floors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    building_id = Column(String(36), ForeignKey("buildings.id"), nullable=False)
    floor_number = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)

    building = relationship("Building", back_populates="floors")
    wards = relationship("Ward", back_populates="floor")

class Ward(Base):
    __tablename__ = "wards"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False)
    floor_id = Column(String(36), ForeignKey("floors.id"), nullable=True)
    name = Column(String(150), nullable=False)
    ward_type = Column(String(50), nullable=False)  # GENERAL, ICU, EMERGENCY, PRIVATE, OBSERVATION
    gender_spec = Column(String(20), default="UNISEX")  # MALE, FEMALE, UNISEX
    is_active = Column(Boolean, default=True)

    branch = relationship("Branch", back_populates="wards")
    floor = relationship("Floor", back_populates="wards")
    rooms = relationship("Room", back_populates="ward", cascade="all, delete-orphan")
    beds = relationship("Bed", back_populates="ward")

class Room(Base):
    __tablename__ = "rooms"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ward_id = Column(String(36), ForeignKey("wards.id"), nullable=False)
    room_number = Column(String(50), nullable=False)
    room_type = Column(String(50), default="STANDARD")

    ward = relationship("Ward", back_populates="rooms")
    beds = relationship("Bed", back_populates="room", cascade="all, delete-orphan")
