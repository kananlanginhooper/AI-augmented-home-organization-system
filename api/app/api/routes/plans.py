from __future__ import annotations

from typing import Literal

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.core import PlanDetail, PlanOut, SendResult, SendToGamePlanIn, TaskIn, TaskOut, TaskPatch
from app.services import plans as service

router = APIRouter(tags=["plans"])


@router.get("/plans/{plan_id}", response_model=PlanDetail)
def get_plan(plan_id: int, db: DbSession):
    return service.detail(db, plan_id)


@router.post("/plans/{plan_id}/status", response_model=PlanOut)
def set_status(plan_id: int, status: Literal["active", "done", "archived"], db: DbSession):
    return service.set_status(db, plan_id, status)


@router.post("/plans/{plan_id}/tasks", response_model=TaskOut, status_code=201)
def add_task(plan_id: int, body: TaskIn, db: DbSession):
    return service.add_task(db, plan_id, body)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def patch_task(task_id: int, body: TaskPatch, db: DbSession):
    return service.patch_task(db, task_id, body)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: DbSession) -> None:
    service.delete_task(db, task_id)


@router.post("/gameplan/send", response_model=SendResult)
def send_to_gameplan(body: SendToGamePlanIn, db: DbSession):
    return service.send_to_gameplan(db, body)


@router.post("/gameplan/sync")
def sync_from_gameplan(db: DbSession) -> dict[str, int]:
    return {"marked_done": service.sync_from_gameplan(db)}
