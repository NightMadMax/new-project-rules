#!/usr/bin/env python3
"""Create and validate one-file-per-item promotion candidates."""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from datetime import date
from pathlib import Path
from typing import Optional, Sequence


ID_RE = re.compile(r"^PC-(\d{4})-([0-9a-f]{12}|\d{3})$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_STATUSES = {"new", "triaged", "approved", "implemented", "rejected"}
ALLOWED_ARTIFACT_TYPES = {"rule", "template", "test", "validator", "script", "skill", "guide"}
REQUIRED_FIELDS = (
    "type", "id", "status", "source", "observation", "generalized_lesson", "scope",
    "evidence", "artifact_type", "proposed_target", "created", "last_verified",
)


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("frontmatter must start with ---")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("frontmatter is not closed") from exc
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if not match:
            raise ValueError(f"unsupported frontmatter line: {line}")
        key, raw = match.groups()
        if key in fields:
            raise ValueError(f"duplicate field: {key}")
        try:
            value = json.loads(raw) if raw.startswith('"') else raw
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON string for {key}") from exc
        fields[key] = str(value).strip()
    return fields


def candidate_files(root: Path) -> list[Path]:
    directory = root / "docs" / "quality" / "promotion-candidates"
    return sorted(path for path in directory.glob("PC-*.md") if path.is_file())


def validate_candidates(root: Path) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []
    seen: dict[str, Path] = {}
    for path in candidate_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            fields = parse_frontmatter(path)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            issues.append((rel, str(exc)))
            continue
        for field in REQUIRED_FIELDS:
            if not fields.get(field):
                issues.append((rel, f"missing required field: {field}"))
        if fields.get("type") != "promotion-candidate":
            issues.append((rel, f"invalid type: {fields.get('type', '')}"))
        candidate_id = fields.get("id", "")
        if not ID_RE.fullmatch(candidate_id):
            issues.append((rel, f"invalid candidate id: {candidate_id}"))
        elif candidate_id in seen:
            issues.append((rel, f"duplicate candidate id also used by {seen[candidate_id].name}"))
        else:
            seen[candidate_id] = path
        if candidate_id and not path.name.startswith(f"{candidate_id}-"):
            issues.append((rel, "filename must start with candidate id and a slug"))
        slug = path.stem[len(candidate_id) + 1:] if candidate_id and path.stem.startswith(f"{candidate_id}-") else ""
        if not SLUG_RE.fullmatch(slug):
            issues.append((rel, f"invalid filename slug: {slug}"))
        if fields.get("status") not in ALLOWED_STATUSES:
            issues.append((rel, f"invalid status: {fields.get('status', '')}"))
        if fields.get("artifact_type") not in ALLOWED_ARTIFACT_TYPES:
            issues.append((rel, f"invalid artifact_type: {fields.get('artifact_type', '')}"))
        for field in ("created", "last_verified"):
            if fields.get(field) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields[field]):
                issues.append((rel, f"{field} must use YYYY-MM-DD"))
        if fields.get("status") == "implemented" and not fields.get("implemented_commit"):
            issues.append((rel, "implemented candidate requires implemented_commit"))
    return issues


def new_id(root: Path, year: int) -> str:
    existing = {parse_frontmatter(path).get("id", "") for path in candidate_files(root)}
    for _ in range(100):
        candidate_id = f"PC-{year}-{secrets.token_hex(6)}"
        if candidate_id not in existing:
            return candidate_id
    raise RuntimeError("could not allocate a unique candidate id")


def quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def create_candidate(root: Path, args: argparse.Namespace) -> Path:
    candidate_id = new_id(root, args.year)
    path = root / "docs" / "quality" / "promotion-candidates" / f"{candidate_id}-{args.slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f'''---
type: promotion-candidate
id: {candidate_id}
status: new
source: {quoted(args.source)}
observation: {quoted(args.observation)}
generalized_lesson: {quoted(args.generalized_lesson)}
scope: {quoted(args.scope)}
evidence: {quoted(args.evidence)}
artifact_type: {args.artifact_type}
proposed_target: {quoted(args.proposed_target)}
created: {args.created}
last_verified: {args.created}
---

# {args.title}

## Notes

Добавьте границы применимости и результат review без приватного контекста.
'''
    path.write_text(content, encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    create = subparsers.add_parser("create")
    create.add_argument("--slug", required=True)
    create.add_argument("--title", required=True)
    for field in ("source", "observation", "generalized-lesson", "scope", "evidence", "proposed-target"):
        create.add_argument(f"--{field}", required=True)
    create.add_argument("--artifact-type", required=True, choices=sorted(ALLOWED_ARTIFACT_TYPES))
    create.add_argument("--year", type=int, default=date.today().year)
    create.add_argument("--created", default=date.today().isoformat())
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    if args.command == "validate":
        issues = validate_candidates(root)
        for path, message in issues:
            print(f"ERROR {path}: {message}")
        print(f"Promotion candidates: {len(candidate_files(root))} file(s), {len(issues)} issue(s).")
        return 1 if issues else 0
    if not SLUG_RE.fullmatch(args.slug):
        print("--slug must use lowercase kebab-case", file=sys.stderr)
        return 2
    path = create_candidate(root, args)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
