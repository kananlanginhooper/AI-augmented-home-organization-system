from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.core import ItemIn, ItemOut, ItemPatch
from app.services import items as service
from app.services import spaces

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemOut])
def list_items(
    db: DbSession,
    space_id: int | None = None,
    q: str | None = None,
    disposition: str | None = None,
    unconfirmed: bool = False,
):
    ids = spaces.subtree_ids(db, space_id) if space_id is not None else None
    return service.list_items(db, ids, q, disposition, unconfirmed)


@router.post("", response_model=ItemOut, status_code=201)
def create_item(body: ItemIn, db: DbSession):
    return service.create_item(db, body)


@router.patch("/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, body: ItemPatch, db: DbSession):
    return service.patch_item(db, item_id, body)


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: DbSession) -> None:
    service.delete_item(db, item_id)
