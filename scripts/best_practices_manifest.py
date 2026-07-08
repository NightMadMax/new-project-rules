#!/usr/bin/env python3
"""Create or update schema-2 Best Practices consumer preferences."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional, Sequence


MANIFEST_NAME = ".best-practices.json"
PREFERENCE_VALUES = ("ask", "optout")
ALLOWED_SECTIONS = {
    "1c", "web", "backend", "mobile", "desktop", "data-ml", "data-analysis",
    "excel-research", "powerbi", "jira-confluence", "devops", "embedded",
    "common", "tools", "anti-patterns", "prompts", "snippets",
}


def empty_manifest() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "preferences": {"global": "ask", "sections": {}},
        "practices": {},
    }


def load_manifest(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"{MANIFEST_NAME} must not be a symlink")
    if not path.exists():
        return empty_manifest()
    if not path.is_file():
        raise ValueError(f"{MANIFEST_NAME} must be a regular file")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{MANIFEST_NAME} must be valid UTF-8 JSON") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 2:
        raise ValueError("existing consumer manifest must use schema_version 2; migrate it first")
    if set(data) != {"schema_version", "preferences", "practices"}:
        raise ValueError("schema 2 consumer manifest has unknown or missing top-level fields")
    preferences = data.get("preferences")
    practices = data.get("practices")
    if not isinstance(preferences, dict) or set(preferences) != {"global", "sections"}:
        raise ValueError("preferences must contain exactly global and sections")
    if preferences.get("global") not in PREFERENCE_VALUES or not isinstance(preferences.get("sections"), dict):
        raise ValueError("preferences contain invalid values")
    if any(not isinstance(key, str) or value not in PREFERENCE_VALUES for key, value in preferences["sections"].items()):
        raise ValueError("section preferences must map section names to ask or optout")
    if not isinstance(practices, dict):
        raise ValueError("practices must be an object")
    return data


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    content = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def update_preference(project: Path, *, global_value: Optional[str], section: Optional[str], section_value: Optional[str]) -> Path:
    project = project.resolve()
    if not project.is_dir():
        raise ValueError("project must be an existing directory")
    path = project / MANIFEST_NAME
    data = load_manifest(path)
    if global_value is not None:
        data["preferences"]["global"] = global_value
    if section is not None:
        if section not in ALLOWED_SECTIONS:
            raise ValueError(f"unsupported Best Practices section: {section}")
        data["preferences"]["sections"][section] = section_value
    atomic_write(path, data)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--set-global", choices=PREFERENCE_VALUES)
    parser.add_argument("--set-section", nargs=2, metavar=("SECTION", "PREFERENCE"))
    parser.add_argument(
        "--stack",
        action="append",
        metavar="SECTION",
        help="mark a project stack as used (records section preference 'ask'); repeatable",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not (args.set_global or args.set_section or args.stack):
        print("nothing to do: provide --set-global, --set-section or --stack", file=sys.stderr)
        return 2
    section = None
    section_value = None
    if args.set_section:
        section, section_value = args.set_section
        if section_value not in PREFERENCE_VALUES:
            print("section preference must be ask or optout", file=sys.stderr)
            return 2
    try:
        path = None
        if args.set_global is not None or section is not None:
            path = update_preference(
                args.project,
                global_value=args.set_global,
                section=section,
                section_value=section_value,
            )
        for stack in args.stack or []:
            path = update_preference(
                args.project,
                global_value=None,
                section=stack,
                section_value="ask",
            )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"updated={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
