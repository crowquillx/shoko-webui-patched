#!/usr/bin/env python3
"""Insert one WebUI release into a Shoko client manifest."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--download-url", required=True)
    parser.add_argument("--checksum", required=True)
    parser.add_argument("--min-server-version", required=True)
    parser.add_argument("--release-notes", type=Path, required=True)
    parser.add_argument("--date", default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    parser.add_argument("--channel", choices=("Stable", "Dev"), default="Dev")
    parser.add_argument("--keep", type=int, default=30)
    args = parser.parse_args()

    if args.keep < 1:
        raise SystemExit("--keep must be at least 1")

    if args.manifest.exists():
        document = json.loads(args.manifest.read_text(encoding="utf-8"))
    else:
        document = {"Stable": [], "Dev": []}
    if not isinstance(document, dict):
        raise SystemExit("manifest root must be an object")
    for channel in ("Stable", "Dev"):
        if not isinstance(document.get(channel), list):
            raise SystemExit(f"manifest field {channel} must be an array")

    for channel in ("Stable", "Dev"):
        document[channel] = [
            item
            for item in document[channel]
            if not isinstance(item, dict)
            or (item.get("version") != args.version and item.get("commit") != args.commit)
        ]

    release_notes = args.release_notes.read_text(encoding="utf-8")
    entry = {
        "version": args.version,
        "minServerVersion": args.min_server_version,
        "downloadUrl": args.download_url,
        "checksum": args.checksum,
        "releaseNotes": release_notes,
        "commit": args.commit,
        "tag": args.tag,
        "date": args.date,
    }
    document[args.channel] = [
        entry,
        *[item for item in document[args.channel] if item.get("version") != args.version],
    ][: args.keep]

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{args.manifest.name}.",
        dir=args.manifest.parent,
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(document, output, indent=2)
            output.write("\n")
        os.replace(temporary_name, args.manifest)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
