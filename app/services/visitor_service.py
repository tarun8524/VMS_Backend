import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from app.db.mongodb import get_db
from app.db import qdrant as qdrant_db
from app.core.config import settings


async def register_visitor(
    name: str,
    phone: str,
    email: str,
    employee_to_visit_id: str,
    purpose: str,
    encoding: list[float],
    thumbnail: str,
) -> dict:
    db = get_db()
    visitor_uid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = {
        "visitor_uid": visitor_uid,
        "name": name,
        "phone": phone,
        "email": email,
        "employee_to_visit_id": employee_to_visit_id,
        "purpose": purpose,
        "thumbnail": thumbnail,
        "created_at": now,
    }
    await db.visitors.insert_one(doc)

    # Store face in Qdrant
    qdrant_db.upsert_face(
        visitor_uid=visitor_uid,
        encoding=encoding,
        meta={
            "name": name,
            "phone": phone,
            "email": email,
            "thumbnail": thumbnail,
        },
    )

    # Create visit record
    visit_doc = {
        "visit_id": str(uuid.uuid4()),
        "visitor_uid": visitor_uid,
        "visitor_name": name,
        "visitor_phone": phone,
        "visitor_email": email,
        "visitor_thumbnail": thumbnail,
        "employee_id": employee_to_visit_id,
        "purpose": purpose,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    await db.visits.insert_one(visit_doc)

    # Email the employee — import here to avoid circular deps
    from app.services.visit_service import notify_employee_new_visit
    try:
        await notify_employee_new_visit(visit_doc)
    except Exception:
        pass  # Email failure must not break registration

    return doc


async def get_all_visitors(limit: int = 100) -> list:
    db = get_db()
    cursor = db.visitors.find({}, {"_id": 0}).limit(limit).sort("created_at", -1)
    return await cursor.to_list(length=limit)


async def get_visitor_by_uid(visitor_uid: str) -> dict:
    db = get_db()
    doc = await db.visitors.find_one({"visitor_uid": visitor_uid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return doc


async def delete_visitor(visitor_uid: str):
    db = get_db()
    result = await db.visitors.delete_one({"visitor_uid": visitor_uid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Visitor not found")
    qdrant_db.delete_face(visitor_uid)
    await db.visits.delete_many({"visitor_uid": visitor_uid})


async def recognize_visitor(encoding: list[float], limit: int = 5) -> dict:
    hits = qdrant_db.search_face(encoding, limit=limit)
    threshold = settings.MATCH_THRESHOLD

    results = []
    matched = []
    for h in hits:
        p = h.payload or {}
        distance = round(h.score, 4)
        is_match = distance < threshold
        item = {
            "visitor_uid": str(h.id),
            "name": p.get("name", ""),
            "phone": p.get("phone", ""),
            "email": p.get("email", ""),
            "distance": distance,
            "is_match": is_match,
            "thumbnail": p.get("thumbnail"),
        }
        results.append(item)
        if is_match:
            matched.append(item)

    return {"matched": matched, "all_results": results, "threshold": threshold}
