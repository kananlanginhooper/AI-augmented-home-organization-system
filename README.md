# Home organization: photo inventory and action plans

Photograph a room, closet or bin. Claude works out what is in it and what state it's in. You decide what stays.
Claude turns that into a checklist of small, concrete steps. Progress is tracked as steps get done and new photos come in.
Chosen steps go to Game Plan, so they land on the calendar.

## How it works

1. **Photos in.** Upload them from the dashboard (drag and drop, phone photos and HEIC included), or with
   `tools/upload_photos.py` from a folder. Each photo belongs to a **space** (room, then zone, then container) and has a
   **phase**: before, progress, after or reference.
2. **Claude looks.** Every photo gets an `analyze_photo` job. Claude lists the items it can see, where they are,
   what condition they're in and a suggested disposition (keep, donate, sell, trash, relocate). It also lists what
   needs doing in the space (clutter, things out of place, cleaning, broken items).
3. **You decide.** Inventory rows start as suggestions. Confirm or change the disposition. Questions only you can
   answer ("keep the bread maker?") show up as decisions.
4. **Claude plans.** For a space and a goal ("garage: park the car inside again"), a `make_plan` job gets the
   inventory, the decisions, the observations and your limits (minutes per session, budget). It writes an ordered
   checklist. Each step is 10-45 minutes, names its first physical action, lists the supplies it needs and what it
   depends on. Supplies roll up into a shopping list.
5. **Do it, track it.** Check steps off, or send them to Game Plan with a date. Game Plan's done state syncs back.
   New progress/after photos plus a `review_progress` job give a written check-in, an estimated percent done, and
   any new steps.

### Who runs the Claude jobs

Jobs live in the `ai_jobs` table, and either worker can take them:
- **API worker:** when `ANTHROPIC_API_KEY` is set, a background thread in the API runs pending jobs with the Claude API.
- **Claude Code thread:** with no key, jobs wait. A Claude Code session lists them with `tools/thread_jobs.py`, looks
  at the photos itself, and posts the result in the same JSON shape. Both workers apply results with the same code.

## Layout

```
api/   FastAPI back end (serves the built UI too) + Dockerfile
ui/    Angular 20 + Material UI
tools/ upload_photos.py, thread_jobs.py (no third-party deps)
docker-compose.yml   joins the shared `homelab` network; no DB service
```

## Run on the laptop

```bash
cp .env.example .env   # fill in the DB_* keys, optionally ANTHROPIC_API_KEY and GAMEPLAN_*
docker compose up -d --build
```

UI dev server: `cd ui && npm start` (proxies `/api` to the container).
