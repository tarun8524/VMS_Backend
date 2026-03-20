from fastapi import APIRouter, Depends, Query
from app.services import visit_service
from app.models.schemas import VisitStatusUpdate
from app.core.security import get_current_employee

router = APIRouter()


@router.get("/my", summary="Visit records for logged-in employee (date or today_only)")
async def my_visits(
    status:     str  = Query(None),
    limit:      int  = 200,
    today_only: bool = Query(False),
    date:       str  = Query(None, description="YYYY-MM-DD — filter to a specific day"),
    current:    dict = Depends(get_current_employee),
):
    return await visit_service.get_visits_for_employee(
        current["employee_id"],
        status=status,
        limit=limit,
        today_only=today_only,
        date_str=date,
    )


@router.get("/my/notifications", summary="Today's visits for approvals page (excl. checked_out)")
async def my_notifications(current: dict = Depends(get_current_employee)):
    return await visit_service.get_notifications_for_employee(current["employee_id"])


@router.get("/my/stats", summary="Dashboard stats — 24h | 7d | 30d | all")
async def my_stats(
    range:   str  = Query("24h"),
    current: dict = Depends(get_current_employee),
):
    return await visit_service.get_dashboard_stats(current["employee_id"], time_range=range)


@router.get("/my/chart-data", summary="Lightweight visit list for chart rendering")
async def chart_data(
    range:   str  = Query("7d"),
    current: dict = Depends(get_current_employee),
):
    return await visit_service.get_visits_for_range(current["employee_id"], time_range=range)


@router.get("/my/pending-count", summary="Pending visit count for notification badge")
async def pending_count(current: dict = Depends(get_current_employee)):
    count = await visit_service.get_pending_count(current["employee_id"])
    return {"count": count}


@router.get("/my/search", summary="Search visits by visitor name / email / phone")
async def search_visits(
    q:       str  = Query(...),
    current: dict = Depends(get_current_employee),
):
    return await visit_service.search_visitor_visits(current["employee_id"], q)


@router.get("/my/visitor/{visitor_uid}", summary="All visit records by one visitor for this employee")
async def visitor_records(
    visitor_uid: str,
    current:     dict = Depends(get_current_employee),
):
    return await visit_service.get_visit_records_for_visitor(
        current["employee_id"], visitor_uid
    )


@router.patch("/{visit_id}/status", summary="Approve / reject / check-in / check-out")
async def update_status(
    visit_id: str,
    body:     VisitStatusUpdate,
    current:  dict = Depends(get_current_employee),
):
    return await visit_service.update_visit_status(
        visit_id=visit_id,
        employee_id=current["employee_id"],
        status=body.status,
        location_id=body.location_id,
        require_otp=body.require_otp,
    )