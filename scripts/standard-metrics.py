#!/usr/bin/env python3
"""Record and report product metrics for standardized consumer projects."""
from __future__ import annotations
import argparse
import json
from datetime import date
from pathlib import Path

RELATIVE_LOG = Path("docs/quality/STANDARD_ADOPTION.json")

def load(project: Path) -> dict:
    path = project / RELATIVE_LOG
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid standard adoption log: {path}") from exc
    if (not isinstance(data, dict) or data.get("schema_version") != 1 or
            not isinstance(data.get("created_at"), str) or
            not isinstance(data.get("interventions"), list)):
        raise ValueError(f"invalid standard adoption log: {path}")
    return data

def write(project: Path, data: dict) -> None:
    (project / RELATIVE_LOG).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", action="append", type=Path, required=True)
    parser.add_argument("--record-first-green", action="store_true")
    parser.add_argument("--self-service", choices=("true", "false"))
    parser.add_argument("--record-intervention")
    args = parser.parse_args()
    if (args.record_first_green and args.record_intervention) or (args.self_service and not args.record_first_green):
        parser.error("record exactly one event; --self-service requires --record-first-green")
    if args.record_intervention is not None and not args.record_intervention.strip():
        parser.error("intervention reason must not be blank")
    reports = []
    for project in args.project:
        project = project.resolve()
        data = load(project)
        if args.record_first_green:
            if data.get("first_green_at") is not None:
                raise ValueError(f"first green already recorded: {project / RELATIVE_LOG}")
            data["first_green_at"] = date.today().isoformat()
            data["first_green_self_service"] = args.self_service == "true"
            write(project, data)
        elif args.record_intervention:
            data["interventions"].append({"recorded_at": date.today().isoformat(), "reason": args.record_intervention})
            write(project, data)
        reports.append({"project": str(project), "created_at": data["created_at"], "first_green_at": data.get("first_green_at"), "self_service": data.get("first_green_self_service"), "manual_interventions": len(data["interventions"])})
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
