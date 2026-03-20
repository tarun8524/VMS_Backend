from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from app.db.mongodb import get_db
from app.services import email_service, location_service
from app.core.config import settings


def _iso(val):
    """Convert datetime → ISO string, pass strings through."""
    if isinstance(val, datetime):
        return val.isoformat()
    return val


# ── helpers ────────────────────────────────────────────────────────────────────

def _since(time_range: str) -> datetime | None:
    """Return the UTC cutoff datetime for the given range, or None for 'all'."""
    now    = datetime.now(timezone.utc)
    deltas = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
    delta  = deltas.get(time_range)
    return (now - delta) if delta else None


def _record_to_dict(rec: dict, visitor_uid: str, visitor_name: str, thumbnail: str | None) -> dict:
    """Flatten a visit_record embedded doc into a response-friendly dict."""
    return {
        "visit_id":         rec.get("visit_id"),
        "visitor_uid":      visitor_uid,
        "visitor_name":     visitor_name,
        "visitor_email":    rec.get("visitor_email"),
        "visitor_phone":    rec.get("visitor_phone"),
        "visitor_thumbnail":thumbnail,
        "purpose":          rec.get("purpose"),
        "status":           rec.get("status"),
        "employee_id":      rec.get("employee_id"),
        "created_at":       _iso(rec.get("created_at")),
        "updated_at":       _iso(rec.get("updated_at")),
        "location_id":      rec.get("location_id"),
        "location_name":    rec.get("location_name"),
        "otp":              rec.get("otp"),
        "require_otp":      rec.get("require_otp", False),
    }


async def _get_thumbnails(db, visitor_uids: list[str]) -> dict[str, str | None]:
    """Fetch thumbnail map {visitor_uid: thumbnail} from visitors collection."""
    if not visitor_uids:
        return {}
    docs = await db.visitors.find(
        {"visitor_uid": {"$in": visitor_uids}},
        {"_id": 0, "visitor_uid": 1, "thumbnail": 1},
    ).to_list(length=500)
    return {d["visitor_uid"]: d.get("thumbnail") for d in docs}


# ── public API ─────────────────────────────────────────────────────────────────

async def get_visits_for_employee(
    employee_id: str,
    status: str | None = None,
    limit: int = 200,
    today_only: bool = False,
    date_str: str | None = None,   # "YYYY-MM-DD"
) -> list:
    """
    Returns flattened visit records for this employee.
    Filters applied inside the visit_records array via aggregation.
    """
    db  = get_db()
    now = datetime.now(timezone.utc)

    # Build date filter for visit_records
    date_filter: dict = {}
    if today_only:
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        date_filter = {"visit_records.created_at": {"$gte": today_start}}
    elif date_str:
        try:
            day      = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            next_day = day + timedelta(days=1)
            date_filter = {"visit_records.created_at": {"$gte": day, "$lt": next_day}}
        except ValueError:
            pass

    status_filter: dict = {}
    if status:
        status_filter = {"visit_records.status": status}

    pipeline = [
        # Pre-filter documents that contain at least one matching record
        {"$match": {"visit_records.employee_id": employee_id, **date_filter, **status_filter}},
        {"$unwind": "$visit_records"},
        # Post-unwind filter (exact match per record)
        {"$match": {
            "visit_records.employee_id": employee_id,
            **({} if not status else {"visit_records.status": status}),
            **({} if not date_filter else {
                k.replace("visit_records.", "visit_records."): v
                for k, v in date_filter.items()
            }),
        }},
        {"$sort": {"visit_records.created_at": -1}},
        {"$limit": limit},
        {"$project": {
            "_id":          0,
            "visitor_uid":  1,
            "visitor_name": 1,
            "visit_records": 1,
        }},
    ]

    # Re-apply the date filter properly after unwind
    pipeline = [
        {"$match": {"visit_records.employee_id": employee_id}},
        {"$unwind": "$visit_records"},
        {"$match": {
            "visit_records.employee_id": employee_id,
            **({} if not status else {"visit_records.status": status}),
        }},
    ]
    if today_only:
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        pipeline.append({"$match": {"visit_records.created_at": {"$gte": today_start}}})
    elif date_str:
        try:
            day      = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            next_day = day + timedelta(days=1)
            pipeline.append({"$match": {"visit_records.created_at": {"$gte": day, "$lt": next_day}}})
        except ValueError:
            pass

    pipeline += [
        {"$sort":  {"visit_records.created_at": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "visitor_uid": 1, "visitor_name": 1, "visit_records": 1}},
    ]

    rows = await db.visits.aggregate(pipeline).to_list(length=limit)

    # Collect thumbnails in one query
    uids       = list({r["visitor_uid"] for r in rows})
    thumbnails = await _get_thumbnails(db, uids)

    # Fetch employee name once
    emp     = await db.employees.find_one({"employee_id": employee_id}, {"name": 1})
    emp_name = emp["name"] if emp else employee_id

    result = []
    for row in rows:
        rec = row["visit_records"]
        flat = _record_to_dict(rec, row["visitor_uid"], row["visitor_name"],
                               thumbnails.get(row["visitor_uid"]))
        flat["employee_name"] = emp_name
        result.append(flat)
    return result


async def get_visit_records_for_visitor(employee_id: str, visitor_uid: str) -> list:
    """All visit records by a specific visitor for this employee."""
    db  = get_db()
    doc = await db.visits.find_one({"visitor_uid": visitor_uid}, {"_id": 0})
    if not doc:
        return []

    thumbnail = None
    profile   = await db.visitors.find_one(
        {"visitor_uid": visitor_uid}, {"_id": 0, "thumbnail": 1}
    )
    if profile:
        thumbnail = profile.get("thumbnail")

    records = [
        r for r in doc.get("visit_records", [])
        if r.get("employee_id") == employee_id
    ]
    records.sort(key=lambda r: r.get("created_at", datetime.min), reverse=True)

    return [
        _record_to_dict(r, visitor_uid, doc.get("visitor_name", ""), thumbnail)
        for r in records
    ]


async def update_visit_status(
    visit_id: str,
    employee_id: str,
    status: str,
    location_id: str | None = None,
    require_otp: bool = False,
) -> dict:
    db  = get_db()
    now = datetime.now(timezone.utc)

    if status == "approved" and not location_id:
        raise HTTPException(
            status_code=400,
            detail="A meeting location must be selected when approving a visit.",
        )

    location = None
    if location_id:
        location = await location_service.get_location(location_id)
        if not location:
            raise HTTPException(status_code=404, detail=f"Location '{location_id}' not found")

    otp = None
    if status == "approved" and require_otp:
        otp = email_service.generate_otp()

    # Build the $set map for the matching array element
    set_map: dict = {
        "visit_records.$.status":     status,
        "visit_records.$.updated_at": now,
    }
    if location:
        set_map["visit_records.$.location_id"]   = location["location_id"]
        set_map["visit_records.$.location_name"] = location["name"]
    if otp:
        set_map["visit_records.$.otp"] = otp
    if status == "approved":
        set_map["visit_records.$.require_otp"] = require_otp

    result = await db.visits.find_one_and_update(
        {
            "visit_records": {
                "$elemMatch": {
                    "visit_id":    visit_id,
                    "employee_id": employee_id,
                }
            }
        },
        {"$set": set_map},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Visit not found or unauthorized")

    # Find the updated record
    updated_rec = next(
        (r for r in result.get("visit_records", []) if r.get("visit_id") == visit_id),
        None,
    )
    if not updated_rec:
        raise HTTPException(status_code=500, detail="Could not locate updated record")

    # Fetch thumbnail
    profile   = await db.visitors.find_one({"visitor_uid": result["visitor_uid"]}, {"thumbnail": 1})
    thumbnail = profile.get("thumbnail") if profile else None

    flat = _record_to_dict(
        updated_rec,
        result["visitor_uid"],
        result.get("visitor_name", ""),
        thumbnail,
    )

    # ── Send emails ───────────────────────────────────────────────────────────
    emp      = await db.employees.find_one({"employee_id": employee_id}, {"name": 1, "email": 1})
    emp_name = emp["name"] if emp else employee_id

    visitor_email = updated_rec.get("visitor_email", "")
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

    flat["employee_name"] = emp_name
    return flat


async def notify_employee_new_visit(
    visitor_uid: str,
    visitor_name: str,
    visitor_phone: str,
    visitor_email: str,
    employee_id: str,
    purpose: str,
    visit_id: str,
) -> None:
    db  = get_db()
    emp = await db.employees.find_one({"employee_id": employee_id}, {"name": 1, "email": 1})
    if not emp or not emp.get("email"):
        return
    await email_service.send_new_visit_notification(
        employee_email=emp["email"],
        employee_name=emp["name"],
        visitor_name=visitor_name,
        visitor_phone=visitor_phone,
        visitor_email=visitor_email,
        purpose=purpose,
        app_url=settings.APP_URL,
    )


async def get_pending_count(employee_id: str) -> int:
    db = get_db()
    pipeline = [
        {"$match":  {"visit_records.employee_id": employee_id, "visit_records.status": "pending"}},
        {"$unwind": "$visit_records"},
        {"$match":  {"visit_records.employee_id": employee_id, "visit_records.status": "pending"}},
        {"$count":  "total"},
    ]
    result = await db.visits.aggregate(pipeline).to_list(length=1)
    return result[0]["total"] if result else 0


async def get_dashboard_stats(employee_id: str, time_range: str = "24h") -> dict:
    db    = get_db()
    since = _since(time_range)

    # Base match: employee_id inside the array
    base = {"visit_records.employee_id": employee_id}
    if since:
        base["visit_records.created_at"] = {"$gte": since}

    pipeline = [
        {"$match":  base},
        {"$unwind": "$visit_records"},
        {"$match": {
            "visit_records.employee_id": employee_id,
            **({} if not since else {"visit_records.created_at": {"$gte": since}}),
        }},
        {"$group": {
            "_id":      None,
            "total":    {"$sum": 1},
            "pending":  {"$sum": {"$cond": [{"$eq": ["$visit_records.status", "pending"]},  1, 0]}},
            "approved": {"$sum": {"$cond": [{"$in":  ["$visit_records.status",
                                                       ["approved","checked_in","checked_out"]]}, 1, 0]}},
            "rejected": {"$sum": {"$cond": [{"$eq": ["$visit_records.status", "rejected"]}, 1, 0]}},
        }},
    ]

    rows = await db.visits.aggregate(pipeline).to_list(length=1)

    # Today count (always absolute)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_pipeline = [
        {"$match":  {"visit_records.employee_id": employee_id,
                     "visit_records.created_at":  {"$gte": today_start}}},
        {"$unwind": "$visit_records"},
        {"$match":  {"visit_records.employee_id": employee_id,
                     "visit_records.created_at":  {"$gte": today_start}}},
        {"$count":  "total"},
    ]
    today_rows = await db.visits.aggregate(today_pipeline).to_list(length=1)

    counts = rows[0] if rows else {"total": 0, "pending": 0, "approved": 0, "rejected": 0}
    return {
        "total":      counts.get("total",    0),
        "pending":    counts.get("pending",  0),
        "approved":   counts.get("approved", 0),
        "rejected":   counts.get("rejected", 0),
        "today":      today_rows[0]["total"] if today_rows else 0,
        "time_range": time_range,
    }


async def get_visits_for_range(employee_id: str, time_range: str = "7d") -> list:
    """Returns flattened visit records for chart rendering."""
    db    = get_db()
    since = _since(time_range)

    pipeline = [
        {"$match": {"visit_records.employee_id": employee_id}},
        {"$unwind": "$visit_records"},
        {"$match": {
            "visit_records.employee_id": employee_id,
            **({} if not since else {"visit_records.created_at": {"$gte": since}}),
        }},
        {"$sort":  {"visit_records.created_at": -1}},
        {"$limit": 2000},
        {"$project": {"_id": 0, "visitor_uid": 1, "visit_records": 1}},
    ]

    rows = await db.visits.aggregate(pipeline).to_list(length=2000)
    return [
        {
            "visit_id":   r["visit_records"]["visit_id"],
            "status":     r["visit_records"]["status"],
            "created_at": _iso(r["visit_records"]["created_at"]),
        }
        for r in rows
    ]


async def search_visitor_visits(employee_id: str, query: str) -> list:
    """Full-text search across visitor name, email, phone for this employee."""
    db    = get_db()
    regex = {"$regex": query, "$options": "i"}

    pipeline = [
        {"$match": {
            "visit_records.employee_id": employee_id,
            "$or": [
                {"visitor_name":              regex},
                {"visit_records.visitor_email": regex},
                {"visit_records.visitor_phone": regex},
            ],
        }},
        {"$unwind": "$visit_records"},
        {"$match": {
            "visit_records.employee_id": employee_id,
            "$or": [
                {"visitor_name":              regex},
                {"visit_records.visitor_email": regex},
                {"visit_records.visitor_phone": regex},
            ],
        }},
        {"$sort":  {"visit_records.created_at": -1}},
        {"$limit": 50},
        {"$project": {"_id": 0, "visitor_uid": 1, "visitor_name": 1, "visit_records": 1}},
    ]

    rows = await db.visits.aggregate(pipeline).to_list(length=50)

    uids       = list({r["visitor_uid"] for r in rows})
    thumbnails = await _get_thumbnails(db, uids)

    emp      = await db.employees.find_one({"employee_id": employee_id}, {"name": 1})
    emp_name = emp["name"] if emp else employee_id

    result = []
    for row in rows:
        flat = _record_to_dict(
            row["visit_records"],
            row["visitor_uid"],
            row.get("visitor_name", ""),
            thumbnails.get(row["visitor_uid"]),
        )
        flat["employee_name"] = emp_name
        result.append(flat)
    return result


async def get_notifications_for_employee(employee_id: str) -> list:
    """
    Today's visit records for this employee, excluding checked_out.
    Used by the approvals / notifications page.
    """
    db          = get_db()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    pipeline = [
        {"$match":  {"visit_records.employee_id": employee_id,
                     "visit_records.created_at":  {"$gte": today_start}}},
        {"$unwind": "$visit_records"},
        {"$match":  {
            "visit_records.employee_id": employee_id,
            "visit_records.created_at":  {"$gte": today_start},
            "visit_records.status":      {"$ne": "checked_out"},
        }},
        {"$sort":  {"visit_records.created_at": -1}},
        {"$limit": 200},
        {"$project": {"_id": 0, "visitor_uid": 1, "visitor_name": 1, "visit_records": 1}},
    ]

    rows = await db.visits.aggregate(pipeline).to_list(length=200)

    uids       = list({r["visitor_uid"] for r in rows})
    thumbnails = await _get_thumbnails(db, uids)

    result = []
    for row in rows:
        flat = _record_to_dict(
            row["visit_records"],
            row["visitor_uid"],
            row.get("visitor_name", ""),
            thumbnails.get(row["visitor_uid"]),
        )
        result.append(flat)
    return result