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

```bash
python tools/thread_jobs.py list --status pending
python tools/thread_jobs.py claim          # saves the photos, prints instructions, context and the answer schema
python tools/thread_jobs.py submit 12 answer.json
```

A wrong-shaped answer is refused with the validation error, so nothing is half-applied.

### Other tools

Photos are also queued for any other tool that wants to look at them: image tagging, face clustering,
sensitivity scanning, OCR, and so on.

- `GET /api/photos/feed?missing_tool=<name>` lists photos that tool hasn't evaluated yet (also `since=`, `limit=`).
- `GET /api/photos/{id}/file?size=full|claude|thumb` returns the image.
- `PUT /api/photos/{id}/evaluations` with `{"tool": "<name>", "version": "...", "result": {...}}` stores the result.
  There is one result per tool per photo, and a re-run replaces it. The dashboard shows them under the photo.

### Game Plan

`GAMEPLAN_API_URL` points at the Game Plan API. "Send to Game Plan" creates one Game Plan task per step, filling
days in checklist order up to a minutes-per-day budget. The note carries the first step, the supplies and the
step id. "Sync" marks steps done once they're done in Game Plan, and follows any date moves made there.

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

UI dev server: `cd ui && npm start` (port 4370, proxies `/api` to the container).

Tests and lint (in Docker, Python 3.12):

```bash
docker build -f api/Dockerfile --target test -t home-organization-test . && docker run --rm home-organization-test
```

After an API change: `python api/export_openapi.py > api/openapi.json` (in the test image), then
`cd ui && npm run api-types` to regenerate the TypeScript types.

Photos and the database are personal data. They live on the host (`PHOTO_HOST_DIR`) and in Postgres, never in this
repo.
