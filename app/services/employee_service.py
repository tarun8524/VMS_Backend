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
        "name": data["name"],
        "email": data["email"],
        "employee_id": data["employee_id"],
        "department": data.get("department"),
        "password_hash": hash_password(data["password"]),
    }
    result = await db.employees.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "name": doc["name"],
        "email": doc["email"],
        "employee_id": doc["employee_id"],
        "department": doc["department"],
    }


async def login_employee(email: str, password: str) -> dict:
    db = get_db()
    emp = await db.employees.find_one({"email": email})
    if not emp or not verify_password(password, emp["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": str(emp["_id"]),
        "email": emp["email"],
        "name": emp["name"],
        "employee_id": emp["employee_id"],
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "employee": {
            "id": str(emp["_id"]),
            "name": emp["name"],
            "email": emp["email"],
            "employee_id": emp["employee_id"],
            "department": emp.get("department"),
        },
    }


async def search_employees(query: str, limit: int = 10) -> list:
    db = get_db()
    regex = {"$regex": query, "$options": "i"}
    cursor = db.employees.find(
        {"$or": [{"name": regex}, {"employee_id": regex}]},
        {"_id": 0, "name": 1, "employee_id": 1, "department": 1}
    ).limit(limit)
    return await cursor.to_list(length=limit)


async def get_all_employees(limit: int = 200) -> list:
    db = get_db()
    cursor = db.employees.find({}, {"_id": 0, "name": 1, "employee_id": 1, "department": 1}).limit(limit)
    return await cursor.to_list(length=limit)
