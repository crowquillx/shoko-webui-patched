#!/usr/bin/env python3
"""Validate the published version embedded in a WebUI build artifact."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

APP_VERSION = re.compile(
    r"VITE_APPVERSION\s*:\s*(?P<quote>[\"'`])(?P<version>[^\"'`]+)(?P=quote)"
)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_directory_artifact(artifact: Path) -> tuple[bytes, list[tuple[str, bytes]]]:
    version_path = artifact / "version.json"
    if not version_path.is_file():
        fail(f"missing {version_path}")
    assets_dir = artifact / "assets"
    if not assets_dir.is_dir():
        fail(f"missing {assets_dir}")
    assets = [
        (path.relative_to(artifact).as_posix(), path.read_bytes())
        for path in sorted(assets_dir.rglob("*.js"))
        if path.is_file()
    ]
    return version_path.read_bytes(), assets


def read_zip_artifact(artifact: Path) -> tuple[bytes, list[tuple[str, bytes]]]:
    try:
        archive = zipfile.ZipFile(artifact)
    except (OSError, zipfile.BadZipFile) as error:
        fail(f"cannot read {artifact}: {error}")

    with archive:
        names = set(archive.namelist())
        if "version.json" not in names:
            fail(f"{artifact} does not contain version.json")
        assets = [
            (name, archive.read(name))
            for name in sorted(names)
            if name.startswith("assets/") and name.endswith(".js")
        ]
        return archive.read("version.json"), assets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path, help="a WebUI dist directory or flat ZIP archive")
    parser.add_argument("--version", required=True, help="the exact published WebUI version")
    args = parser.parse_args()

    if not args.version:
        fail("published version must not be empty")
    if args.artifact.is_dir():
        version_bytes, assets = read_directory_artifact(args.artifact)
    elif args.artifact.is_file():
        version_bytes, assets = read_zip_artifact(args.artifact)
    else:
        fail(f"artifact does not exist: {args.artifact}")

    try:
        version_document = json.loads(version_bytes)
    except json.JSONDecodeError as error:
        fail(f"version.json is not valid JSON: {error}")
    if not isinstance(version_document, dict):
        fail("version.json root must be an object")
    package_version = version_document.get("package")
    if package_version != args.version:
        fail(
            f"version.json package is {package_version!r}, expected {args.version!r}"
        )

    embedded_versions = {
        match.group("version")
        for _, asset in assets
        for match in APP_VERSION.finditer(asset.decode("utf-8", errors="strict"))
    }
    if not embedded_versions:
        fail("no VITE_APPVERSION value found in the production assets")
    if embedded_versions != {args.version}:
        found = ", ".join(sorted(repr(version) for version in embedded_versions))
        fail(f"bundled production asset version is {found}, expected {args.version!r}")

    print(f"valid: {args.artifact} ({args.version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
