"""The Claude job queue. The dashboard shows it; a Claude Code thread works it by hand."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.schemas.core import JobContext, JobOut, JobResultIn
from app.services import ai

router = APIRouter(prefix="/ai/jobs", tags=["ai"])


@router.get("", response_model=list[JobOut])
def list_jobs(db: DbSession, status: str | None = None, limit: int = 100):
    return ai.list_jobs(db, status, min(limit, 500))


@router.post("/claim", response_model=JobContext)
def claim_next(db: DbSession):
    """Take the oldest pending job for a thread and return what to look at."""
    job = ai.claim(db, None, "thread")
    if job is None:
        raise HTTPException(404, "no pending jobs")
    return ai.context_for(db, job.id)


@router.get("/{job_id}/context", response_model=JobContext)
def context(job_id: int, db: DbSession):
    return ai.context_for(db, job_id)


@router.post("/{job_id}/result", response_model=JobOut)
def submit(job_id: int, body: JobResultIn, db: DbSession):
    return ai.submit(db, job_id, body.result)


@router.post("/{job_id}/retry", response_model=JobOut)
def retry(job_id: int, db: DbSession):
    return ai.retry(db, job_id)
