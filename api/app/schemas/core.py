"""Request and response models for the dashboard's own data."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- spaces ---
class SpaceIn(BaseModel):
    name: str
    kind: Literal["room", "zone", "container"] = "room"
    parent_id: int | None = None
    goal: str | None = None
    note: str | None = None


class SpacePatch(BaseModel):
    name: str | None = None
    kind: Literal["room", "zone", "container"] | None = None
    parent_id: int | None = None
    goal: str | None = None
    note: str | None = None


class SpaceOut(Out):
    id: int
    name: str
    kind: str
    parent_id: int | None
    goal: str | None
    note: str | None


class Progress(BaseModel):
    tasks_total: int
    tasks_done: int
    minutes_total: int
    minutes_done: int
    items_total: int
    items_decided: int
    photos: int
    latest_percent: int | None


class SpaceSummary(SpaceOut):
    path: str  # "Garage / Back wall / Bin 3"
    progress: Progress


# --- photos ---
class PhotoOut(Out):
    id: int
    space_id: int | None
    original_name: str | None
    width: int | None
    height: int | None
    taken_at: datetime | None
    phase: str
    source: str
    caption: str | None
    analysis: dict[str, Any] | None
    analyzed_at: datetime | None
    uploaded_at: datetime


class PhotoPatch(BaseModel):
    space_id: int | None = None
    phase: Literal["before", "progress", "after", "reference"] | None = None
    caption: str | None = None


class UploadResult(BaseModel):
    photo: PhotoOut
    duplicate: bool


# --- items ---
Disposition = Literal["keep", "donate", "sell", "trash", "relocate", "undecided"]


class ItemIn(BaseModel):
    name: str
    category: str | None = None
    space_id: int | None = None
    quantity: int = Field(1, ge=1)
    spot: str | None = None
    condition: str | None = None
    disposition: Disposition = "undecided"
    note: str | None = None


class ItemPatch(BaseModel):
    name: str | None = None
    category: str | None = None
    space_id: int | None = None
    quantity: int | None = Field(None, ge=1)
    spot: str | None = None
    condition: str | None = None
    disposition: Disposition | None = None
    confirmed: bool | None = None
    note: str | None = None


class ItemOut(Out):
    id: int
    name: str
    category: str | None
    space_id: int | None
    photo_id: int | None
    quantity: int
    spot: str | None
    condition: str | None
    disposition: str
    confirmed: bool
    note: str | None
    source: str
    updated_at: datetime


# --- plans and tasks ---
class PlanIn(BaseModel):
    goal: str
    session_minutes: int = Field(30, ge=5, le=240)
    constraints: str | None = None  # budget, help available, deadlines, things to keep


class TaskOut(Out):
    id: int
    plan_id: int
    space_id: int | None
    title: str
    detail: str | None
    first_step: str | None
    phase: str
    est_minutes: int
    priority: int
    sort: int
    depends_on: list[int] | None
    supplies: list[str] | None
    status: str
    source: str
    gameplan_task_id: str | None
    gameplan_date: str | None
    done_at: datetime | None


class TaskIn(BaseModel):
    title: str
    detail: str | None = None
    first_step: str | None = None
    phase: str = "sort"
    est_minutes: int = Field(20, ge=1)
    priority: int = Field(2, ge=1, le=3)


class TaskPatch(BaseModel):
    title: str | None = None
    detail: str | None = None
    first_step: str | None = None
    est_minutes: int | None = Field(None, ge=1)
    priority: int | None = Field(None, ge=1, le=3)
    sort: int | None = None
    status: Literal["todo", "doing", "done", "skipped"] | None = None


class PlanOut(Out):
    id: int
    space_id: int
    goal: str
    session_minutes: int
    constraints: str | None
    summary: str | None
    decisions: list[dict[str, Any]] | None
    shopping: list[dict[str, Any]] | None
    status: str
    created_at: datetime


class PlanDetail(PlanOut):
    tasks: list[TaskOut]
    job_status: str | None  # the latest make_plan job, while it runs


class SendToGamePlanIn(BaseModel):
    task_ids: list[int]
    date: str  # YYYY-MM-DD, the first day; tasks are placed in order
    per_day_minutes: int = Field(60, ge=10)


class SendResult(BaseModel):
    sent: list[TaskOut]
    errors: list[str]


class CheckinOut(Out):
    id: int
    space_id: int
    plan_id: int | None
    summary: str
    percent_done: int | None
    source: str
    created_at: datetime


class CheckinIn(BaseModel):
    summary: str
    percent_done: int | None = Field(None, ge=0, le=100)


# --- evaluations from other tools ---
class EvaluationIn(BaseModel):
    tool: str = Field(..., min_length=1, max_length=60)
    version: str | None = None
    result: dict[str, Any]


class EvaluationOut(Out):
    id: int
    photo_id: int
    tool: str
    version: str | None
    result: dict[str, Any]
    created_at: datetime


class PhotoForTools(BaseModel):
    """One row of the feed other tools read: what to evaluate, and what has been done already."""

    id: int
    space_path: str | None
    phase: str
    uploaded_at: datetime
    file_url: str  # relative to the API: api/photos/{id}/file
    sha256: str
    analyzed: bool
    tools_done: list[str]


# --- jobs ---
class JobOut(Out):
    id: int
    kind: str
    target_id: int
    status: str
    worker: str | None
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class JobContext(BaseModel):
    """Everything a Claude Code thread needs to do a job by hand."""

    job: JobOut
    instructions: str
    context: str  # the same text the API worker sends Claude
    photo_ids: list[int]  # GET /api/photos/{id}/file to look at them
    result_schema: dict[str, Any]


class JobResultIn(BaseModel):
    result: dict[str, Any]


# --- system ---
class RuntimeConfig(BaseModel):
    apiBase: str
    basePath: str
    publicUrl: str
    frameParents: list[str]
    login: dict[str, Any]
    claude: dict[str, Any]
    gameplan: dict[str, Any]


class Overview(BaseModel):
    spaces: list[SpaceSummary]
    progress: Progress
    next_tasks: list[TaskOut]
    open_decisions: int
    pending_jobs: int
    recent_checkins: list[CheckinOut]
