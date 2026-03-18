"""
Location service — manages meeting locations.
Predefined locations (Block A, Block B) are seeded into MongoDB on startup.
"""
from app.db.mongodb import get_db


PREDEFINED_LOCATIONS = [
    {
        "location_id": "block_a",
        "name": "Block A",
        "address": "Block A, Campus",
        "lat": "17.352528",
        "lng": "82.537000",
        # 17°21'09.1"N  → 17 + 21/60 + 09.1/3600 = 17.352528
        # 82°32'13.2"E  → 82 + 32/60 + 13.2/3600 = 82.537000
        "maps_url": "https://www.google.com/maps?q=17.352528,82.537000",
    },
    {
        "location_id": "block_b",
        "name": "Block B",
        "address": "Block B, Campus",
        "lat": "17.357056",
        "lng": "82.538778",
        # 17°21'25.4"N  → 17 + 21/60 + 25.4/3600 = 17.357056
        # 82°32'19.6"E  → 82 + 32/60 + 19.6/3600 = 82.538778
        "maps_url": "https://www.google.com/maps?q=17.357056,82.538778",
    },
]


async def seed_locations() -> None:
    """Upsert predefined locations into MongoDB on startup."""
    db = get_db()
    for loc in PREDEFINED_LOCATIONS:
        await db.locations.update_one(
            {"location_id": loc["location_id"]},
            {"$set": loc},
            upsert=True,
        )
    print(f"✅ {len(PREDEFINED_LOCATIONS)} locations seeded")


async def get_all_locations() -> list:
    db = get_db()
    cursor = db.locations.find({}, {"_id": 0})
    return await cursor.to_list(length=50)


async def get_location(location_id: str) -> dict | None:
    db = get_db()
    return await db.locations.find_one({"location_id": location_id}, {"_id": 0})
