from datetime import datetime, timezone
from fastapi import HTTPException
from app.db.mongodb import get_db


def _serialize(doc: dict) -> dict:
    """Convert datetime objects to ISO strings for JSON serialization."""
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


async def get_visits_for_employee(employee_id: str, status: str = None, limit: int = 50) -> list:
    db = get_db()
    query = {"employee_id": employee_id}
    if status:
        query["status"] = status
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


async def update_visit_status(visit_id: str, employee_id: str, status: str) -> dict:
    db = get_db()
    now = datetime.now(timezone.utc)
    result = await db.visits.find_one_and_update(
        {"visit_id": visit_id, "employee_id": employee_id},
        {"$set": {"status": status, "updated_at": now}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Visit not found or unauthorized")
    result.pop("_id", None)
    return _serialize(result)


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