from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ── Employees ──────────────────────────────────────────────────────────────────

class EmployeeRegister(BaseModel):
    name:        str
    email:       EmailStr
    employee_id: str          # e.g. R098
    department:  Optional[str] = None
    password:    str


class EmployeeLogin(BaseModel):
    email:    EmailStr
    password: str


class EmployeeOut(BaseModel):
    id:          str
    name:        str
    email:       str
    employee_id: str
    department:  Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    employee:     EmployeeOut


# ── Visitors ───────────────────────────────────────────────────────────────────
# visitors collection: pure profile, no visit data.
# Unique on email + phone — deduplication enforced at DB + service level.

class VisitorOut(BaseModel):
    visitor_uid: str
    name:        str
    email:       str
    phone:       str
    thumbnail:   Optional[str]      = None
    created_at:  Optional[datetime] = None
    updated_at:  Optional[datetime] = None


class VisitorWithStats(BaseModel):
    """Visitor profile + aggregate stats derived from visits collection."""
    visitor_uid:     str
    name:            str
    email:           str
    phone:           str
    thumbnail:       Optional[str] = None
    total_visits:    int = 0
    rejected_visits: int = 0
    last_visit:      Optional[str] = None


# ── Visit records ──────────────────────────────────────────────────────────────
# visits collection: ONE document per visitor_uid.
# visit_records[] is an embedded array — one element per individual visit.

class VisitStatus(str, Enum):
    pending     = "pending"
    approved    = "approved"
    rejected    = "rejected"
    checked_in  = "checked_in"
    checked_out = "checked_out"


class VisitRecord(BaseModel):
    """
    A single embedded visit inside visits.visit_records[].
    No visitor thumbnail here — look up visitors collection by visitor_uid.
    """
    visit_id:      str
    visitor_email: str
    visitor_phone: str
    purpose:       Optional[str] = None
    status:        VisitStatus
    employee_id:   str
    created_at:    datetime
    updated_at:    Optional[datetime] = None
    location_id:   Optional[str]  = None
    location_name: Optional[str]  = None
    otp:           Optional[str]  = None
    require_otp:   Optional[bool] = None


class VisitOut(BaseModel):
    """
    Flattened view returned by API endpoints — merges visitor profile fields
    with a single visit_record for easy rendering in the UI.
    """
    visit_id:           str
    visitor_uid:        str
    visitor_name:       str
    visitor_email:      str
    visitor_phone:      str
    visitor_thumbnail:  Optional[str]      = None
    employee_id:        str
    employee_name:      Optional[str]      = None
    purpose:            Optional[str]      = None
    status:             VisitStatus
    created_at:         str
    updated_at:         Optional[str]      = None
    location_id:        Optional[str]      = None
    location_name:      Optional[str]      = None
    otp:                Optional[str]      = None
    require_otp:        Optional[bool]     = None


class VisitStatusUpdate(BaseModel):
    status:      VisitStatus
    location_id: Optional[str] = None
    require_otp: bool = False


# ── Dashboard Stats ────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total:      int
    pending:    int
    approved:   int
    rejected:   int
    today:      int
    time_range: str


# ── Locations ──────────────────────────────────────────────────────────────────

class LocationOut(BaseModel):
    location_id: str
    name:        str
    address:     str
    lat:         str
    lng:         str
    maps_url:    str


# ── Face Search ────────────────────────────────────────────────────────────────

class FaceMatch(BaseModel):
    visitor_uid: str
    name:        str
    phone:       str
    email:       str
    distance:    float
    is_match:    bool
    thumbnail:   Optional[str] = None