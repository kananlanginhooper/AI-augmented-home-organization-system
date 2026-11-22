"""Upload photos (files or whole folders) to the home organization API.

    python tools/upload_photos.py <file-or-folder>... [--space "Garage/Back wall"] [--phase before] [--caption ...]
                                  [--source folder] [--no-analyze] [--move-to <folder>]

Standard library only. HOME_ORG_URL picks the API (default http://localhost:8109).
--move-to moves each uploaded file out of an inbox folder so it isn't sent twice.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import shutil
import sys
import urllib.request
import uuid
from pathlib import Path

EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff", ".bmp"}


def files_in(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(f for f in p.rglob("*") if f.suffix.lower() in EXTENSIONS))
        elif p.is_file():
            out.append(p)
        else:
            print(f"skip: {p} not found", file=sys.stderr)
    return out


def post(url: str, fields: dict[str, str], file: Path) -> dict:
    boundary = uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
    ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    body += (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file.name}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode()
    body += file.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=bytes(body), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--space", help='space name or path, e.g. "Garage/Back wall" (created if missing)')
    ap.add_argument("--phase", default="before", choices=["before", "progress", "after", "reference"])
    ap.add_argument("--caption")
    ap.add_argument("--source", default="folder", choices=["dashboard", "thread", "folder"])
    ap.add_argument("--no-analyze", action="store_true", help="don't queue a Claude analysis")
    ap.add_argument("--move-to", help="move each uploaded file into this folder")
    args = ap.parse_args()

    base = os.environ.get("HOME_ORG_URL", "http://localhost:8109").rstrip("/")
    fields = {"phase": args.phase, "source": args.source, "analyze": "false" if args.no_analyze else "true"}
    if args.space:
        fields["space"] = args.space
    if args.caption:
        fields["caption"] = args.caption

    done = 0
    for f in files_in(args.paths):
        try:
            res = post(f"{base}/api/photos", fields, f)
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {f}: {e}", file=sys.stderr)
            continue
        photo = res["photo"]
        print(f"{'duplicate' if res['duplicate'] else 'uploaded '} photo {photo['id']}  {f.name}")
        done += 1
        if args.move_to:
            dest = Path(args.move_to)
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), dest / f.name)
    print(f"{done} file(s) sent to {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
