"""The Claude work queue.

A job is (kind, target). The same three functions serve both workers:
  build(job)  -> instructions, context text, photo ids (what Claude is shown)
  apply(job, result)  -> writes the answer into items / plans / tasks / checkins
The API worker (when ANTHROPIC_API_KEY is set) sends build()'s output to the Claude API.
A Claude Code thread fetches the same build() output from /api/ai/jobs/{id}/context,
looks at the photos itself and posts the answer to /api/ai/jobs/{id}/result.
"""

from __future__ import annotations

import base64
import logging
import threading
import time

from pydantic import BaseModel, ValidationError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AiJob, Checkin, Item, Photo, Plan, Space, Task, now
from app.db.session import SessionLocal
from app.schemas.ai import RESULT_SCHEMAS, PhotoAnalysis, PlannedTask, PlanResult, ReviewResult
from app.schemas.core import JobContext, JobOut
from app.services import photos as photo_files
from app.services import spaces
from app.services.common import InvalidRequestError, NotFoundError, get_or_404

log = logging.getLogger("ai")

SYSTEM = """You help one person organize their home: a practical, unhurried professional organizer.
You see their photos and their inventory, and you write plans they can actually carry out.

Rules for every plan and task:
- A task is one sitting of real work, 10-45 minutes, that fits the person's session length. Split anything bigger.
- The title starts with a verb and names the exact spot ("Empty the left garage shelf onto a tarp"), never "Organize the garage".
- first_step is the first physical action, small enough to start without thinking.
- Order matters: clear and sort before cleaning; decide what stays before buying storage; buy containers
  only after you know what goes in them (measure first); label and set up maintenance last.
- Items the owner already decided (confirmed) keep that decision. Undecided items become decide tasks or questions,
  and you never assume something should be thrown away.
- Things only the owner can know (sentimental value, who else uses the space, budget) are questions, not guesses.
- Donate / sell / trash outflow needs its own tasks (bag it, schedule a drop-off), or the pile just moves.
- Be specific about what you can see; say so when a photo is unclear instead of inventing details."""

INSTRUCTIONS = {
    "analyze_photo": "Look at the photo. List the items you can identify (group many small identical things into one "
    "line with a quantity), where they are, their condition and a suggested disposition with the reason. Then list "
    "what needs attention in this space and any questions for the owner. space_guess: what room/area this looks like.",
    "make_plan": "Write the checklist that gets this space from where it is now to the goal. Use the inventory, the "
    "observations and the photos. Give each task a short key so later tasks can depend on earlier ones. Put supplies "
    "that must be bought in the shopping list. Decisions the owner must make first go in decisions.",
    "review_progress": "Compare the earlier photos with the latest ones and the checklist state. Write a short, honest "
    "check-in: what got done, what's left, an estimated percent done toward the goal, and any new tasks the latest "
    "photos show are needed (don't repeat open tasks).",
}

MAX_PHOTOS = 6


# --- queue ---
def queue(db: Session, kind: str, target_id: int) -> AiJob:
    if kind not in RESULT_SCHEMAS:
        raise InvalidRequestError(f"unknown job kind {kind}")
    job = AiJob(kind=kind, target_id=target_id)
    db.add(job)
    db.flush()
    return job


def list_jobs(db: Session, status: str | None = None, limit: int = 100) -> list[AiJob]:
    stmt = select(AiJob).order_by(AiJob.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(AiJob.status == status)
    return list(db.scalars(stmt))


def claim(db: Session, job_id: int | None, worker: str) -> AiJob | None:
    """Move one pending job to running. Atomic, so the API worker and a thread never take the same job."""
    if job_id is None:
        job_id = db.scalar(select(AiJob.id).where(AiJob.status == "pending").order_by(AiJob.id).limit(1))
        if job_id is None:
            return None
    taken = db.execute(
        update(AiJob)
        .where(AiJob.id == job_id, AiJob.status == "pending")
        .values(status="running", worker=worker, started_at=now(), error=None)
    ).rowcount
    db.commit()
    return db.get(AiJob, job_id) if taken else None


def retry(db: Session, job_id: int) -> AiJob:
    job = get_or_404(db, AiJob, job_id)
    job.status, job.worker, job.error, job.started_at, job.finished_at = "pending", None, None, None, None
    db.commit()
    return job


def fail(db: Session, job: AiJob, error: str) -> None:
    job.status, job.error, job.finished_at = "failed", error[:4000], now()
    db.commit()


# --- what Claude is shown ---
def _item_lines(items: list[Item], names: dict[int, str]) -> str:
    if not items:
        return "(no inventory yet)"
    lines = []
    for i in items:
        where = names.get(i.space_id, "unplaced") if i.space_id else "unplaced"
        decided = f"{i.disposition} (owner decided)" if i.confirmed else f"suggested {i.disposition}, not reviewed"
        extra = "; ".join(x for x in [i.spot, i.condition, i.note] if x)
        lines.append(f"- {i.name} x{i.quantity} [{where}] {decided}{f' - {extra}' if extra else ''}")
    return "\n".join(lines)


def _observation_lines(photo_rows: list[Photo]) -> str:
    lines = []
    for p in photo_rows:
        for o in (p.analysis or {}).get("observations", []):
            lines.append(f"- ({o.get('severity')}) {o.get('issue')} -> {o.get('suggestion')} [photo {p.id}]")
        for q in (p.analysis or {}).get("questions", []):
            lines.append(f"- question: {q} [photo {p.id}]")
    return "\n".join(lines) or "(no photo observations yet)"


def _task_lines(tasks: list[Task]) -> str:
    return "\n".join(f"- [{t.status}] {t.title} ({t.est_minutes} min, {t.phase})" for t in tasks) or "(none)"


def build(db: Session, job: AiJob) -> tuple[str, str, list[int]]:
    """Returns (instructions, context text, photo ids to show)."""
    names = spaces.paths(db)
    if job.kind == "analyze_photo":
        photo = get_or_404(db, Photo, job.target_id)
        not_this_photo = Item.photo_id.is_(None) | (Item.photo_id != photo.id)
        known = db.scalars(select(Item).where(Item.space_id == photo.space_id, not_this_photo)) if photo.space_id else []
        context = "\n".join(
            [
                f"Space: {names.get(photo.space_id, 'not assigned yet') if photo.space_id else 'not assigned yet'}",
                f"Photo phase: {photo.phase}",
                f"Owner's caption: {photo.caption or '(none)'}",
                "Already in the inventory for this space (don't list these again unless you see more of them):",
                _item_lines(list(known), names),
            ]
        )
        return INSTRUCTIONS["analyze_photo"], context, [photo.id]

    if job.kind == "make_plan":
        plan = get_or_404(db, Plan, job.target_id)
        ids = spaces.subtree_ids(db, plan.space_id)
        photo_rows = photo_files.list_photos(db, ids)
        items = list(db.scalars(select(Item).where(Item.space_id.in_(ids)).order_by(Item.space_id, Item.name)))
        other = list(db.scalars(select(Task).where(Task.space_id.in_(ids), Task.plan_id != plan.id, Task.status != "done")))
        context = "\n".join(
            [
                f"Space: {names[plan.space_id]}",
                "Spaces inside it: " + (", ".join(names[i] for i in sorted(ids) if i != plan.space_id) or "(none)"),
                f"Goal: {plan.goal}",
                f"Session length: {plan.session_minutes} minutes",
                f"Constraints from the owner: {plan.constraints or '(none)'}",
                "",
                "Inventory:",
                _item_lines(items, names),
                "",
                "Observations from photos:",
                _observation_lines(photo_rows),
                "",
                "Open tasks from other plans for this space (don't duplicate):",
                _task_lines(other),
            ]
        )
        shown = [p.id for p in photo_rows if p.phase in ("before", "reference", "progress")][:MAX_PHOTOS]
        return INSTRUCTIONS["make_plan"], context, shown

    if job.kind == "review_progress":
        space = get_or_404(db, Space, job.target_id)
        ids = spaces.subtree_ids(db, space.id)
        photo_rows = photo_files.list_photos(db, ids)  # newest first
        plan = _active_plan(db, space.id)
        tasks = list(db.scalars(select(Task).where(Task.space_id.in_(ids)).order_by(Task.sort)))
        last = db.scalar(select(Checkin).where(Checkin.space_id == space.id).order_by(Checkin.created_at.desc()).limit(1))
        earliest = [p.id for p in reversed(photo_rows) if p.phase in ("before", "reference")][:3]
        latest = [p.id for p in photo_rows if p.phase in ("progress", "after")][:3]
        context = "\n".join(
            [
                f"Space: {names[space.id]}",
                f"Goal: {plan.goal if plan else space.goal or '(none set)'}",
                f"Earlier photos: {earliest or 'none'}; latest photos: {latest or 'none'} (shown in that order)",
                "",
                "Checklist:",
                _task_lines(tasks),
                "",
                f"Last check-in: {last.summary if last else '(none)'}",
            ]
        )
        return INSTRUCTIONS["review_progress"], context, earliest + latest

    raise InvalidRequestError(f"unknown job kind {job.kind}")


def context_for(db: Session, job_id: int) -> JobContext:
    job = get_or_404(db, AiJob, job_id)
    instructions, context, photo_ids = build(db, job)
    return JobContext(
        job=JobOut.model_validate(job),
        instructions=SYSTEM + "\n\n" + instructions,
        context=context,
        photo_ids=photo_ids,
        result_schema=RESULT_SCHEMAS[job.kind].model_json_schema(),
    )


# --- writing the answer back ---
def _active_plan(db: Session, space_id: int) -> Plan | None:
    return db.scalar(
        select(Plan)
        .where(Plan.space_id == space_id, Plan.status.in_(["planning", "active"]))
        .order_by(Plan.created_at.desc())
        .limit(1)
    )


def _add_tasks(db: Session, plan: Plan, planned: list[PlannedTask], source: str) -> None:
    start = db.scalar(select(Task.sort).where(Task.plan_id == plan.id).order_by(Task.sort.desc()).limit(1)) or 0
    by_key: dict[str, Task] = {}
    for n, p in enumerate(planned, start=1):
        task = Task(
            plan_id=plan.id,
            space_id=plan.space_id,
            title=p.title[:200],
            detail=p.detail,
            first_step=p.first_step[:300],
            phase=p.phase,
            est_minutes=max(1, p.est_minutes),
            priority=p.priority,
            sort=start + n,
            supplies=p.supplies,
            source=source,
        )
        db.add(task)
        db.flush()
        by_key[p.key] = task
    for p in planned:
        deps = [by_key[k].id for k in p.depends_on if k in by_key and k != p.key]
        by_key[p.key].depends_on = deps or None


def apply(db: Session, job: AiJob, raw: dict) -> None:
    schema: type[BaseModel] = RESULT_SCHEMAS[job.kind]
    try:
        result = schema.model_validate(raw)
    except ValidationError as e:
        raise InvalidRequestError(f"result doesn't match the {job.kind} schema: {e}") from e

    if isinstance(result, PhotoAnalysis):
        photo = get_or_404(db, Photo, job.target_id)
        photo.analysis, photo.analyzed_at = result.model_dump(), now()
        # A re-analysis replaces Claude's unreviewed suggestions from this photo; reviewed items stay.
        for old in db.scalars(select(Item).where(Item.photo_id == photo.id, Item.confirmed.is_(False), Item.source == "claude")):
            db.delete(old)
        for seen in result.items:
            db.add(
                Item(
                    name=seen.name[:200],
                    category=seen.category[:80],
                    quantity=max(1, seen.quantity),
                    spot=seen.spot[:200],
                    condition=seen.condition[:200],
                    disposition=seen.suggested_disposition,
                    note=seen.reason,
                    space_id=photo.space_id,
                    photo_id=photo.id,
                    source="claude",
                    confirmed=False,
                )
            )
    elif isinstance(result, PlanResult):
        plan = get_or_404(db, Plan, job.target_id)
        plan.summary = result.summary
        plan.decisions = [d.model_dump() for d in result.decisions]
        plan.shopping = [s.model_dump() for s in result.shopping]
        plan.status = "active"
        _add_tasks(db, plan, result.tasks, "claude")
    elif isinstance(result, ReviewResult):
        space = get_or_404(db, Space, job.target_id)
        plan = _active_plan(db, space.id)
        db.add(
            Checkin(
                space_id=space.id,
                plan_id=plan.id if plan else None,
                summary="\n".join(
                    [result.summary]
                    + ([("Done: " + "; ".join(result.wins))] if result.wins else [])
                    + ([("Left: " + "; ".join(result.remaining))] if result.remaining else [])
                ),
                percent_done=max(0, min(100, result.percent_done)),
                source="claude",
            )
        )
        if result.new_tasks:
            if plan is None:
                plan = Plan(space_id=space.id, goal=space.goal or "Follow-ups from a progress review", status="active")
                db.add(plan)
                db.flush()
            _add_tasks(db, plan, result.new_tasks, "review")

    job.status, job.result, job.finished_at, job.error = "done", raw, now(), None
    db.commit()


def submit(db: Session, job_id: int, raw: dict, worker: str = "thread") -> AiJob:
    """A thread posting a result. Claims the job first if nobody has."""
    job = get_or_404(db, AiJob, job_id)
    if job.status == "done":
        raise InvalidRequestError("job is already done")
    if job.status == "pending":
        claim(db, job_id, worker)
        db.refresh(job)
    apply(db, job, raw)
    return job


# --- the API worker ---
def _image_blocks(db: Session, photo_ids: list[int]) -> list[dict]:
    blocks: list[dict] = []
    for pid in photo_ids:
        photo = db.get(Photo, pid)
        path = photo_files.file_path(photo, "claude") if photo else None
        if not path or not path.is_file():
            continue
        data = base64.standard_b64encode(path.read_bytes()).decode()
        blocks.append({"type": "text", "text": f"Photo {pid} ({photo.phase}):"})
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
    return blocks


def run_with_api(db: Session, job: AiJob) -> None:
    import anthropic

    instructions, context, photo_ids = build(db, job)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    content = _image_blocks(db, photo_ids) + [{"type": "text", "text": f"{instructions}\n\n{context}"}]
    try:
        response = client.messages.parse(
            model=settings.claude_model,
            max_tokens=16000,
            system=SYSTEM,
            output_config={"effort": settings.claude_effort},
            messages=[{"role": "user", "content": content}],
            output_format=RESULT_SCHEMAS[job.kind],
        )
    except anthropic.RateLimitError as e:
        # Put it back for the next pass instead of failing it.
        job.status, job.worker, job.started_at, job.error = "pending", None, None, f"rate limited: {e.message}"
        db.commit()
        time.sleep(30)
        return
    except anthropic.APIStatusError as e:
        fail(db, job, f"Claude API {e.status_code}: {e.message}")
        return
    except anthropic.APIConnectionError as e:
        fail(db, job, f"Claude API unreachable: {e}")
        return
    if response.stop_reason == "refusal":
        fail(db, job, f"Claude declined: {getattr(response.stop_details, 'explanation', '')}")
        return
    if response.parsed_output is None:
        fail(db, job, f"no structured answer (stop_reason {response.stop_reason})")
        return
    apply(db, job, response.parsed_output.model_dump())


def _worker_loop(stop: threading.Event) -> None:
    log.info("Claude API worker started (model %s)", settings.claude_model)
    while not stop.is_set():
        with SessionLocal() as db:
            job = claim(db, None, "api")
            if job is None:
                stop.wait(5)
                continue
            try:
                run_with_api(db, job)
            except (InvalidRequestError, NotFoundError) as e:
                fail(db, job, str(e))
            except Exception as e:  # noqa: BLE001  (keep the worker alive; the job shows the error)
                log.exception("job %s failed", job.id)
                db.rollback()
                fail(db, job, f"{type(e).__name__}: {e}")


def start_worker() -> threading.Event | None:
    if not settings.api_worker_enabled:
        return None
    stop = threading.Event()
    threading.Thread(target=_worker_loop, args=(stop,), name="claude-worker", daemon=True).start()
    return stop
