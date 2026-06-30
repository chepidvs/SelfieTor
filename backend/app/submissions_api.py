import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from PIL import Image

from .config import SUBMISSIONS_DIR
from .database import get_conn
from .auth import require_login

router = APIRouter(prefix="/api", tags=["submissions"])

MAX_DIMENSION = 1920
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _resize_and_save_jpg(dest_path: Path, src_path: Path):
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        longest = max(w, h)
        if longest > MAX_DIMENSION:
            ratio = MAX_DIMENSION / longest
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        img.save(dest_path, "JPEG", quality=88, optimize=True)


@router.post("/submissions")
async def submit_photo(
    file: UploadFile = File(...),
    template_id: str = Form(None),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Format harus JPG, PNG, atau WEBP")

    submission_id = str(uuid.uuid4())
    tmp_path = SUBMISSIONS_DIR / f"tmp_{submission_id}"
    final_filename = f"{submission_id}.jpg"
    final_path = SUBMISSIONS_DIR / final_filename

    contents = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(contents)

    try:
        _resize_and_save_jpg(final_path, tmp_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Gagal proses gambar, pastikan file valid")
    finally:
        tmp_path.unlink(missing_ok=True)

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO submissions (id, template_id, filename, submitted_at) VALUES (?, ?, ?, ?)",
            (submission_id, template_id, final_filename, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    return {"id": submission_id, "url": f"/static/submissions/{final_filename}"}


@router.get("/admin/submissions")
def list_submissions(_: bool = Depends(require_login)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, template_id, filename, submitted_at FROM submissions ORDER BY submitted_at DESC"
        ).fetchall()
    return [
        {
            "id": r["id"],
            "template_id": r["template_id"],
            "submitted_at": r["submitted_at"],
            "url": f"/static/submissions/{r['filename']}",
        }
        for r in rows
    ]
