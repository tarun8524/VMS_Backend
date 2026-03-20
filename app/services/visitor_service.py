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
    """
    ── visitors collection (pure profile, never changed except thumbnail/name) ──
        visitor_uid, name, email, phone, thumbnail, created_at, updated_at

    ── visits collection (one document per visitor_uid) ──
        visitor_uid, visitor_name,
        visit_records: [
            visit_id, visitor_email, visitor_phone, purpose, status,
            employee_id, created_at, updated_at,
            location_id, location_name, otp, require_otp
        ]

    Deduplication: email OR phone must be unique across visitors.
    Returning visitors get their thumbnail + name updated.
    Each new visit appends one record into visit_records[].
    """
    db  = get_db()
    now = datetime.now(timezone.utc)

    # ── 1. Deduplicate by email OR phone ─────────────────────────────────────
    existing = await db.visitors.find_one(
        {"$or": [{"email": email}, {"phone": phone}]}
    )

    if existing:
        visitor_uid = existing["visitor_uid"]
        # Refresh thumbnail and name on every return visit
        await db.visitors.update_one(
            {"visitor_uid": visitor_uid},
            {"$set": {"thumbnail": thumbnail, "name": name, "updated_at": now}},
        )
        # Refresh face vector in Qdrant
        qdrant_db.upsert_face(
            visitor_uid=visitor_uid,
            encoding=encoding,
            meta={"visitor_uid": visitor_uid, "name": name,
                  "phone": phone, "email": email, "thumbnail": thumbnail},
        )
    else:
        # New visitor — create pure profile document
        visitor_uid = str(uuid.uuid4())
        await db.visitors.insert_one({
            "visitor_uid": visitor_uid,
            "name":        name,
            "email":       email,
            "phone":       phone,
            "thumbnail":   thumbnail,
            "created_at":  now,
            "updated_at":  now,
        })
        qdrant_db.upsert_face(
            visitor_uid=visitor_uid,
            encoding=encoding,
            meta={"visitor_uid": visitor_uid, "name": name,
                  "phone": phone, "email": email, "thumbnail": thumbnail},
        )

    # ── 2. Build new visit_record ─────────────────────────────────────────────
    visit_id     = str(uuid.uuid4())
    visit_record = {
        "visit_id":      visit_id,
        "visitor_email": email,
        "visitor_phone": phone,
        "purpose":       purpose,
        "status":        "pending",
        "employee_id":   employee_to_visit_id,
        "created_at":    now,
        "updated_at":    now,
        "location_id":   None,
        "location_name": None,
        "otp":           None,
        "require_otp":   False,
    }

    # ── 3. Upsert visits document (one per visitor_uid) ───────────────────────
    existing_visits = await db.visits.find_one({"visitor_uid": visitor_uid})
    if existing_visits:
        await db.visits.update_one(
            {"visitor_uid": visitor_uid},
            {
                "$push": {"visit_records": visit_record},
                "$set":  {"visitor_name": name, "updated_at": now},
            },
        )
    else:
        await db.visits.insert_one({
            "visitor_uid":   visitor_uid,
            "visitor_name":  name,
            "visit_records": [visit_record],
            "created_at":    now,
            "updated_at":    now,
        })

    # ── 4. Email the employee ─────────────────────────────────────────────────
    from app.services.visit_service import notify_employee_new_visit
    try:
        await notify_employee_new_visit(
            visitor_uid=visitor_uid,
            visitor_name=name,
            visitor_phone=phone,
            visitor_email=email,
            employee_id=employee_to_visit_id,
            purpose=purpose,
            visit_id=visit_id,
        )
    except Exception:
        pass

    # Return clean visitor profile
    out = await db.visitors.find_one({"visitor_uid": visitor_uid}, {"_id": 0})
    return out or {}


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
    await db.visits.delete_one({"visitor_uid": visitor_uid})
    qdrant_db.delete_face(visitor_uid)


async def recognize_visitor(encoding: list[float], limit: int = 5) -> dict:
    hits      = qdrant_db.search_face(encoding, limit=limit)
    threshold = settings.MATCH_THRESHOLD

    results = []
    matched = []
    for h in hits:
        p        = h.payload or {}
        distance = round(h.score, 4)
        is_match = distance < threshold
        item = {
            "visitor_uid": str(h.id),
            "name":        p.get("name", ""),
            "phone":       p.get("phone", ""),
            "email":       p.get("email", ""),
            "distance":    distance,
            "is_match":    is_match,
            "thumbnail":   p.get("thumbnail"),
        }
        results.append(item)
        if is_match:
            matched.append(item)

    return {"matched": matched, "all_results": results, "threshold": threshold}


async def get_visitors_for_employee(employee_id: str) -> list:
    """
    All unique visitors who have at least one visit record for this employee.
    Returns visitor profile + aggregate stats (total, rejected, last visit).
    """
    db = get_db()

    # Unwind visit_records, filter by employee, then group back per visitor
    pipeline = [
        {"$match":   {"visit_records.employee_id": employee_id}},
        {"$unwind":  "$visit_records"},
        {"$match":   {"visit_records.employee_id": employee_id}},
        {"$group": {
            "_id":             "$visitor_uid",
            "visitor_uid":    {"$first": "$visitor_uid"},
            "visitor_name":   {"$first": "$visitor_name"},
            "total_visits":   {"$sum": 1},
            "rejected_visits":{"$sum": {"$cond": [
                {"$eq": ["$visit_records.status", "rejected"]}, 1, 0
            ]}},
            "last_visit":     {"$max": "$visit_records.created_at"},
        }},
        {"$sort": {"last_visit": -1}},
    ]

    docs = await db.visits.aggregate(pipeline).to_list(length=500)

    # Pull thumbnails + contact from visitors collection
    uids     = [d["visitor_uid"] for d in docs]
    profiles = await db.visitors.find(
        {"visitor_uid": {"$in": uids}},
        {"_id": 0, "visitor_uid": 1, "email": 1, "phone": 1, "thumbnail": 1},
    ).to_list(length=500)
    pmap = {v["visitor_uid"]: v for v in profiles}

    result = []
    for d in docs:
        uid     = d["visitor_uid"]
        profile = pmap.get(uid, {})
        last    = d.get("last_visit")
        result.append({
            "visitor_uid":     uid,
            "name":            d.get("visitor_name", ""),
            "email":           profile.get("email", ""),
            "phone":           profile.get("phone", ""),
            "thumbnail":       profile.get("thumbnail"),
            "total_visits":    d["total_visits"],
            "rejected_visits": d["rejected_visits"],
            "last_visit":      last.isoformat() if isinstance(last, datetime) else last,
        })
    return result