"""The JSON shapes Claude returns. The API worker asks for them as structured output,
and a Claude Code thread posts the same shapes to /api/ai/jobs/{id}/result."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Disposition = Literal["keep", "donate", "sell", "trash", "relocate", "undecided"]
Phase = Literal["sort", "decide", "remove", "clean", "repair", "store", "label", "maintain", "buy"]


class SeenItem(BaseModel):
    name: str
    category: str
    quantity: int
    spot: str  # where in the photo / space, e.g. "floor by the door"
    condition: str
    suggested_disposition: Disposition
    reason: str


class Observation(BaseModel):
    issue: str  # what needs attention, e.g. "boxes stacked against the water heater"
    severity: Literal["low", "medium", "high"]
    suggestion: str


class PhotoAnalysis(BaseModel):
    space_guess: str  # e.g. "garage, back wall shelving"; empty if unclear
    summary: str
    items: list[SeenItem]
    observations: list[Observation]
    questions: list[str]  # things only the owner can answer


class PlannedTask(BaseModel):
    key: str  # short id used only inside this answer, for depends_on
    title: str
    detail: str
    first_step: str  # the first physical action, e.g. "Carry the three blue bins to the driveway"
    phase: Phase
    est_minutes: int
    priority: Literal[1, 2, 3]
    depends_on: list[str]  # keys of earlier tasks
    supplies: list[str]


class Decision(BaseModel):
    question: str
    options: list[str]
    why: str


class ShoppingLine(BaseModel):
    item: str
    quantity: str
    why: str


class PlanResult(BaseModel):
    summary: str
    decisions: list[Decision]
    tasks: list[PlannedTask]
    shopping: list[ShoppingLine]


class ReviewResult(BaseModel):
    summary: str
    percent_done: int
    wins: list[str]
    remaining: list[str]
    new_tasks: list[PlannedTask]


RESULT_SCHEMAS: dict[str, type[BaseModel]] = {
    "analyze_photo": PhotoAnalysis,
    "make_plan": PlanResult,
    "review_progress": ReviewResult,
}
