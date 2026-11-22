"""The inventory: what is where, and what happens to it."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Item
from app.schemas.core import ItemIn, ItemPatch
from app.services.common import apply_patch, get_or_404


def list_items(
    db: Session,
    space_ids: set[int] | None = None,
    q: str | None = None,
    disposition: str | None = None,
    unconfirmed: bool = False,
) -> list[Item]:
    stmt = select(Item).order_by(Item.space_id, Item.name)
    if space_ids is not None:
        stmt = stmt.where(Item.space_id.in_(space_ids))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(func.lower(Item.name).like(like), func.lower(Item.category).like(like), func.lower(Item.note).like(like))
        )
    if disposition:
        stmt = stmt.where(Item.disposition == disposition)
    if unconfirmed:
        stmt = stmt.where(Item.confirmed.is_(False))
    return list(db.scalars(stmt))


def create_item(db: Session, body: ItemIn) -> Item:
    item = Item(**body.model_dump(), confirmed=True, source="manual")
    db.add(item)
    db.commit()
    return item


def patch_item(db: Session, item_id: int, body: ItemPatch) -> Item:
    item = get_or_404(db, Item, item_id)
    changes = body.model_dump(exclude_unset=True)
    # Changing what happens to an item is the owner deciding, so it counts as reviewed.
    if "disposition" in changes and "confirmed" not in changes:
        changes["confirmed"] = True
    apply_patch(item, changes)
    db.commit()
    return item


def delete_item(db: Session, item_id: int) -> None:
    db.delete(get_or_404(db, Item, item_id))
    db.commit()
