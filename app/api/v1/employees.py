from fastapi import APIRouter, Query, Depends, UploadFile, File, Form
from typing import Optional
from app.services import employee_service, face_service
from app.core.security import get_current_employee

router = APIRouter()


@router.get("/search", summary="Search employees by name or ID")
async def search_employees(q: str = Query(..., min_length=1)):
    return await employee_service.search_employees(q)


@router.get("/", summary="List all employees")
async def list_employees():
    return await employee_service.get_all_employees()


@router.get("/me", summary="Current logged-in employee (with thumbnail + phone)")
async def me(current: dict = Depends(get_current_employee)):
    return await employee_service.get_employee_by_id(current["employee_id"])


@router.patch("/me/photo", summary="Upload or update employee profile photo")
async def upload_photo(
    photo:   UploadFile = File(...),
    current: dict       = Depends(get_current_employee),
):
    raw       = await photo.read()
    rgb       = face_service.bytes_to_rgb(raw)
    face      = face_service.extract_face_encoding(rgb)
    thumbnail = face["thumbnail"]
    return await employee_service.update_employee_photo(current["employee_id"], thumbnail)


@router.patch("/me/phone", summary="Update employee phone number")
async def update_phone(
    phone:   str  = Form(...),
    current: dict = Depends(get_current_employee),
):
    """Accept full E.164 phone string e.g. +919876543210"""
    return await employee_service.update_employee_phone(current["employee_id"], phone)