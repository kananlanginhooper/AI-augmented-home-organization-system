"""Photo files: stored once per content hash, phone formats (HEIC) converted to JPEG,
EXIF rotation applied, a thumbnail and a Claude-sized copy made at upload."""

from __future__ import annotations

import hashlib
import io
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image, ImageOps
from pillow_heif import register_heif_opener
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Photo
from app.schemas.core import PhotoPatch
from app.services.common import InvalidRequestError, apply_patch, get_or_404

register_heif_opener()

THUMB_EDGE = 480
CLAUDE_EDGE = 1568  # Claude's vision works at up to about this long edge; bigger only costs tokens
SIZES = {"full": None, "thumb": THUMB_EDGE, "claude": CLAUDE_EDGE}


def _dir(size: str) -> Path:
    path = settings.photo_dir if size == "full" else settings.photo_dir / size
    path.mkdir(parents=True, exist_ok=True)
    return path


def file_path(photo: Photo, size: str = "full") -> Path:
    return _dir(size) / photo.filename


def _taken_at(img: Image.Image) -> datetime | None:
    exif = img.getexif()
    raw = exif.get_ifd(ExifTags.IFD.Exif).get(ExifTags.Base.DateTimeOriginal) or exif.get(ExifTags.Base.DateTime)
    try:
        return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S") if raw else None
    except ValueError:
        return None


def store(
    db: Session,
    data: bytes,
    original_name: str | None,
    space_id: int | None,
    phase: str,
    source: str,
    caption: str | None = None,
) -> tuple[Photo, bool]:
    """Save an upload. Returns (photo, duplicate): the same bytes uploaded twice are one photo."""
    sha = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(Photo).where(Photo.sha256 == sha))
    if existing:
        return existing, True
    try:
        img = Image.open(io.BytesIO(data))
        taken = _taken_at(img)
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception as e:  # noqa: BLE001  (Pillow raises many types for bad files)
        raise InvalidRequestError(f"not an image Pillow can read: {e}") from e

    name = f"{sha[:24]}.jpg"
    for size, edge in SIZES.items():
        copy = img.copy()
        if edge:
            copy.thumbnail((edge, edge))
        copy.save(_dir(size) / name, "JPEG", quality=88 if size == "full" else 82)

    photo = Photo(
        sha256=sha,
        filename=name,
        original_name=original_name,
        width=img.width,
        height=img.height,
        taken_at=taken,
        space_id=space_id,
        phase=phase,
        source=source,
        caption=caption,
    )
    db.add(photo)
    db.commit()
    return photo, False


def list_photos(db: Session, space_ids: set[int] | None = None, unassigned: bool = False) -> list[Photo]:
    stmt = select(Photo).order_by(Photo.uploaded_at.desc())
    if unassigned:
        stmt = stmt.where(Photo.space_id.is_(None))
    elif space_ids is not None:
        stmt = stmt.where(Photo.space_id.in_(space_ids))
    return list(db.scalars(stmt))


def patch_photo(db: Session, photo_id: int, body: PhotoPatch) -> Photo:
    photo = get_or_404(db, Photo, photo_id)
    apply_patch(photo, body.model_dump(exclude_unset=True))
    db.commit()
    return photo


def delete_photo(db: Session, photo_id: int) -> None:
    photo = get_or_404(db, Photo, photo_id)
    for size in SIZES:
        file_path(photo, size).unlink(missing_ok=True)
    db.delete(photo)
    db.commit()
