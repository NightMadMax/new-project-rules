#!/usr/bin/env python3
"""Prepare the XML export for a tool that cannot read the EDT canon, and bring it back."""

from __future__ import annotations

import argparse
import csv
import io
import json
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from one_c_source import (  # noqa: E402
    FINGERPRINT_NAME, SourceError, accept, cli_converter, export, fingerprint, import_back,
    release, state_directory,
)

REGISTRY = "config/1c-projects.tsv"
RECORD = "export.json"


def read_base(root: Path, identity: str) -> dict[str, str]:
    path = root / REGISTRY
    if not path.is_file():
        raise SourceError(f"{REGISTRY} not found in {root}")
    rows = list(csv.DictReader(io.StringIO(path.read_bytes().decode("utf-8-sig")), delimiter="\t", quoting=csv.QUOTE_NONE))
    for row in rows:
        if f"{row.get('project_id')}/{row.get('environment_id')}" == identity:
            return row
    known = ", ".join(f"{row.get('project_id')}/{row.get('environment_id')}" for row in rows) or "—"
    raise SourceError(f"Base '{identity}' is not in {REGISTRY}; known bases: {known}")


def converter(command: str, source_option: str, target_option: str):
    """The converter, or nothing: a missing one is a SKIP, not a failure."""
    if not command:
        return None
    # Not str.split: the usual path on Windows holds spaces. Not POSIX mode
    # either: it would eat the backslashes in that same path — so quotes are
    # removed by hand instead.
    tokens = [token[1:-1] if len(token) > 1 and token[0] == token[-1] in '"\'' else token
              for token in shlex.split(command, posix=False)]
    return cli_converter(tokens, source_option, target_option)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--base", required=True, help="base identity as project_id/environment_id")
    parser.add_argument("--converter", default="", help="command converting the canon to XML")
    parser.add_argument("--converter-back", dest="converter_back", default="",
                        help="command converting XML back; the two directions are different commands")
    parser.add_argument("--source-option", default="--source", help="how the converter names its input")
    parser.add_argument("--target-option", default="--target", help="how the converter names its output")
    # The real converter names the same directory differently depending on which
    # way it is going: 1cedtcli exports with --project into --configuration-files
    # and imports with --configuration-files into --project. One pair of names
    # for both directions cannot express that, and the return would silently be
    # given the export's flags (defect 166).
    parser.add_argument("--back-source-option", default="",
                        help="how the return names its input; defaults to --source-option")
    parser.add_argument("--back-target-option", default="",
                        help="how the return names its output; defaults to --target-option")
    parser.add_argument("--skip-determinism-check", action="store_true",
                        help="do not convert twice; halves the cost and drops the guarantee")
    parser.add_argument("--import", dest="do_import", action="store_true", help="return to the canon")
    parser.add_argument("--apply", action="store_true", help="accept the review that was shown")
    parser.add_argument("--release", action="store_true", help="drop the export, the staging and the lock")
    arguments = parser.parse_args()

    root = Path(arguments.root).resolve()
    try:
        base = read_base(root, arguments.base)
        if not base.get("folder") or not base.get("source_format"):
            raise SourceError(f"{REGISTRY} has no folder or source_format for '{arguments.base}'")
        source = root / base["folder"]
        record = state_directory(root, arguments.base) / RECORD

        # Release first, and without reading the record: it is the way out of a
        # broken state, so it must not depend on that state being readable.
        if arguments.release:
            release(root, arguments.base)
            print("[RELEASE  ] выгрузка, staging и блокировка удалены")
            return 0

        try:
            stored = json.loads(record.read_text(encoding="utf-8")) if record.is_file() else {}
        except (OSError, ValueError):
            raise SourceError(f"The export record {record} is unreadable; run --release and start over") from None
        if not isinstance(stored, dict):
            raise SourceError(f"The export record {record} is not an object; run --release and start over")

        if arguments.apply and not arguments.do_import:
            # Applying what was shown, not what a fresh conversion would produce.
            if not stored.get("staging"):
                raise SourceError("There is no reviewed return to apply; run --import first")
            # A conversation happens between --import and --apply, and the canon
            # can move during it. Checking only at --import would put the very
            # overwrite this contract forbids one step to the right.
            recorded = state_directory(root, arguments.base) / FINGERPRINT_NAME
            if not recorded.is_file() or recorded.read_text(encoding="utf-8").strip() != fingerprint(source):
                raise SourceError(
                    "The canon changed after the review; redo the export — "
                    "applying now would overwrite work done meanwhile"
                )
            accept(root, source, Path(stored["staging"]))
            stored.pop("staging", None)
            record.write_text(json.dumps(stored), encoding="utf-8")
            print("[APPLIED  ] канон обновлён")
            return 0

        if arguments.do_import:
            if not stored.get("export"):
                raise SourceError("There is no export to return from")
            result = import_back(
                root, arguments.base, source, Path(stored["export"]),
                converter(arguments.converter_back,
                          arguments.back_source_option or arguments.source_option,
                          arguments.back_target_option or arguments.target_option),
            )
            print(f"[{result['action'].upper():9}] {result['reason'] or arguments.base}")
            if result["action"] != "review":
                return 0
            print(result["diff"])
            stored["staging"] = str(result["staging"])
            record.write_text(json.dumps(stored), encoding="utf-8")
            if not arguments.apply:
                print("Изменения не применены. Показать пользователю и повторить с --apply.")
                return 1
            accept(root, source, Path(stored["staging"]))
            stored.pop("staging", None)
            record.write_text(json.dumps(stored), encoding="utf-8")
            print("[APPLIED  ] канон обновлён")
            return 0

        result = export(
            root, arguments.base, source, base["source_format"],
            converter(arguments.converter, arguments.source_option, arguments.target_option),
            check_determinism=not arguments.skip_determinism_check,
        )
        if result["action"] == "skip":
            print(f"[SKIP     ] {result['reason']}")
            return 0
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"export": str(result["export"]), "base": arguments.base}), encoding="utf-8")
        print(f"[EXPORT   ] {result['export']}")
        if result["reason"]:
            print(f"[WARN     ] {result['reason']}")
        return 0
    except SourceError as error:
        print(f"[ERROR    ] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
