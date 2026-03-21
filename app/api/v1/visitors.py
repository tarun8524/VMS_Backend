from fastapi import APIRouter, UploadFile, File, Form, Depends
from app.services import visitor_service, face_service
from app.core.security import get_current_employee

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTANT: ALL static-path routes MUST be declared before any
# dynamic /{visitor_uid} routes, otherwise FastAPI will match
# "recognize", "verify-identity", "my-visitors" etc. as visitor_uid values.
# ─────────────────────────────────────────────────────────────────────────────


# ── Static routes ─────────────────────────────────────────────────────────────

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


@router.post("/recognize", summary="Recognize visitor by face photo")
async def recognize_visitor(
    photo: UploadFile = File(...),
    limit: int = 5,
):
    raw  = await photo.read()
    rgb  = face_service.bytes_to_rgb(raw)
    face = face_service.extract_face_encoding(rgb)
    return await visitor_service.recognize_visitor(face["encoding"], limit=limit)


@router.post("/verify-identity", summary="Verify returning visitor identity by phone + email")
async def verify_identity(
    visitor_uid: str = Form(...),
    phone:       str = Form(...),
    email:       str = Form(...),
):
    """
    Returns { verified: bool, visitor: {...} | None }
    Used by the returning-visitor flow to confirm identity before allowing
    a visit request or a details update.
    """
    return await visitor_service.verify_visitor_identity(
        visitor_uid=visitor_uid,
        phone=phone,
        email=email,
    )


# ── Dynamic /{visitor_uid} routes — MUST come last ────────────────────────────

@router.get("/{visitor_uid}", summary="Get visitor profile by UID")
async def get_visitor(visitor_uid: str):
    return await visitor_service.get_visitor_by_uid(visitor_uid)


@router.delete("/{visitor_uid}", summary="Delete visitor and all their visit records")
async def delete_visitor(visitor_uid: str):
    await visitor_service.delete_visitor(visitor_uid)
    return {"deleted": visitor_uid}


@router.patch("/{visitor_uid}/details", summary="Update returning visitor name/phone/email")
async def update_visitor_details(
    visitor_uid: str,
    name:  str        = Form(None),
    phone: str        = Form(None),
    email: str        = Form(None),
    photo: UploadFile = File(None),
):
    """
    Allows a verified returning visitor to update their contact details and/or photo.
    Only provided fields are updated.
    """
    new_encoding  = None
    new_thumbnail = None

    if photo:
        raw = await photo.read()
        rgb = face_service.bytes_to_rgb(raw)
        face = face_service.extract_face_encoding(rgb)
        new_encoding  = face["encoding"]
        new_thumbnail = face["thumbnail"]

    return await visitor_service.update_visitor_details(
        visitor_uid=visitor_uid,
        name=name,
        phone=phone,
        email=email,
        encoding=new_encoding,
        thumbnail=new_thumbnail,
    )