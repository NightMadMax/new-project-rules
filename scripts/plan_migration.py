#!/usr/bin/env python3
"""Read-only migration planner for projects and global agent policy."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import sync_global_agents as agent_sync
import project_metadata


MIN_PYTHON = (3, 9)
PROFILE_RANKS = {"minimal": 0, "software": 1, "operated": 2, "all": 3}
MIGRATION_FIELDS = ("migration_id", "target", "from_schema", "to_schema", "handler", "description")
PROFILE_FIELDS = ("minimum_profile", "source", "destination", "root_purpose", "docs_section", "docs_label")
KNOWN_HANDLERS = {"project_metadata", "global_managed_block"}


class MigrationConfigError(Exception):
    pass


@dataclass(frozen=True)
class Migration:
    migration_id: str
    target: str
    from_schema: int
    to_schema: int
    handler: str
    description: str


@dataclass(frozen=True)
class GitState:
    available: bool
    repository: bool
    clean: bool
    commit: Optional[str]
    detail: str = ""


@dataclass(frozen=True)
class MigrationPlan:
    target: str
    status: str
    migration_id: Optional[str]
    summary: str
    changes: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    preview: str = ""


def read_standard_version(contract_root: Path) -> int:
    try:
        raw = (contract_root / "STANDARD_VERSION").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise MigrationConfigError(f"Cannot read STANDARD_VERSION: {exc}") from exc
    if not re.fullmatch(r"[1-9][0-9]*", raw):
        raise MigrationConfigError("STANDARD_VERSION must be a positive integer")
    return int(raw)


def read_migrations(contract_root: Path, standard_version: int) -> list[Migration]:
    path = contract_root / "config" / "migrations.tsv"
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if tuple(reader.fieldnames or ()) != MIGRATION_FIELDS:
                raise MigrationConfigError(f"Unexpected migrations.tsv header: {path}")
            raw_rows = list(reader)
    except OSError as exc:
        raise MigrationConfigError(f"Cannot read migration manifest: {exc}") from exc

    rows: list[Migration] = []
    seen: set[str] = set()
    for raw in raw_rows:
        migration_id = raw["migration_id"]
        if not re.fullmatch(r"[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*", migration_id):
            raise MigrationConfigError(f"Invalid migration_id: {migration_id!r}")
        if migration_id in seen:
            raise MigrationConfigError(f"Duplicate migration_id: {migration_id}")
        seen.add(migration_id)
        if raw["target"] not in {"project", "global"}:
            raise MigrationConfigError(f"Invalid migration target: {raw['target']!r}")
        if raw["handler"] not in KNOWN_HANDLERS:
            raise MigrationConfigError(f"Unknown migration handler: {raw['handler']!r}")
        try:
            from_schema = int(raw["from_schema"])
            to_schema = int(raw["to_schema"])
        except ValueError as exc:
            raise MigrationConfigError(f"Migration schemas must be integers: {migration_id}") from exc
        if from_schema < 0 or to_schema <= from_schema or to_schema > standard_version:
            raise MigrationConfigError(f"Invalid schema transition for {migration_id}")
        rows.append(Migration(migration_id, raw["target"], from_schema, to_schema, raw["handler"], raw["description"]))
    return rows


def find_migration(rows: Sequence[Migration], target: str, from_schema: int, to_schema: int) -> Migration:
    matches = [row for row in rows if row.target == target and row.from_schema == from_schema and row.to_schema == to_schema]
    if len(matches) != 1:
        raise MigrationConfigError(f"Expected exactly one {target} migration {from_schema}->{to_schema}")
    return matches[0]


def read_profile_destinations(contract_root: Path) -> dict[str, set[str]]:
    path = contract_root / "config" / "profiles.tsv"
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if tuple(reader.fieldnames or ()) != PROFILE_FIELDS:
                raise MigrationConfigError(f"Unexpected profiles.tsv header: {path}")
            rows = list(reader)
    except OSError as exc:
        raise MigrationConfigError(f"Cannot read profile manifest: {exc}") from exc
    result: dict[str, set[str]] = {}
    for profile, rank in PROFILE_RANKS.items():
        selected: set[str] = set()
        for row in rows:
            minimum = row["minimum_profile"]
            if minimum not in PROFILE_RANKS:
                raise MigrationConfigError(f"Unknown minimum_profile: {minimum!r}")
            if PROFILE_RANKS[minimum] <= rank:
                selected.add(row["destination"])
        result[profile] = selected
    return result


def inspect_git(path: Path) -> GitState:
    git = shutil.which("git")
    if not git:
        return GitState(False, False, False, None, "Git is unavailable")
    top = subprocess.run([git, "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != path.resolve():
        return GitState(True, False, False, None, "Target is not a Git repository root")
    status = subprocess.run([git, "-C", str(path), "status", "--porcelain"], capture_output=True, text=True)
    head = subprocess.run([git, "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
    if status.returncode != 0 or head.returncode != 0:
        return GitState(True, True, False, None, "Cannot inspect Git status or HEAD")
    commit = head.stdout.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        return GitState(True, True, False, None, "Git HEAD is not a full commit ID")
    clean = not status.stdout.strip()
    return GitState(True, True, clean, commit.lower(), "" if clean else "Git working tree is not clean")


def infer_profile(project_root: Path, profiles: dict[str, set[str]], requested: str) -> tuple[Optional[str], list[str]]:
    known = set().union(*profiles.values())
    present = {item for item in known if (project_root / item).is_file()}
    if requested != "auto":
        missing = sorted(profiles[requested] - present)
        extra = sorted(present - profiles[requested])
        blockers = []
        if missing:
            blockers.append(f"Profile {requested} is missing managed artifacts: {', '.join(missing)}")
        if extra:
            blockers.append(f"Profile {requested} conflicts with higher-profile artifacts: {', '.join(extra)}")
        return requested, blockers
    matches = [profile for profile, expected in profiles.items() if expected == present]
    if len(matches) != 1:
        return None, ["Cannot infer one exact profile; pass --profile after reviewing managed artifacts"]
    return matches[0], []


def project_plan(project_root: Path, contract_root: Path, profile_arg: str, migrations: Sequence[Migration], version: int) -> MigrationPlan:
    if not project_root.is_dir():
        return MigrationPlan("project", "blocked", None, "Project migration cannot be planned.", blockers=("Project root is not a directory",))
    metadata_path = project_root / ".project-standard.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return MigrationPlan("project", "blocked", None, "Existing project metadata is invalid.", blockers=(str(exc),))
        try:
            source = (contract_root / "config" / "standard-source.txt").read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise MigrationConfigError(f"Cannot read standard source: {exc}") from exc
        known_project = [row.migration_id for row in migrations if row.target == "project"]
        issues = project_metadata.validate_metadata(metadata, version, source, known_project)
        if not issues:
            return MigrationPlan("project", "up_to_date", None, "Project already uses the current standard schema.")
        return MigrationPlan("project", "blocked", None, "Existing project metadata is not valid for the current schema.", blockers=tuple(issues))

    migration = find_migration(migrations, "project", 0, version)
    profiles = read_profile_destinations(contract_root)
    profile, blockers = infer_profile(project_root, profiles, profile_arg)
    project_git = inspect_git(project_root)
    contract_git = inspect_git(contract_root)
    if not project_git.repository or not project_git.clean:
        blockers.append(project_git.detail or "Project Git state is not ready")
    if not contract_git.repository or not contract_git.clean or not contract_git.commit:
        blockers.append(contract_git.detail or "Rules repository must be clean and committed")
    try:
        source = (contract_root / "config" / "standard-source.txt").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise MigrationConfigError(f"Cannot read standard source: {exc}") from exc
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source):
        raise MigrationConfigError("config/standard-source.txt must contain owner/repository")
    if profile is None or contract_git.commit is None:
        preview = ""
    else:
        metadata = project_metadata.build_legacy_metadata(
            version, profile, source, contract_git.commit, migration.migration_id
        )
        preview = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    status = "blocked" if blockers else "ready"
    return MigrationPlan(
        "project", status, migration.migration_id,
        "Create explicit metadata for a legacy project without changing project content.",
        changes=("create .project-standard.json",), blockers=tuple(blockers), preview=preview,
    )


def global_plan(home: Path, contract_root: Path, migrations: Sequence[Migration], version: int) -> MigrationPlan:
    migration = find_migration(migrations, "global", 0, version)
    state = agent_sync.inspect_sync_state(
        contract_root / "GLOBAL_AGENT_INSTRUCTIONS.md", home / ".codex" / "AGENTS.md", version
    )
    contract_git = inspect_git(contract_root)
    blockers: list[str] = []
    if state.status == "managed_match":
        return MigrationPlan("global", "up_to_date", None, "Global policy already uses the current managed schema.")
    if state.status not in {"legacy_exact", "missing"}:
        blockers.append(f"Global sync state {state.status} does not permit automatic ownership adoption")
    if not contract_git.repository or not contract_git.clean:
        blockers.append(contract_git.detail or "Rules repository must be clean and committed")
    if state.status == "missing":
        changes = ("create managed policy file",)
    elif state.status == "legacy_exact":
        changes = ("wrap matching policy in schema=1 managed markers", "create timestamped backup before future apply")
    else:
        changes = ()
    return MigrationPlan(
        "global", "blocked" if blockers else "ready", migration.migration_id,
        "Adopt managed ownership without exposing active policy content.",
        changes=changes, blockers=tuple(blockers), preview=agent_sync.secret_safe_diff(state),
    )


def format_plan(plan: MigrationPlan) -> str:
    output = [f"target={plan.target}", f"status={plan.status}"]
    if plan.migration_id:
        output.append(f"migration={plan.migration_id}")
    output.append(plan.summary)
    for change in plan.changes:
        output.append(f"CHANGE: {change}")
    for blocker in plan.blockers:
        output.append(f"BLOCKER: {blocker}")
    if plan.preview:
        output.append("PREVIEW:")
        output.append(plan.preview.rstrip("\n"))
    output.append("No files were changed.")
    return "\n".join(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan project-standard migrations without changing files.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="Produce a read-only migration plan.")
    parser.add_argument("--target", choices=("project", "global"), required=True)
    parser.add_argument("--root", default=".", help="Project root for target=project.")
    parser.add_argument("--home", default=str(Path.home()), help="Home directory for target=global.")
    parser.add_argument("--profile", choices=("auto", *PROFILE_RANKS), default="auto")
    parser.add_argument("--contract-root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--report-only", action="store_true", help="Always return 0 after reporting.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if sys.version_info < MIN_PYTHON:
        print("Python 3.9+ is required.", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    contract_root = Path(args.contract_root).resolve()
    try:
        version = read_standard_version(contract_root)
        migrations = read_migrations(contract_root, version)
        if args.target == "project":
            plan = project_plan(Path(args.root).resolve(), contract_root, args.profile, migrations, version)
        else:
            plan = global_plan(Path(args.home).resolve(), contract_root, migrations, version)
    except (MigrationConfigError, agent_sync.SyncConfigError) as exc:
        print(f"Migration configuration error: {exc}", file=sys.stderr)
        return 0 if args.report_only else 2
    print(format_plan(plan))
    if args.report_only:
        return 0
    return 1 if plan.status == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
