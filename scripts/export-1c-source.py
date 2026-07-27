#!/usr/bin/env python3
"""Prepare the XML export for a tool that cannot read the EDT canon, and bring it back."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from one_c_source import (  # noqa: E402
    SourceError, accept, cli_converter, export, import_back, release, state_directory,
)

REGISTRY = "config/1c-projects.tsv"
EXPORT_RECORD = "export.json"


def read_base(root: Path, identity: str) -> dict[str, str]:
    path = root / REGISTRY
    if not path.is_file():
        raise SourceError(f"{REGISTRY} not found in {root}")
    rows = list(csv.DictReader(io.StringIO(path.read_bytes().decode("utf-8-sig")), delimiter="\t"))
    for row in rows:
        if f"{row.get('project_id')}/{row.get('environment_id')}" == identity:
            return row
    known = ", ".join(f"{row.get('project_id')}/{row.get('environment_id')}" for row in rows) or "—"
    raise SourceError(f"Base '{identity}' is not in {REGISTRY}; known bases: {known}")


def converter(command: str | None):
    """The EDT CLI, or nothing: a missing converter is a SKIP, not a failure."""
    return cli_converter(command.split()) if command else None


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--base", required=True, help="base identity as project_id/environment_id")
    parser.add_argument("--converter", default="", help="EDT CLI command for canon → XML; empty means the route is unavailable")
    parser.add_argument("--converter-back", dest="converter_back", default="",
                        help="EDT CLI command for XML → canon; the two directions are different commands")
    parser.add_argument("--import", dest="do_import", action="store_true", help="return to the canon")
    parser.add_argument("--apply", action="store_true", help="accept a reviewed return")
    parser.add_argument("--release", action="store_true", help="drop the export and the lock")
    arguments = parser.parse_args()

    root = Path(arguments.root).resolve()
    record = state_directory(root) / EXPORT_RECORD
    try:
        base = read_base(root, arguments.base)
        source = root / base["folder"]
        convert = converter(arguments.converter or None)
        convert_back = converter(arguments.converter_back or None)

        if arguments.release:
            stored = json.loads(record.read_text(encoding="utf-8")) if record.is_file() else {}
            release(root, Path(stored["export"]) if stored.get("export") else None)
            record.unlink(missing_ok=True)
            print("[RELEASE  ] выгрузка и блокировка удалены")
            return 0

        if arguments.do_import:
            stored = json.loads(record.read_text(encoding="utf-8")) if record.is_file() else {}
            if not stored.get("export"):
                raise SourceError("There is no export to return from")
            result = import_back(root, source, Path(stored["export"]), convert_back)
            print(f"[{result['action'].upper():9}] {result['reason'] or arguments.base}")
            if result["action"] != "review":
                return 0
            print(result["diff"])
            if not arguments.apply:
                print("Изменения не применены. Показать пользователю и повторить с --apply.")
                return 1
            accept(source, result["staging"])
            print("[APPLIED  ] канон обновлён")
            return 0

        result = export(root, source, base["source_format"], convert)
        if result["action"] == "skip":
            print(f"[SKIP     ] {result['reason']}")
            return 0
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"export": str(result["export"]), "base": arguments.base}), encoding="utf-8")
        print(f"[EXPORT   ] {result['export']}")
        return 0
    except SourceError as error:
        print(f"[ERROR    ] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
