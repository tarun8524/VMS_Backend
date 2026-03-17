import base64
import numpy as np
from io import BytesIO
from PIL import Image
import face_recognition
from fastapi import HTTPException


def bytes_to_rgb(image_bytes: bytes) -> np.ndarray:
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    if max(w, h) > 1024:
        scale = 1024 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)))
    return np.array(img)


def extract_face_encoding(rgb: np.ndarray) -> dict:
    """
    Detect face, generate 128-dim dlib embedding.
    Returns encoding (list of floats) + base64 thumbnail.
    Raises HTTP 400 if no face detected.
    """
    locations = face_recognition.face_locations(
        rgb, number_of_times_to_upsample=2, model="hog"
    )
    if not locations:
        raise HTTPException(
            status_code=400,
            detail="No face detected. Please use a clear, well-lit, front-facing photo.",
        )

    best = max(locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))

    encodings = face_recognition.face_encodings(
        rgb,
        known_face_locations=[best],
        num_jitters=5,
        model="large",
    )
    if not encodings:
        raise HTTPException(status_code=400, detail="Could not encode face. Try another photo.")

    encoding = encodings[0]

    # Crop thumbnail
    top, right, bottom, left = best
    h, w = rgb.shape[:2]
    pad = int((bottom - top) * 0.4)
    t, l, b, r = max(0, top - pad), max(0, left - pad), min(h, bottom + pad), min(w, right + pad)
    face_img = Image.fromarray(rgb[t:b, l:r]).resize((220, 220))
    buf = BytesIO()
    face_img.save(buf, format="JPEG", quality=88)
    thumbnail_b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "encoding": encoding.tolist(),
        "thumbnail": thumbnail_b64,
    }
