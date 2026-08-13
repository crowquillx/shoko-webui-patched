#!/usr/bin/env python3
"""Validate a Shoko WebUI client manifest without third-party packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

VERSION = re.compile(r"^\d+(?:\.\d+){0,2}-dev\.\d+$")
SERVER_VERSION = re.compile(r"^\d+(?:\.\d+){0,3}(?:-[0-9A-Za-z.-]+)?$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
CHECKSUM = re.compile(r"^sha256:[0-9a-f]{64}$")


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()

    try:
        document = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read {args.manifest}: {error}")

    if not isinstance(document, dict):
        fail("manifest root must be an object")
    if set(document) != {"Stable", "Dev"}:
        fail("manifest root must contain only Stable and Dev")

    seen_versions: set[str] = set()
    seen_commits: set[str] = set()
    expected_host = "github.com"
    expected_prefix = f"https://github.com/{args.repository}/releases/download/"

    for channel in ("Stable", "Dev"):
        entries = document[channel]
        if not isinstance(entries, list):
            fail(f"{channel} must be an array")
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                fail(f"{channel}[{index}] must be an object")
            for field in ("version", "minServerVersion", "downloadUrl", "checksum", "releaseNotes", "commit", "tag", "date"):
                if not isinstance(entry.get(field), str) or not entry[field]:
                    fail(f"{channel}[{index}] is missing string field {field}")
            version = entry["version"]
            if not SERVER_VERSION.fullmatch(entry["minServerVersion"]):
                fail(f"{channel}[{index}] has an invalid minimum server version")
            if channel == "Dev" and not VERSION.fullmatch(version):
                fail(f"{channel}[{index}] has an invalid dev version: {version}")
            if channel == "Stable" and VERSION.fullmatch(version):
                fail(f"{channel}[{index}] has a dev version in Stable: {version}")
            if version in seen_versions:
                fail(f"duplicate version: {version}")
            seen_versions.add(version)
            if not COMMIT.fullmatch(entry["commit"]):
                fail(f"{channel}[{index}] has an invalid commit")
            if entry["commit"] in seen_commits:
                fail(f"duplicate upstream commit: {entry['commit']}")
            seen_commits.add(entry["commit"])
            if not CHECKSUM.fullmatch(entry["checksum"]):
                fail(f"{channel}[{index}] has an invalid checksum")
            parsed_url = urlparse(entry["downloadUrl"])
            if parsed_url.scheme != "https" or parsed_url.netloc != expected_host:
                fail(f"{channel}[{index}] downloadUrl must use https://github.com")
            expected_url = f"{expected_prefix}v{version}/Shoko-WebUI-v{version}.zip"
            if entry["downloadUrl"] != expected_url:
                fail(f"{channel}[{index}] downloadUrl does not match the repository and version")
            if entry["tag"] != f"v{version}":
                fail(f"{channel}[{index}] tag does not match version")
            try:
                release_date = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
            except ValueError:
                fail(f"{channel}[{index}] date is not ISO-8601")
            if release_date.tzinfo is None or release_date.utcoffset() != timezone.utc.utcoffset(release_date):
                fail(f"{channel}[{index}] date must be UTC")

    print(f"valid: {args.manifest} ({len(seen_versions)} release entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
