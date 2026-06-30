import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from PIL import Image

from .config import TEMPLATES_DIR
from .database import get_conn
from .auth import require_login

router = APIRouter(prefix="/api", tags=["templates"])

MAX_TEMPLATES = 5
MAX_DIMENSION = 1920  # px, sisi terpanjang
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _resize_and_save_jpg(dest_path: Path, src_path: Path):
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        longest = max(w, h)
        if longest > MAX_DIMENSION:
            ratio = MAX_DIMENSION / longest
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        img.save(dest_path, "JPEG", quality=85, optimize=True)


@router.get("/templates")
def list_templates_public():
    """Dipanggil visitor app — cuma template aktif."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, filename FROM templates WHERE active = 1 ORDER BY created_at ASC"
        ).fetchall()
    return [
        {"id": r["id"], "name": r["name"], "url": f"/static/templates/{r['filename']}"}
        for r in rows
    ]


@router.get("/admin/templates")
def list_templates_admin(_: bool = Depends(require_login)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, filename, active, created_at FROM templates ORDER BY created_at ASC"
        ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "active": bool(r["active"]),
            "created_at": r["created_at"],
            "url": f"/static/templates/{r['filename']}",
        }
        for r in rows
    ]


@router.post("/admin/templates")
async def upload_template(
    name: str = Form(...),
    file: UploadFile = File(...),
    _: bool = Depends(require_login),
):
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM templates WHERE active = 1"
        ).fetchone()["c"]
    if count >= MAX_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Maksimal {MAX_TEMPLATES} template aktif")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Format harus JPG, PNG, atau WEBP")

    template_id = str(uuid.uuid4())
    tmp_path = TEMPLATES_DIR / f"tmp_{template_id}"
    final_filename = f"{template_id}.jpg"
    final_path = TEMPLATES_DIR / final_filename

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
            "INSERT INTO templates (id, name, filename, active, created_at) VALUES (?, ?, ?, 1, ?)",
            (template_id, name, final_filename, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    return {"id": template_id, "name": name, "url": f"/static/templates/{final_filename}"}


@router.delete("/admin/templates/{template_id}")
def delete_template(template_id: str, _: bool = Depends(require_login)):
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM templates WHERE id = ?", (template_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Template gak ketemu")
        conn.execute("UPDATE templates SET active = 0 WHERE id = ?", (template_id,))
        conn.commit()
    return {"status": "ok"}
