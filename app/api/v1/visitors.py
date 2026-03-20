from fastapi import APIRouter, UploadFile, File, Form, Depends
from app.services import visitor_service, face_service
from app.core.security import get_current_employee

router = APIRouter()


@router.post("/", summary="Register visitor (deduplicates by email / phone)")
async def register_visitor(
    name:                 str        = Form(...),
    phone:                str        = Form(...),
    email:                str        = Form(...),
    employee_to_visit_id: str        = Form(...),
    purpose:              str        = Form(""),
    photo:                UploadFile = File(...),
):
    raw  = await photo.read()
    rgb  = face_service.bytes_to_rgb(raw)
    face = face_service.extract_face_encoding(rgb)

    return await visitor_service.register_visitor(
        name=name, phone=phone, email=email,
        employee_to_visit_id=employee_to_visit_id,
        purpose=purpose,
        encoding=face["encoding"],
        thumbnail=face["thumbnail"],
    )


@router.get("/", summary="List all visitors (profiles only, no visit data)")
async def list_visitors(limit: int = 100):
    visitors = await visitor_service.get_all_visitors(limit)
    return {"visitors": visitors, "total": len(visitors)}


@router.get("/my-visitors", summary="Visitor directory for this employee with visit stats")
async def my_visitors(current: dict = Depends(get_current_employee)):
    return await visitor_service.get_visitors_for_employee(current["employee_id"])


@router.get("/{visitor_uid}", summary="Get visitor profile by UID")
async def get_visitor(visitor_uid: str):
    return await visitor_service.get_visitor_by_uid(visitor_uid)


@router.delete("/{visitor_uid}", summary="Delete visitor and all their visit records")
async def delete_visitor(visitor_uid: str):
    await visitor_service.delete_visitor(visitor_uid)
    return {"deleted": visitor_uid}


@router.post("/recognize", summary="Recognize visitor by face photo")
async def recognize_visitor(
    photo: UploadFile = File(...),
    limit: int = 5,
):
    raw  = await photo.read()
    rgb  = face_service.bytes_to_rgb(raw)
    face = face_service.extract_face_encoding(rgb)
    return await visitor_service.recognize_visitor(face["encoding"], limit=limit)