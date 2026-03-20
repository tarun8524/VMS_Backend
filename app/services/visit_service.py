from datetime import datetime, timezone
from fastapi import HTTPException
from app.db.mongodb import get_db
from app.services import email_service, location_service
from app.core.config import settings


def _serialize(doc: dict) -> dict:
    """Convert datetime objects to ISO strings for JSON serialization."""
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


async def get_visits_for_employee(
    employee_id: str,
    status: str = None,
    limit: int = 50,
    today_only: bool = False,
) -> list:
    db = get_db()
    query = {"employee_id": employee_id}
    if status:
        query["status"] = status
    if today_only:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        query["created_at"] = {"$gte": today_start}

    cursor = db.visits.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    visits = await cursor.to_list(length=limit)
    emp = await db.employees.find_one({"employee_id": employee_id}, {"name": 1})
    result = []
    for v in visits:
        v["employee_name"] = emp["name"] if emp else employee_id
        result.append(_serialize(v))
    return result


async def get_all_visits(limit: int = 100) -> list:
    db = get_db()
    cursor = db.visits.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_serialize(d) for d in docs]


async def update_visit_status(
    visit_id: str,
    employee_id: str,
    status: str,
    location_id: str | None = None,
    require_otp: bool = False,
) -> dict:
    db = get_db()
    now = datetime.now(timezone.utc)

    # Validate approval requires a location
    if status == "approved" and not location_id:
        raise HTTPException(
            status_code=400,
            detail="A meeting location must be selected when approving a visit.",
        )

    # Resolve location
    location = None
    if location_id:
        location = await location_service.get_location(location_id)
        if not location:
            raise HTTPException(status_code=404, detail=f"Location '{location_id}' not found")

    # Generate OTP if requested
    otp = None
    if status == "approved" and require_otp:
        otp = email_service.generate_otp()

    update_fields: dict = {"status": status, "updated_at": now}
    if location:
        update_fields["location_id"] = location["location_id"]
        update_fields["location_name"] = location["name"]
    if otp:
        update_fields["otp"] = otp
    if status == "approved":
        update_fields["require_otp"] = require_otp

    result = await db.visits.find_one_and_update(
        {"visit_id": visit_id, "employee_id": employee_id},
        {"$set": update_fields},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Visit not found or unauthorized")

    result.pop("_id", None)

    # ── Send emails ──────────────────────────────────────────────────────────
    employee = await db.employees.find_one({"employee_id": employee_id}, {"name": 1, "email": 1})
    emp_name = employee["name"] if employee else employee_id

    visitor_email = result.get("visitor_email", "")
    visitor_name  = result.get("visitor_name", "Visitor")

    if status == "approved" and location and visitor_email:
        await email_service.send_approval_to_visitor(
            visitor_email=visitor_email,
            visitor_name=visitor_name,
            employee_name=emp_name,
            location=location,
            otp=otp,
        )
    elif status == "rejected" and visitor_email:
        await email_service.send_rejection_to_visitor(
            visitor_email=visitor_email,
            visitor_name=visitor_name,
            employee_name=emp_name,
        )

    return _serialize(result)


async def notify_employee_new_visit(visit_doc: dict) -> None:
    """Fire-and-forget: email the employee that a new visitor is waiting."""
    db = get_db()
    emp = await db.employees.find_one(
        {"employee_id": visit_doc["employee_id"]},
        {"name": 1, "email": 1},
    )
    if not emp or not emp.get("email"):
        return
    await email_service.send_new_visit_notification(
        employee_email=emp["email"],
        employee_name=emp["name"],
        visitor_name=visit_doc["visitor_name"],
        visitor_phone=visit_doc["visitor_phone"],
        visitor_email=visit_doc["visitor_email"],
        purpose=visit_doc.get("purpose", ""),
        app_url=settings.APP_URL,
    )


async def get_pending_count(employee_id: str) -> int:
    db = get_db()
    return await db.visits.count_documents({"employee_id": employee_id, "status": "pending"})


async def get_dashboard_stats(employee_id: str) -> dict:
    db = get_db()
    total    = await db.visits.count_documents({"employee_id": employee_id})
    pending  = await db.visits.count_documents({"employee_id": employee_id, "status": "pending"})
    approved = await db.visits.count_documents({"employee_id": employee_id, "status": "approved"})
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today    = await db.visits.count_documents({"employee_id": employee_id, "created_at": {"$gte": today_start}})
    return {"total": total, "pending": pending, "approved": approved, "today": today}


async def search_visitor_visits(employee_id: str, query: str) -> list:
    db = get_db()
    regex = {"$regex": query, "$options": "i"}
    cursor = db.visits.find(
        {"employee_id": employee_id, "$or": [
            {"visitor_name": regex},
            {"visitor_email": regex},
            {"visitor_phone": regex},
        ]},
        {"_id": 0}
    ).sort("created_at", -1).limit(20)
    docs = await cursor.to_list(length=20)
    return [_serialize(d) for d in docs]