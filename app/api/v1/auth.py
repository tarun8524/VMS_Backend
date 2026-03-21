from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
from app.services import employee_service, face_service

router = APIRouter()


@router.post("/register", summary="Register new employee (with optional photo + phone)")
async def register(
    name:        str           = Form(...),
    email:       str           = Form(...),
    employee_id: str           = Form(...),
    department:  Optional[str] = Form(None),
    phone:       Optional[str] = Form(None),   # full E.164 e.g. +919876543210
    password:    str           = Form(...),
    photo:       Optional[UploadFile] = File(None),
):
    thumbnail = None
    if photo:
        raw       = await photo.read()
        rgb       = face_service.bytes_to_rgb(raw)
        face      = face_service.extract_face_encoding(rgb)
        thumbnail = face["thumbnail"]

    emp = await employee_service.register_employee({
        "name":        name,
        "email":       email,
        "employee_id": employee_id,
        "department":  department,
        "phone":       phone,
        "password":    password,
        "thumbnail":   thumbnail,
    })
    return emp


@router.post("/login", summary="Employee login")
async def login(email: str = Form(...), password: str = Form(...)):
    return await employee_service.login_employee(email, password)