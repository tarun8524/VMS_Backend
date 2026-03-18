from fastapi import APIRouter
from app.services import location_service

router = APIRouter()


@router.get("/", summary="List all meeting locations")
async def list_locations():
    return await location_service.get_all_locations()
