"""Plans (a goal for a space) and their checklists, plus the hand-off to Game Plan."""

from __future__ import annotations

from datetime import date, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AiJob, Plan, Space, Task, now
from app.schemas.core import PlanDetail, PlanIn, PlanOut, SendResult, SendToGamePlanIn, TaskIn, TaskOut, TaskPatch
from app.services.common import InvalidRequestError, apply_patch, get_or_404


def create_plan(db: Session, space_id: int, body: PlanIn) -> Plan:
    """A new plan starts as 'planning' with a make_plan job; Claude's answer fills in the checklist."""
    from app.services import ai

    space = get_or_404(db, Space, space_id)
    plan = Plan(space_id=space.id, **body.model_dump())
    db.add(plan)
    db.flush()
    if not space.goal:
        space.goal = body.goal
    ai.queue(db, "make_plan", plan.id)
    db.commit()
    return plan


def detail(db: Session, plan_id: int) -> PlanDetail:
    plan = get_or_404(db, Plan, plan_id)
    tasks = list(db.scalars(select(Task).where(Task.plan_id == plan_id).order_by(Task.sort, Task.id)))
    job = db.scalar(select(AiJob).where(AiJob.kind == "make_plan", AiJob.target_id == plan_id).order_by(AiJob.id.desc()).limit(1))
    return PlanDetail(
        **PlanOut.model_validate(plan).model_dump(),
        tasks=[TaskOut.model_validate(t) for t in tasks],
        job_status=job.status if job else None,
    )


def set_status(db: Session, plan_id: int, status: str) -> Plan:
    plan = get_or_404(db, Plan, plan_id)
    plan.status = status
    db.commit()
    return plan


def add_task(db: Session, plan_id: int, body: TaskIn) -> Task:
    plan = get_or_404(db, Plan, plan_id)
    last = db.scalar(select(Task.sort).where(Task.plan_id == plan_id).order_by(Task.sort.desc()).limit(1)) or 0
    task = Task(plan_id=plan.id, space_id=plan.space_id, source="manual", sort=last + 1, **body.model_dump())
    db.add(task)
    db.commit()
    return task


def patch_task(db: Session, task_id: int, body: TaskPatch) -> Task:
    task = get_or_404(db, Task, task_id)
    changes = body.model_dump(exclude_unset=True)
    if "status" in changes:
        task.done_at = now() if changes["status"] == "done" else None
    apply_patch(task, changes)
    db.commit()
    return task


def delete_task(db: Session, task_id: int) -> None:
    db.delete(get_or_404(db, Task, task_id))
    db.commit()


def next_tasks(db: Session, limit: int = 8) -> list[Task]:
    """Open steps whose dependencies are all done, most important first."""
    open_tasks = list(
        db.scalars(
            select(Task)
            .join(Plan, Plan.id == Task.plan_id)
            .where(Task.status.in_(["todo", "doing"]), Plan.status.in_(["planning", "active"]))
            .order_by(Task.status.desc(), Task.priority, Task.plan_id, Task.sort)
        )
    )
    done = set(db.scalars(select(Task.id).where(Task.status.in_(["done", "skipped"]))))
    ready = [t for t in open_tasks if all(d in done for d in (t.depends_on or []))]
    return ready[:limit]


# --- Game Plan ---
def _gameplan() -> httpx.Client:
    if not settings.gameplan_api_url:
        raise InvalidRequestError("Game Plan isn't configured (GAMEPLAN_API_URL)")
    headers = {"Authorization": f"Bearer {settings.gameplan_api_token}"} if settings.gameplan_api_token else {}
    return httpx.Client(base_url=settings.gameplan_api_url.rstrip("/"), headers=headers, timeout=15)


def send_to_gameplan(db: Session, body: SendToGamePlanIn) -> SendResult:
    """Create one Game Plan task per step, filling days in order up to per_day_minutes each."""
    tasks = [get_or_404(db, Task, tid) for tid in body.task_ids]
    tasks.sort(key=lambda t: (t.plan_id, t.sort, t.id))
    try:
        day = date.fromisoformat(body.date)
    except ValueError as e:
        raise InvalidRequestError("date must be YYYY-MM-DD") from e
    used, sent, errors = 0, [], []
    with _gameplan() as client:
        for task in tasks:
            if task.gameplan_task_id:
                errors.append(f"'{task.title}' is already in Game Plan")
                continue
            if used and used + task.est_minutes > body.per_day_minutes:
                day, used = day + timedelta(days=1), 0
            space = db.get(Space, task.space_id) if task.space_id else None
            note = "\n".join(
                x
                for x in [
                    f"First step: {task.first_step}" if task.first_step else "",
                    task.detail or "",
                    f"Supplies: {', '.join(task.supplies)}" if task.supplies else "",
                    f"From Home organization{f' ({space.name})' if space else ''}, step {task.id}",
                ]
                if x
            )
            payload = {
                "title": task.title,
                "date": day.isoformat(),
                "est": task.est_minutes,
                "area": settings.gameplan_area,
                "note": note,
            }
            try:
                r = client.post("/api/tasks", json=payload)
                r.raise_for_status()
            except httpx.HTTPError as e:
                errors.append(f"'{task.title}': {e}")
                continue
            task.gameplan_task_id = str(r.json()["id"])
            task.gameplan_date = day.isoformat()
            used += task.est_minutes
            sent.append(task)
    db.commit()
    return SendResult(sent=[TaskOut.model_validate(t) for t in sent], errors=errors)


def sync_from_gameplan(db: Session) -> int:
    """Mark steps done that were finished in Game Plan. Returns how many changed."""
    linked = list(db.scalars(select(Task).where(Task.gameplan_task_id.is_not(None), Task.status != "done")))
    if not linked:
        return 0
    start = min(t.gameplan_date or "1970-01-01" for t in linked)
    with _gameplan() as client:
        r = client.get("/api/tasks", params={"start": start})
        r.raise_for_status()
        remote = {str(t["id"]): t for t in r.json()}
    changed = 0
    for task in linked:
        other = remote.get(task.gameplan_task_id or "")
        if other and other.get("done"):
            task.status, task.done_at = "done", now()
            changed += 1
        elif other and other.get("date") and other["date"] != task.gameplan_date:
            task.gameplan_date = other["date"]  # moved in Game Plan
    db.commit()
    return changed
