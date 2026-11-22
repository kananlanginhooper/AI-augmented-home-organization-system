"""The whole loop on a throwaway SQLite DB: upload -> analysis -> plan -> progress -> review,
with the Claude answers posted the way a Claude Code thread posts them."""

from __future__ import annotations

import io
import os
import tempfile

TMP = tempfile.mkdtemp()
os.environ.update(
    DATABASE_URL=f"sqlite:///{TMP}/test.db",
    PHOTO_DIR=f"{TMP}/photos",
    ANTHROPIC_API_KEY="",
    GAMEPLAN_API_URL="http://gameplan.test",
    ENV_FILE="/nonexistent",
)

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402
from app.services import plans as plan_service  # noqa: E402


def jpeg(color: str) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), color).save(buf, "JPEG")
    return buf.getvalue()


ANALYSIS = {
    "space_guess": "garage shelving",
    "summary": "Crowded shelf with bins and loose tools.",
    "items": [
        {
            "name": "Blue storage bin",
            "category": "storage",
            "quantity": 3,
            "spot": "top shelf",
            "condition": "good",
            "suggested_disposition": "keep",
            "reason": "Sturdy and reusable",
        },
        {
            "name": "Broken box fan",
            "category": "appliance",
            "quantity": 1,
            "spot": "floor",
            "condition": "cracked blade",
            "suggested_disposition": "trash",
            "reason": "Not repairable",
        },
    ],
    "observations": [{"issue": "Tools loose on the floor", "severity": "medium", "suggestion": "Pegboard"}],
    "questions": ["Is the old bike still used?"],
}

PLAN = {
    "summary": "Clear the floor, then shelve what stays.",
    "decisions": [{"question": "Keep the bike?", "options": ["keep", "sell"], "why": "It takes a whole corner"}],
    "tasks": [
        {
            "key": "clear",
            "title": "Move everything off the floor onto a tarp",
            "detail": "",
            "first_step": "Lay the tarp",
            "phase": "sort",
            "est_minutes": 30,
            "priority": 1,
            "depends_on": [],
            "supplies": ["tarp"],
        },
        {
            "key": "trash",
            "title": "Bag the broken fan and trash for pickup",
            "detail": "",
            "first_step": "Get a bag",
            "phase": "remove",
            "est_minutes": 15,
            "priority": 2,
            "depends_on": ["clear"],
            "supplies": ["contractor bags"],
        },
    ],
    "shopping": [{"item": "Pegboard", "quantity": "1 sheet", "why": "Wall storage for tools"}],
}


def test_full_loop(monkeypatch):
    with TestClient(app) as c:
        cfg = c.get("/api/config").json()
        assert cfg["claude"]["apiWorker"] is False

        up = c.post("/api/photos", files={"file": ("shelf.jpg", jpeg("gray"))}, data={"space": "Garage/Shelf", "phase": "before"})
        assert up.status_code == 201, up.text
        photo = up.json()["photo"]
        again = c.post("/api/photos", files={"file": ("copy.jpg", jpeg("gray"))}, data={"space": "Garage"})
        assert again.json()["duplicate"] is True
        assert c.get(f"/api/photos/{photo['id']}/file?size=thumb").status_code == 200

        spaces = {s["path"]: s for s in c.get("/api/spaces").json()}
        assert set(spaces) == {"Garage", "Garage / Shelf"}
        garage = spaces["Garage"]

        # A thread takes the analysis job and answers it.
        ctx = c.post("/api/ai/jobs/claim").json()
        assert ctx["job"]["kind"] == "analyze_photo" and ctx["photo_ids"] == [photo["id"]]
        assert c.post(f"/api/ai/jobs/{ctx['job']['id']}/result", json={"result": ANALYSIS}).status_code == 200
        items = c.get(f"/api/items?space_id={garage['id']}").json()
        assert len(items) == 2 and not any(i["confirmed"] for i in items)
        fan = next(i for i in items if "fan" in i["name"])
        assert c.patch(f"/api/items/{fan['id']}", json={"disposition": "trash"}).json()["confirmed"] is True

        # Bad shapes are refused, not half-applied.
        plan = c.post(f"/api/spaces/{garage['id']}/plans", json={"goal": "Park the car inside", "session_minutes": 30}).json()
        plan_job = c.post("/api/ai/jobs/claim").json()
        assert plan_job["job"]["kind"] == "make_plan" and "Broken box fan" in plan_job["context"]
        assert c.post(f"/api/ai/jobs/{plan_job['job']['id']}/result", json={"result": {"summary": "x"}}).status_code == 400
        assert c.post(f"/api/ai/jobs/{plan_job['job']['id']}/result", json={"result": PLAN}).status_code == 200

        detail = c.get(f"/api/plans/{plan['id']}").json()
        assert detail["status"] == "active" and len(detail["tasks"]) == 2
        first, second = detail["tasks"]
        assert second["depends_on"] == [first["id"]]

        # Only the first step is ready; finishing it unlocks the second.
        ov = c.get("/api/overview").json()
        assert [t["id"] for t in ov["next_tasks"]] == [first["id"]]
        c.patch(f"/api/tasks/{first['id']}", json={"status": "done"})
        ov = c.get("/api/overview").json()
        assert [t["id"] for t in ov["next_tasks"]] == [second["id"]]
        assert ov["progress"]["tasks_done"] == 1 and ov["progress"]["minutes_done"] == 30

        # Game Plan hand-off, against a fake Game Plan.
        # Game Plan splits the step: part 1 keeps gp-1, part 2 is gp-2 with splitFrom gp-1.
        part2_done = {"value": False}

        def fake(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return httpx.Response(201, json={"id": "gp-1", "date": "2026-11-23", "done": False})
            return httpx.Response(
                200,
                json=[
                    {"id": "gp-1", "date": "2026-11-23", "done": True, "splitFrom": None},
                    {"id": "gp-2", "date": "2026-11-24", "done": part2_done["value"], "splitFrom": "gp-1"},
                ],
            )

        monkeypatch.setattr(
            plan_service, "_gameplan", lambda: httpx.Client(base_url="http://gameplan.test", transport=httpx.MockTransport(fake))
        )
        sent = c.post("/api/gameplan/send", json={"task_ids": [second["id"]], "date": "2026-11-23"}).json()
        assert sent["errors"] == [] and sent["sent"][0]["gameplan_task_id"] == "gp-1"
        assert c.post("/api/gameplan/sync").json() == {"marked_done": 0}  # part 2 still open
        part2_done["value"] = True
        assert c.post("/api/gameplan/sync").json() == {"marked_done": 1}

        # Progress photo + review.
        c.post(
            "/api/photos",
            files={"file": ("after.jpg", jpeg("white"))},
            data={"space_id": str(garage["id"]), "phase": "after", "analyze": "false"},
        )
        review_job = c.post(f"/api/spaces/{garage['id']}/review").json()
        ctx = c.get(f"/api/ai/jobs/{review_job['id']}/context").json()
        assert len(ctx["photo_ids"]) == 2
        review = {
            "summary": "Floor is clear.",
            "percent_done": 60,
            "wins": ["floor"],
            "remaining": ["pegboard"],
            "new_tasks": [
                {
                    "key": "peg",
                    "title": "Mount the pegboard",
                    "detail": "",
                    "first_step": "Find studs",
                    "phase": "store",
                    "est_minutes": 45,
                    "priority": 2,
                    "depends_on": [],
                    "supplies": [],
                }
            ],
        }
        c.post(f"/api/ai/jobs/{review_job['id']}/result", json={"result": review})
        assert c.get(f"/api/spaces/{garage['id']}/checkins").json()[0]["percent_done"] == 60
        assert len(c.get(f"/api/plans/{plan['id']}").json()["tasks"]) == 3

        # Other tools: the feed, and posting an evaluation.
        feed = c.get("/api/photos/feed?missing_tool=siglip-tags").json()
        assert len(feed) == 2
        c.put(f"/api/photos/{photo['id']}/evaluations", json={"tool": "siglip-tags", "result": {"tags": ["shelf"]}})
        assert [p["id"] for p in c.get("/api/photos/feed?missing_tool=siglip-tags").json()] != [photo["id"]]
        assert c.get("/api/photos/feed").json()[0]["tools_done"] == ["siglip-tags"]
