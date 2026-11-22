from __future__ import annotations

from typing import TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class NotFoundError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


def get_or_404[T](db: Session, model: type[T], row_id: int) -> T:
    row = db.get(model, row_id)
    if row is None:
        raise NotFoundError(f"{model.__name__} {row_id} not found")
    return row


def apply_patch(row: object, patch: dict) -> None:
    for key, value in patch.items():
        setattr(row, key, value)
