from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
from app.services import visitor_service, face_service

router = APIRouter()


@router.post("/", summary="Register visitor with face")
async def register_visitor(
    name:                 str        = Form(...),
    phone:                str        = Form(...),
    email:                str        = Form(...),
    employee_to_visit_id: str        = Form(...),
    purpose:              str        = Form(""),
    photo:                UploadFile = File(...),
):
    raw = await photo.read()
    rgb = face_service.bytes_to_rgb(raw)
    face = face_service.extract_face_encoding(rgb)

    visitor = await visitor_service.register_visitor(
        name=name, phone=phone, email=email,
        employee_to_visit_id=employee_to_visit_id,
        purpose=purpose,
        encoding=face["encoding"],
        thumbnail=face["thumbnail"],
    )
    visitor.pop("_id", None)
    return visitor


@router.get("/", summary="List all visitors")
async def list_visitors(limit: int = 100):
    visitors = await visitor_service.get_all_visitors(limit)
    return {"visitors": visitors, "total": len(visitors)}


@router.get("/{visitor_uid}", summary="Get visitor by UID")
async def get_visitor(visitor_uid: str):
    return await visitor_service.get_visitor_by_uid(visitor_uid)


@router.delete("/{visitor_uid}", summary="Delete visitor")
async def delete_visitor(visitor_uid: str):
    await visitor_service.delete_visitor(visitor_uid)
    return {"deleted": visitor_uid}


@router.post("/recognize", summary="Recognize visitor by face photo")
async def recognize_visitor(
    photo: UploadFile = File(...),
    limit: int = 5,
):
    raw = await photo.read()
    rgb = face_service.bytes_to_rgb(raw)
    face = face_service.extract_face_encoding(rgb)
    return await visitor_service.recognize_visitor(face["encoding"], limit=limit)
