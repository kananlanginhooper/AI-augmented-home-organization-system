"""Database tables.

spaces    rooms, zones inside rooms, and containers (bins, shelves, drawers): a tree via parent_id
photos    files on disk under PHOTO_DIR; analysis holds Claude's last reading of the photo
items     the inventory: what it is, where it lives, what to do with it
plans     one goal for one space; tasks are its checklist
tasks     concrete steps; gameplan_task_id links a step sent to Game Plan
checkins  written progress reviews (from Claude or typed by hand)
photo_evaluations  results other tools post about a photo
ai_jobs   the Claude work queue, run by the API worker or by a Claude Code thread
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Space(Base):
    __tablename__ = "spaces"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20), default="room")  # room | zone | container
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("spaces.id", ondelete="SET NULL"), nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    space_id: Mapped[int | None] = mapped_column(ForeignKey("spaces.id", ondelete="SET NULL"), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    filename: Mapped[str] = mapped_column(String(120))  # stored name under PHOTO_DIR
    original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    phase: Mapped[str] = mapped_column(String(20), default="before")  # before | progress | after | reference
    source: Mapped[str] = mapped_column(String(20), default="dashboard")  # dashboard | thread | folder
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    space_id: Mapped[int | None] = mapped_column(ForeignKey("spaces.id", ondelete="SET NULL"), nullable=True)
    photo_id: Mapped[int | None] = mapped_column(ForeignKey("photos.id", ondelete="SET NULL"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    spot: Mapped[str | None] = mapped_column(String(200), nullable=True)  # "top shelf, left"
    condition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # keep | donate | sell | trash | relocate | undecided
    disposition: Mapped[str] = mapped_column(String(20), default="undecided")
    confirmed: Mapped[bool] = mapped_column(default=False)  # False = Claude's suggestion, not yet reviewed
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual | claude
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"))
    goal: Mapped[str] = mapped_column(Text)
    session_minutes: Mapped[int] = mapped_column(Integer, default=30)
    constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    decisions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    shopping: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="planning")  # planning | active | done | archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"))
    space_id: Mapped[int | None] = mapped_column(ForeignKey("spaces.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_step: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # sort | decide | remove | clean | repair | store | label | maintain | buy
    phase: Mapped[str] = mapped_column(String(20), default="sort")
    est_minutes: Mapped[int] = mapped_column(Integer, default=20)
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1 high .. 3 low
    sort: Mapped[int] = mapped_column(Integer, default=0)
    depends_on: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)  # task ids
    supplies: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="todo")  # todo | doing | done | skipped
    source: Mapped[str] = mapped_column(String(20), default="claude")  # claude | manual | review
    gameplan_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gameplan_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Checkin(Base):
    __tablename__ = "checkins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"))
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    percent_done: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="claude")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class PhotoEvaluation(Base):
    """Results other tools post about a photo (image tagging, face clusters, sensitivity, OCR, ...).
    One row per tool per photo; a re-run replaces it."""

    __tablename__ = "photo_evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    photo_id: Mapped[int] = mapped_column(ForeignKey("photos.id", ondelete="CASCADE"))
    tool: Mapped[str] = mapped_column(String(60))  # e.g. "siglip-tags", "sensitivity"
    version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("photo_id", "tool", name="uq_photo_evaluation_tool"),)


class AiJob(Base):
    __tablename__ = "ai_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))  # analyze_photo | make_plan | review_progress
    target_id: Mapped[int] = mapped_column(Integer)  # photo id, plan id, or space id (review_progress)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | running | done | failed
    worker: Mapped[str | None] = mapped_column(String(20), nullable=True)  # api | thread
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
