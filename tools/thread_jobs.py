"""Work the Claude job queue from a Claude Code session (no API key needed).

    python tools/thread_jobs.py list [--status pending]
    python tools/thread_jobs.py claim [JOB_ID]     # claims the oldest (or that) job, saves its photos, prints the brief
    python tools/thread_jobs.py submit JOB_ID RESULT.json
    python tools/thread_jobs.py retry JOB_ID

`claim` prints the instructions, the context, the photo files to look at, and the JSON schema the answer must match.
The session looks at the photos, writes the answer to a JSON file and runs `submit`. The API validates it against
the same schema the API worker uses, so a bad answer is refused instead of half-applied.

Standard library only. HOME_ORG_URL picks the API (default http://127.0.0.1:8109; localhost stalls on Windows while IPv6 is tried first);
photos are saved under HOME_ORG_JOB_DIR (default: the system temp folder).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ.get("HOME_ORG_URL", "http://127.0.0.1:8109").rstrip("/")
JOB_DIR = Path(os.environ.get("HOME_ORG_JOB_DIR", Path(tempfile.gettempdir()) / "home-org-jobs"))


def call(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path}: {e.code} {e.read().decode(errors='replace')}")


def show(ctx: dict) -> None:
    job = ctx["job"]
    folder = JOB_DIR / f"job-{job['id']}"
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for pid in ctx["photo_ids"]:
        dest = folder / f"photo-{pid}.jpg"
        with urllib.request.urlopen(f"{BASE}/api/photos/{pid}/file?size=claude", timeout=60) as r:
            dest.write_bytes(r.read())
        files.append(str(dest))
    print(f"JOB {job['id']}  {job['kind']}  (target {job['target_id']})\n")
    print("== INSTRUCTIONS ==\n" + ctx["instructions"] + "\n")
    print("== CONTEXT ==\n" + ctx["context"] + "\n")
    print("== PHOTOS (look at each) ==\n" + ("\n".join(files) or "(none)") + "\n")
    print("== ANSWER SCHEMA ==\n" + json.dumps(ctx["result_schema"], indent=1))
    print(f"\nWrite the answer JSON, then: python tools/thread_jobs.py submit {job['id']} <file.json>")


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "list":
        status = rest[1] if len(rest) == 2 and rest[0] == "--status" else ""
        for j in call("GET", f"/api/ai/jobs?status={status}" if status else "/api/ai/jobs"):
            print(f"{j['id']:>5}  {j['status']:<8} {j['kind']:<16} target {j['target_id']:<5} {j['worker'] or ''} {j['error'] or ''}")
    elif cmd == "claim":
        if rest:
            ctx = call("GET", f"/api/ai/jobs/{rest[0]}/context")
        else:
            ctx = call("POST", "/api/ai/jobs/claim")
        show(ctx)
    elif cmd == "submit" and len(rest) == 2:
        result = json.loads(Path(rest[1]).read_text(encoding="utf-8"))
        job = call("POST", f"/api/ai/jobs/{rest[0]}/result", {"result": result})
        print(f"job {job['id']}: {job['status']}")
    elif cmd == "retry" and rest:
        job = call("POST", f"/api/ai/jobs/{rest[0]}/retry")
        print(f"job {job['id']}: {job['status']}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
