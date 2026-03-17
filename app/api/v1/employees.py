from fastapi import APIRouter, Query, Depends
from app.services import employee_service
from app.core.security import get_current_employee

router = APIRouter()


@router.get("/search", summary="Search employees by name or ID")
async def search_employees(q: str = Query(..., min_length=1)):
    return await employee_service.search_employees(q)


@router.get("/", summary="List all employees (for visitor form dropdown)")
async def list_employees():
    return await employee_service.get_all_employees()


@router.get("/me", summary="Current logged-in employee")
async def me(current: dict = Depends(get_current_employee)):
    return current
