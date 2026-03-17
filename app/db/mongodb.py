from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DB_NAME]
    print(f"✅ MongoDB connected → {settings.DB_NAME}")

    # Create indexes
    await db.employees.create_index("email", unique=True)
    await db.employees.create_index("employee_id", unique=True)
    await db.visitors.create_index("visitor_uid", unique=True)
    await db.visits.create_index([("visitor_uid", 1), ("created_at", -1)])
    await db.visits.create_index([("employee_id", 1), ("status", 1)])
    print("✅ Indexes ensured")


async def close_db():
    global client
    if client:
        client.close()


def get_db():
    return db
