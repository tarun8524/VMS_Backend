from fastapi import APIRouter, Depends, Query
from app.services import visit_service
from app.models.schemas import VisitStatusUpdate
from app.core.security import get_current_employee

router = APIRouter()


@router.get("/my", summary="Get visits for the logged-in employee")
async def my_visits(
    status: str = Query(None),
    limit: int = 50,
    today_only: bool = Query(False),
    current: dict = Depends(get_current_employee),
):
    return await visit_service.get_visits_for_employee(
        current["employee_id"], status=status, limit=limit, today_only=today_only
    )


@router.get("/my/stats", summary="Dashboard stats for logged-in employee")
async def my_stats(current: dict = Depends(get_current_employee)):
    return await visit_service.get_dashboard_stats(current["employee_id"])


@router.get("/my/pending-count", summary="Pending visit count (for notification badge)")
async def pending_count(current: dict = Depends(get_current_employee)):
    count = await visit_service.get_pending_count(current["employee_id"])
    return {"count": count}


@router.get("/my/search", summary="Search visitor visits")
async def search_visits(
    q: str = Query(...),
    current: dict = Depends(get_current_employee),
):
    return await visit_service.search_visitor_visits(current["employee_id"], q)


@router.patch("/{visit_id}/status", summary="Approve / reject / update visit status")
async def update_status(
    visit_id: str,
    body: VisitStatusUpdate,
    current: dict = Depends(get_current_employee),
):
    return await visit_service.update_visit_status(
        visit_id=visit_id,
        employee_id=current["employee_id"],
        status=body.status,
        location_id=body.location_id,
        require_otp=body.require_otp,
    )


@router.get("/all", summary="Admin: all visits")
async def all_visits(limit: int = 100):
    return await visit_service.get_all_visits(limit)