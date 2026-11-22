from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.db.models import Checkin, Space
from app.schemas.core import CheckinIn, CheckinOut, JobOut, PlanIn, PlanOut, SpaceIn, SpaceOut, SpacePatch, SpaceSummary
from app.services import ai, plans, spaces
from app.services.common import get_or_404

router = APIRouter(prefix="/spaces", tags=["spaces"])


@router.get("", response_model=list[SpaceSummary])
def list_spaces(db: DbSession):
    return spaces.summaries(db)


@router.post("", response_model=SpaceOut, status_code=201)
def create_space(body: SpaceIn, db: DbSession):
    return spaces.create_space(db, body)


@router.patch("/{space_id}", response_model=SpaceOut)
def patch_space(space_id: int, body: SpacePatch, db: DbSession):
    return spaces.patch_space(db, space_id, body)


@router.delete("/{space_id}", status_code=204)
def delete_space(space_id: int, db: DbSession) -> None:
    spaces.delete_space(db, space_id)


@router.get("/{space_id}/plans", response_model=list[PlanOut])
def list_plans(space_id: int, db: DbSession):
    return spaces.plans_for(db, space_id)


@router.post("/{space_id}/plans", response_model=PlanOut, status_code=201)
def create_plan(space_id: int, body: PlanIn, db: DbSession):
    """Starts a make_plan job; GET /api/plans/{id} shows the checklist once it's written."""
    return plans.create_plan(db, space_id, body)


@router.post("/{space_id}/review", response_model=JobOut, status_code=201)
def review(space_id: int, db: DbSession):
    """Ask Claude for a progress check-in from the before and latest photos."""
    get_or_404(db, Space, space_id)
    job = ai.queue(db, "review_progress", space_id)
    db.commit()
    return job


@router.get("/{space_id}/checkins", response_model=list[CheckinOut])
def list_checkins(space_id: int, db: DbSession):
    return list(db.scalars(select(Checkin).where(Checkin.space_id == space_id).order_by(Checkin.created_at.desc())))


@router.post("/{space_id}/checkins", response_model=CheckinOut, status_code=201)
def add_checkin(space_id: int, body: CheckinIn, db: DbSession):
    get_or_404(db, Space, space_id)
    row = Checkin(space_id=space_id, summary=body.summary, percent_done=body.percent_done, source="manual")
    db.add(row)
    db.commit()
    return row
