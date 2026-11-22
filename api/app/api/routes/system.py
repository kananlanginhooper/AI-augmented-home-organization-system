from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.core.config import settings
from app.db.models import AiJob, Checkin, Item
from app.schemas.core import CheckinOut, Overview, RuntimeConfig, TaskOut
from app.services import plans, spaces

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config", response_model=RuntimeConfig)
def config() -> RuntimeConfig:
    return RuntimeConfig(
        apiBase="api",
        basePath=settings.ui_base,
        publicUrl=settings.public_url,
        frameParents=settings.frame_ancestor_list,
        login={"enabled": settings.login == "on", "issuer": settings.oidc_issuer, "clientId": settings.oidc_client_id},
        claude={"apiWorker": settings.api_worker_enabled, "model": settings.claude_model},
        gameplan={"enabled": bool(settings.gameplan_api_url), "area": settings.gameplan_area},
    )


@router.get("/overview", response_model=Overview)
def overview(db: DbSession) -> Overview:
    open_decisions = db.scalar(select(func.count(Item.id)).where(Item.confirmed.is_(False))) or 0
    pending = db.scalar(select(func.count(AiJob.id)).where(AiJob.status.in_(["pending", "running"]))) or 0
    checkins = db.scalars(select(Checkin).order_by(Checkin.created_at.desc()).limit(5))
    return Overview(
        spaces=spaces.summaries(db),
        progress=spaces.progress(db, None),
        next_tasks=[TaskOut.model_validate(t) for t in plans.next_tasks(db)],
        open_decisions=open_decisions,
        pending_jobs=pending,
        recent_checkins=[CheckinOut.model_validate(c) for c in checkins],
    )
