"""Spaces (room > zone > container) and the progress numbers shown for each."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Checkin, Item, Photo, Plan, Space, Task
from app.schemas.core import Progress, SpaceIn, SpacePatch, SpaceSummary
from app.services.common import InvalidRequestError, apply_patch, get_or_404


def list_spaces(db: Session) -> list[Space]:
    return list(db.scalars(select(Space).order_by(Space.sort, Space.name)))


def create_space(db: Session, body: SpaceIn) -> Space:
    if body.parent_id is not None:
        get_or_404(db, Space, body.parent_id)
    space = Space(**body.model_dump())
    db.add(space)
    db.commit()
    return space


def find_or_create(db: Session, name: str, kind: str = "room", parent_id: int | None = None) -> Space:
    """Used by uploads that name a space ("Garage", or "Garage/Back wall")."""
    parent = parent_id
    space = None
    for i, part in enumerate(p.strip() for p in name.split("/") if p.strip()):
        space = db.scalar(select(Space).where(func.lower(Space.name) == part.lower(), Space.parent_id.is_(parent)))
        if space is None:
            space = Space(name=part, kind=kind if i == 0 else "zone", parent_id=parent)
            db.add(space)
            db.flush()
        parent = space.id
    if space is None:
        raise InvalidRequestError("empty space name")
    db.commit()
    return space


def patch_space(db: Session, space_id: int, body: SpacePatch) -> Space:
    space = get_or_404(db, Space, space_id)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("parent_id") is not None and changes["parent_id"] in subtree_ids(db, space_id):
        raise InvalidRequestError("a space can't sit inside itself")
    apply_patch(space, changes)
    db.commit()
    return space


def delete_space(db: Session, space_id: int) -> None:
    db.delete(get_or_404(db, Space, space_id))
    db.commit()


def subtree_ids(db: Session, space_id: int) -> set[int]:
    """The space and everything inside it."""
    children: dict[int | None, list[int]] = {}
    for sid, parent in db.execute(select(Space.id, Space.parent_id)):
        children.setdefault(parent, []).append(sid)
    out, todo = set(), [space_id]
    while todo:
        sid = todo.pop()
        if sid not in out:
            out.add(sid)
            todo.extend(children.get(sid, []))
    return out


def paths(db: Session) -> dict[int, str]:
    rows = {s.id: s for s in list_spaces(db)}

    def path(sid: int, seen: set[int]) -> str:
        s = rows[sid]
        if s.parent_id in rows and s.parent_id not in seen:
            return path(s.parent_id, seen | {sid}) + " / " + s.name
        return s.name

    return {sid: path(sid, set()) for sid in rows}


def progress(db: Session, space_ids: set[int] | None) -> Progress:
    """Counts for a set of spaces (None = the whole house)."""

    def scoped(stmt, column):  # type: ignore[no-untyped-def]
        return stmt if space_ids is None else stmt.where(column.in_(space_ids))

    task_rows = db.execute(scoped(select(Task.status, Task.est_minutes), Task.space_id)).all()
    active = [t for t in task_rows if t.status != "skipped"]
    done = [t for t in active if t.status == "done"]
    items_total = db.scalar(scoped(select(func.count(Item.id)), Item.space_id)) or 0
    items_decided = (
        db.scalar(
            scoped(select(func.count(Item.id)).where(Item.confirmed.is_(True), Item.disposition != "undecided"), Item.space_id)
        )
        or 0
    )
    photos = db.scalar(scoped(select(func.count(Photo.id)), Photo.space_id)) or 0
    latest = db.scalar(scoped(select(Checkin.percent_done).order_by(Checkin.created_at.desc()).limit(1), Checkin.space_id))
    return Progress(
        tasks_total=len(active),
        tasks_done=len(done),
        minutes_total=sum(t.est_minutes for t in active),
        minutes_done=sum(t.est_minutes for t in done),
        items_total=items_total,
        items_decided=items_decided,
        photos=photos,
        latest_percent=latest,
    )


def summaries(db: Session) -> list[SpaceSummary]:
    names = paths(db)
    out = []
    for space in list_spaces(db):
        out.append(
            SpaceSummary(
                id=space.id,
                name=space.name,
                kind=space.kind,
                parent_id=space.parent_id,
                goal=space.goal,
                note=space.note,
                path=names[space.id],
                progress=progress(db, subtree_ids(db, space.id)),
            )
        )
    return sorted(out, key=lambda s: s.path.lower())


def plans_for(db: Session, space_id: int) -> list[Plan]:
    return list(db.scalars(select(Plan).where(Plan.space_id == space_id).order_by(Plan.created_at.desc())))
