from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ── Employees ──────────────────────────────────────────────────────────────────

class EmployeeRegister(BaseModel):
    name: str
    email: EmailStr
    employee_id: str          # e.g. R098
    department: Optional[str] = None
    password: str


class EmployeeLogin(BaseModel):
    email: EmailStr
    password: str


class EmployeeOut(BaseModel):
    id: str
    name: str
    email: str
    employee_id: str
    department: Optional[str] = None


class EmployeeSearchOut(BaseModel):
    name: str
    employee_id: str
    department: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee: EmployeeOut


# ── Visitors ───────────────────────────────────────────────────────────────────

class VisitorCreate(BaseModel):
    name: str
    phone: str
    email: EmailStr
    employee_to_visit_id: str   # employee_id like R098
    purpose: Optional[str] = None


class VisitorOut(BaseModel):
    visitor_uid: str
    name: str
    phone: str
    email: str
    employee_to_visit_id: str
    purpose: Optional[str] = None
    thumbnail: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Visits / Check-ins ─────────────────────────────────────────────────────────

class VisitStatus(str, Enum):
    pending     = "pending"
    approved    = "approved"
    rejected    = "rejected"
    checked_in  = "checked_in"
    checked_out = "checked_out"


class VisitOut(BaseModel):
    visit_id: str
    visitor_uid: str
    visitor_name: str
    visitor_phone: str
    visitor_email: str
    visitor_thumbnail: Optional[str] = None
    employee_id: str
    employee_name: Optional[str] = None
    purpose: Optional[str] = None
    status: VisitStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    location_id: Optional[str] = None
    location_name: Optional[str] = None
    otp: Optional[str] = None
    require_otp: Optional[bool] = None


class VisitStatusUpdate(BaseModel):
    status: VisitStatus
    location_id: Optional[str] = None   # required when status == "approved"
    require_otp: bool = False            # if True, generate & email OTP to visitor


# ── Locations ──────────────────────────────────────────────────────────────────

class LocationOut(BaseModel):
    location_id: str
    name: str
    address: str
    lat: str
    lng: str
    maps_url: str


# ── Face Search ────────────────────────────────────────────────────────────────

class FaceMatch(BaseModel):
    visitor_uid: str
    name: str
    phone: str
    email: str
    distance: float
    is_match: bool
    thumbnail: Optional[str] = None
