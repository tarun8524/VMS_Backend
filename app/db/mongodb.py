from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DB_NAME]
    print(f"✅ MongoDB connected → {settings.DB_NAME}")

    # ── visitors collection ───────────────────────────────────────────────────
    # Pure profile docs: visitor_uid, name, email, phone, thumbnail, created_at, updated_at
    await db.visitors.create_index("visitor_uid", unique=True)
    await db.visitors.create_index("email",       unique=True)   # no duplicate emails
    await db.visitors.create_index("phone",       unique=True)   # no duplicate phones

    # ── visits collection ─────────────────────────────────────────────────────
    # One document per visitor_uid.
    # visit_records[] is an embedded array — each element has visit_id, employee_id, status, created_at …
    await db.visits.create_index("visitor_uid", unique=True)

    # Allows fast lookup "all visits for employee X"
    await db.visits.create_index("visit_records.employee_id")

    # Allows fast lookup "pending visits for employee X"
    await db.visits.create_index([
        ("visit_records.employee_id", 1),
        ("visit_records.status",      1),
    ])

    # Allows fast lookup by visit_id (used in status-update patch)
    await db.visits.create_index("visit_records.visit_id")

    # ── employees collection ──────────────────────────────────────────────────
    await db.employees.create_index("email",       unique=True)
    await db.employees.create_index("employee_id", unique=True)

    print("✅ Indexes ensured")


async def close_db():
    global client
    if client:
        client.close()


def get_db():
    return db