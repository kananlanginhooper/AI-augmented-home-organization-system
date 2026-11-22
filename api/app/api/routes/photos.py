from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import DbSession
from app.db.models import Photo
from app.schemas.core import EvaluationIn, EvaluationOut, JobOut, PhotoForTools, PhotoOut, PhotoPatch, UploadResult
from app.services import ai, evaluations, spaces
from app.services import photos as service
from app.services.common import get_or_404

router = APIRouter(prefix="/photos", tags=["photos"])

MAX_UPLOAD_BYTES = 40 * 1024 * 1024


@router.get("", response_model=list[PhotoOut])
def list_photos(db: DbSession, space_id: int | None = None, unassigned: bool = False):
    ids = spaces.subtree_ids(db, space_id) if space_id is not None else None
    return service.list_photos(db, ids, unassigned)


@router.post("", response_model=UploadResult, status_code=201)
async def upload(
    db: DbSession,
    file: UploadFile = File(...),
    space_id: int | None = Form(None),
    space: str | None = Form(None),  # a name or "Room/Zone" path; created if missing
    phase: Literal["before", "progress", "after", "reference"] = Form("before"),
    source: Literal["dashboard", "thread", "folder"] = Form("dashboard"),
    caption: str | None = Form(None),
    analyze: bool = Form(True),
):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "photo is over 40 MB")
    if space_id is None and space:
        space_id = spaces.find_or_create(db, space).id
    photo, duplicate = service.store(db, data, file.filename, space_id, phase, source, caption)
    if not duplicate and analyze:
        ai.queue(db, "analyze_photo", photo.id)
        db.commit()
    return UploadResult(photo=PhotoOut.model_validate(photo), duplicate=duplicate)


@router.get("/feed", response_model=list[PhotoForTools])
def feed(db: DbSession, since: datetime | None = None, missing_tool: str | None = None, limit: int = 200):
    """For other tools: photos in upload order. missing_tool=<name> lists only photos that tool hasn't evaluated."""
    return evaluations.feed(db, since, missing_tool, min(limit, 1000))


@router.get("/{photo_id}", response_model=PhotoOut)
def get_photo(photo_id: int, db: DbSession):
    return get_or_404(db, Photo, photo_id)


@router.get("/{photo_id}/file", include_in_schema=False)
def get_file(photo_id: int, db: DbSession, size: Literal["full", "thumb", "claude"] = "full"):
    path = service.file_path(get_or_404(db, Photo, photo_id), size)
    if not path.is_file():
        raise HTTPException(404, "file missing on disk")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.patch("/{photo_id}", response_model=PhotoOut)
def patch_photo(photo_id: int, body: PhotoPatch, db: DbSession):
    return service.patch_photo(db, photo_id, body)


@router.delete("/{photo_id}", status_code=204)
def delete_photo(photo_id: int, db: DbSession) -> None:
    service.delete_photo(db, photo_id)


@router.post("/{photo_id}/analyze", response_model=JobOut, status_code=201)
def analyze(photo_id: int, db: DbSession):
    get_or_404(db, Photo, photo_id)
    job = ai.queue(db, "analyze_photo", photo_id)
    db.commit()
    return job


@router.get("/{photo_id}/evaluations", response_model=list[EvaluationOut])
def list_evaluations(photo_id: int, db: DbSession):
    return evaluations.list_for_photo(db, photo_id)


@router.put("/{photo_id}/evaluations", response_model=EvaluationOut)
def save_evaluation(photo_id: int, body: EvaluationIn, db: DbSession):
    """Another tool's result for this photo; one per tool, a re-run replaces it."""
    return evaluations.save(db, photo_id, body)
