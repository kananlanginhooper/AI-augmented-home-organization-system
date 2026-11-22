"""The feed other tools read (new photos, and which tools have looked at them) and the results they post back."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Photo, PhotoEvaluation, now
from app.schemas.core import EvaluationIn, PhotoForTools
from app.services import spaces
from app.services.common import get_or_404


def feed(db: Session, since: datetime | None, missing_tool: str | None, limit: int) -> list[PhotoForTools]:
    """Photos in upload order. missing_tool = only photos that tool hasn't evaluated yet."""
    stmt = select(Photo).order_by(Photo.uploaded_at, Photo.id).limit(limit)
    if since:
        stmt = stmt.where(Photo.uploaded_at > since)
    if missing_tool:
        done = select(PhotoEvaluation.photo_id).where(PhotoEvaluation.tool == missing_tool)
        stmt = stmt.where(Photo.id.not_in(done))
    photos = list(db.scalars(stmt))
    tools: dict[int, list[str]] = {}
    if photos:
        rows = db.execute(
            select(PhotoEvaluation.photo_id, PhotoEvaluation.tool).where(PhotoEvaluation.photo_id.in_([p.id for p in photos]))
        )
        for photo_id, tool in rows:
            tools.setdefault(photo_id, []).append(tool)
    names = spaces.paths(db)
    return [
        PhotoForTools(
            id=p.id,
            space_path=names.get(p.space_id) if p.space_id else None,
            phase=p.phase,
            uploaded_at=p.uploaded_at,
            file_url=f"api/photos/{p.id}/file",
            sha256=p.sha256,
            analyzed=p.analysis is not None,
            tools_done=sorted(tools.get(p.id, [])),
        )
        for p in photos
    ]


def list_for_photo(db: Session, photo_id: int) -> list[PhotoEvaluation]:
    get_or_404(db, Photo, photo_id)
    return list(db.scalars(select(PhotoEvaluation).where(PhotoEvaluation.photo_id == photo_id).order_by(PhotoEvaluation.tool)))


def save(db: Session, photo_id: int, body: EvaluationIn) -> PhotoEvaluation:
    get_or_404(db, Photo, photo_id)
    row = db.scalar(select(PhotoEvaluation).where(PhotoEvaluation.photo_id == photo_id, PhotoEvaluation.tool == body.tool))
    if row is None:
        row = PhotoEvaluation(photo_id=photo_id, tool=body.tool)
        db.add(row)
    row.version = body.version
    row.result = body.result
    row.created_at = now()
    db.commit()
    return row
