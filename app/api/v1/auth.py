from fastapi import APIRouter
from app.models.schemas import EmployeeRegister, EmployeeLogin, TokenOut
from app.services import employee_service

router = APIRouter()


@router.post("/register", summary="Register new employee")
async def register(body: EmployeeRegister):
    emp = await employee_service.register_employee(body.model_dump())
    return emp


@router.post("/login", summary="Employee login")
async def login(body: EmployeeLogin):
    return await employee_service.login_employee(body.email, body.password)
