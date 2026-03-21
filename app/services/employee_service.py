from fastapi import HTTPException
from app.db.mongodb import get_db
from app.core.security import hash_password, verify_password, create_access_token


async def register_employee(data: dict) -> dict:
    db = get_db()
    existing = await db.employees.find_one({"email": data["email"]})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_id = await db.employees.find_one({"employee_id": data["employee_id"]})
    if existing_id:
        raise HTTPException(status_code=400, detail="Employee ID already taken")

    doc = {
        "name":          data["name"],
        "email":         data["email"],
        "employee_id":   data["employee_id"],
        "department":    data.get("department"),
        "phone":         data.get("phone"),       # E.164 string or None
        "password_hash": hash_password(data["password"]),
        "thumbnail":     data.get("thumbnail"),   # base64 JPEG or None
    }
    result = await db.employees.insert_one(doc)
    return _to_out(doc, str(result.inserted_id))


async def login_employee(email: str, password: str) -> dict:
    db = get_db()
    emp = await db.employees.find_one({"email": email})
    if not emp or not verify_password(password, emp["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub":         str(emp["_id"]),
        "email":       emp["email"],
        "name":        emp["name"],
        "employee_id": emp["employee_id"],
    })
    return {
        "access_token": token,
        "token_type":   "bearer",
        "employee":     _to_out(emp, str(emp["_id"])),
    }


async def get_employee_by_id(employee_id: str) -> dict:
    db  = get_db()
    emp = await db.employees.find_one({"employee_id": employee_id})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return _to_out(emp, str(emp["_id"]))


async def update_employee_photo(employee_id: str, thumbnail: str) -> dict:
    db     = get_db()
    result = await db.employees.find_one_and_update(
        {"employee_id": employee_id},
        {"$set": {"thumbnail": thumbnail}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Employee not found")
    return _to_out(result, str(result["_id"]))


async def update_employee_phone(employee_id: str, phone: str) -> dict:
    db     = get_db()
    result = await db.employees.find_one_and_update(
        {"employee_id": employee_id},
        {"$set": {"phone": phone}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Employee not found")
    return _to_out(result, str(result["_id"]))


async def search_employees(query: str, limit: int = 10) -> list:
    db    = get_db()
    regex = {"$regex": query, "$options": "i"}
    cursor = db.employees.find(
        {"$or": [{"name": regex}, {"employee_id": regex}]},
        {"_id": 1, "name": 1, "employee_id": 1, "department": 1, "phone": 1, "thumbnail": 1}
    ).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_to_out(d, str(d["_id"])) for d in docs]


async def get_all_employees(limit: int = 200) -> list:
    db     = get_db()
    cursor = db.employees.find(
        {},
        {"_id": 1, "name": 1, "employee_id": 1, "department": 1, "phone": 1, "thumbnail": 1}
    ).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_to_out(d, str(d["_id"])) for d in docs]


# ── Internal helper ───────────────────────────────────────────────────────────
def _to_out(doc: dict, mongo_id: str) -> dict:
    return {
        "id":          mongo_id,
        "name":        doc.get("name", ""),
        "email":       doc.get("email", ""),
        "employee_id": doc.get("employee_id", ""),
        "department":  doc.get("department"),
        "phone":       doc.get("phone"),
        "thumbnail":   doc.get("thumbnail"),
    }