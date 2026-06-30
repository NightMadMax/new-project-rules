#!/usr/bin/env python3
"""Planner and conservative apply for standardizing an existing project."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Sequence
import hashlib


MIN_PYTHON = (3, 9)
PROFILE_RANKS = {"minimal": 0, "software": 1, "operated": 2, "all": 3}
PROFILE_FIELDS = (
    "minimum_profile",
    "source",
    "destination",
    "root_purpose",
    "docs_section",
    "docs_label",
)
SAFE_CREATE_FILES = {
    "CLAUDE.md",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    "docs/README.md",
}
CORE_DOCS = ("README.md", "PROJECT.md", "INDEX.md", "AGENTS.md")
TRANSFER_DIRS = ("src", "app", "lib", "tests", "docs")
TRANSFER_FILES = (
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
)
MANUAL_REVIEW_PATTERNS = (
    ".github",
    ".env",
    ".env.local",
    ".env.production",
    "deploy",
    "deployment",
)


class StandardizationConfigError(Exception):
    pass


class StandardizationApplyError(Exception):
    pass


@dataclass(frozen=True)
class Artifact:
    minimum_profile: str
    source: str
    destination: str
    root_purpose: str
    docs_section: str
    docs_label: str


@dataclass(frozen=True)
class GitState:
    available: bool
    repository: bool
    clean: bool
    detail: str = ""


@dataclass(frozen=True)
class AssessmentReport:
    root: Path
    requested_strategy: str
    requested_profile: str
    status: str
    recommended_strategy: str
    candidate_profile: Optional[str]
    safe_to_adopt_in_place: bool
    safe_to_rebootstrap: bool
    blocking_issues: tuple[str, ...]
    files_to_create: tuple[str, ...]
    files_to_merge: tuple[str, ...]
    files_to_review_manually: tuple[str, ...]
    proposed_transfer_set: tuple[str, ...]
    adopt_blockers: tuple[str, ...]
    rebootstrap_blockers: tuple[str, ...]
    git_repository: bool
    clean_git_tree: bool
    nested_obsidian: bool
    conflicting_claude: bool
    exact_profiles: tuple[str, ...]
    missing_by_profile: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class FilePlan:
    path: Path
    action: str
    content: str
    existed: bool


@dataclass(frozen=True)
class ApplyPlan:
    status: str
    strategy: str
    profile: str
    summary: str
    files: tuple[FilePlan, ...]
    blockers: tuple[str, ...]
    fingerprint: str


def load_validator_module(contract_root: Path):
    path = contract_root / "scripts" / "validate-project.py"
    spec = importlib.util.spec_from_file_location("project_validator", path)
    if spec is None or spec.loader is None:
        raise StandardizationConfigError(f"Cannot load validator module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_migration_module(contract_root: Path):
    path = contract_root / "scripts" / "plan_migration.py"
    spec = importlib.util.spec_from_file_location("plan_migration_runtime", path)
    if spec is None or spec.loader is None:
        raise StandardizationConfigError(f"Cannot load migration planner from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_artifacts(contract_root: Path) -> list[Artifact]:
    path = contract_root / "config" / "profiles.tsv"
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if tuple(reader.fieldnames or ()) != PROFILE_FIELDS:
                raise StandardizationConfigError(f"Unexpected profiles.tsv header: {path}")
            rows = [Artifact(**row) for row in reader]
    except OSError as exc:
        raise StandardizationConfigError(f"Cannot read {path}: {exc}") from exc
    for row in rows:
        if row.minimum_profile not in PROFILE_RANKS:
            raise StandardizationConfigError(f"Unknown minimum_profile: {row.minimum_profile}")
    return rows


def profile_destinations(rows: Sequence[Artifact]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for profile, rank in PROFILE_RANKS.items():
        result[profile] = {
            row.destination for row in rows if PROFILE_RANKS[row.minimum_profile] <= rank
        }
    return result


def inspect_git(path: Path) -> GitState:
    git = shutil.which("git")
    if not git:
        return GitState(False, False, False, "Git is unavailable")
    top = subprocess.run([git, "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != path.resolve():
        return GitState(True, False, False, "Target is not a Git repository root")
    status = subprocess.run([git, "-C", str(path), "status", "--porcelain"], capture_output=True, text=True)
    if status.returncode != 0:
        return GitState(True, True, False, "Cannot inspect Git status")
    clean = not status.stdout.strip()
    detail = "" if clean else "Git working tree is not clean"
    return GitState(True, True, clean, detail)


def existing_managed(root: Path, known: set[str]) -> set[str]:
    return {destination for destination in known if (root / destination).exists()}


def detect_candidate_profile(
    present: set[str],
    destinations: dict[str, set[str]],
    requested: str,
) -> tuple[Optional[str], tuple[str, ...], dict[str, tuple[str, ...]], tuple[str, ...]]:
    missing_by_profile = {
        profile: tuple(sorted(expected - present))
        for profile, expected in destinations.items()
    }
    exact_profiles = tuple(
        profile for profile, expected in destinations.items()
        if expected.issubset(present)
    )
    blockers: list[str] = []
    if requested != "auto":
        unsafe_missing = tuple(
            item for item in missing_by_profile[requested]
            if item not in SAFE_CREATE_FILES
        )
        if unsafe_missing:
            blockers.append(
                f"Profile {requested} is missing managed artifacts: {', '.join(unsafe_missing)}"
            )
        return requested, exact_profiles, missing_by_profile, tuple(blockers)
    if exact_profiles:
        chosen = max(exact_profiles, key=lambda item: PROFILE_RANKS[item])
        return chosen, exact_profiles, missing_by_profile, ()

    ranked = sorted(
        ((len(missing), -PROFILE_RANKS[profile], profile) for profile, missing in missing_by_profile.items()),
        key=lambda item: (item[0], item[1], item[2]),
    )
    best_missing = ranked[0][0]
    best_profiles = [profile for missing_count, _, profile in ranked if missing_count == best_missing]
    chosen = best_profiles[0]
    if len(best_profiles) > 1:
        blockers.append(
            "Candidate profile is ambiguous; multiple profiles require the same number of managed artifacts"
        )
    return chosen, exact_profiles, missing_by_profile, tuple(blockers)


def has_conflicting_claude(root: Path) -> bool:
    path = root / "CLAUDE.md"
    if not path.exists():
        return False
    try:
        return path.read_text(encoding="utf-8").strip() != "@AGENTS.md"
    except OSError:
        return True


def collect_files_to_create(root: Path) -> tuple[str, ...]:
    return tuple(sorted(path for path in SAFE_CREATE_FILES if not (root / path).exists()))


def collect_files_to_merge(root: Path) -> tuple[str, ...]:
    merge_candidates = list(CORE_DOCS) + ["docs/README.md"]
    return tuple(path for path in merge_candidates if (root / path).exists())


def collect_manual_review(root: Path) -> tuple[str, ...]:
    review: list[str] = []
    for path in ("README.md", "PROJECT.md", "AGENTS.md", "docs"):
        if (root / path).exists():
            review.append(path)
    for pattern in MANUAL_REVIEW_PATTERNS:
        if (root / pattern).exists():
            review.append(pattern)
    if (root / ".github").exists():
        review.append(".github")
    return tuple(sorted(dict.fromkeys(review)))


def collect_transfer_set(root: Path) -> tuple[str, ...]:
    transfer: list[str] = []
    for path in TRANSFER_DIRS:
        if (root / path).exists():
            transfer.append(path)
    for path in TRANSFER_FILES:
        if (root / path).exists():
            transfer.append(path)
    return tuple(transfer)


def assess_project(root: Path, contract_root: Path, requested_strategy: str, requested_profile: str) -> AssessmentReport:
    if not root.is_dir():
        raise StandardizationConfigError(f"Project root is not a directory: {root}")
    rows = load_artifacts(contract_root)
    destinations = profile_destinations(rows)
    present = existing_managed(root, set().union(*destinations.values()))
    git_state = inspect_git(root)
    candidate_profile, exact_profiles, missing_by_profile, profile_blockers = detect_candidate_profile(
        present, destinations, requested_profile
    )
    nested_obsidian = (root / ".obsidian").exists()
    conflicting_claude = has_conflicting_claude(root)
    expected = destinations[candidate_profile] if candidate_profile else set()
    files_to_create = tuple(sorted(
        path for path in SAFE_CREATE_FILES
        if path in expected and not (root / path).exists()
    ))
    files_to_merge = collect_files_to_merge(root)
    files_to_review = collect_manual_review(root)
    proposed_transfer = collect_transfer_set(root)

    adopt_blockers: list[str] = list(profile_blockers)
    rebootstrap_blockers: list[str] = []
    core_missing = [path for path in CORE_DOCS if not (root / path).exists()]
    if not git_state.repository:
        adopt_blockers.append("adopt-in-place requires the target to be a Git repository root")
    if not git_state.clean:
        adopt_blockers.append("adopt-in-place should not start from a dirty working tree without explicit approval")
    if nested_obsidian:
        adopt_blockers.append("nested .obsidian must be removed or explained before in-place standardization")
    if conflicting_claude:
        adopt_blockers.append("CLAUDE.md conflicts with the managed @AGENTS.md import contract")
    if requested_profile != "auto" and requested_profile in missing_by_profile:
        unsafe_missing = [
            item for item in missing_by_profile[requested_profile]
            if item not in SAFE_CREATE_FILES
        ]
        if unsafe_missing:
            adopt_blockers.append(f"Requested profile {requested_profile} is incomplete for the current tree")
    if len(core_missing) >= 3:
        adopt_blockers.append(f"Too many core documents are missing for safe in-place adoption: {', '.join(core_missing)}")

    if nested_obsidian:
        rebootstrap_blockers.append("legacy project contains nested .obsidian; contents need manual review before transfer")

    safe_to_adopt = not adopt_blockers
    safe_to_rebootstrap = not rebootstrap_blockers

    if requested_strategy == "adopt-in-place":
        recommended = "adopt-in-place" if safe_to_adopt else "re-bootstrap-from-existing"
    elif requested_strategy == "re-bootstrap-from-existing":
        recommended = "re-bootstrap-from-existing" if safe_to_rebootstrap else "adopt-in-place"
    else:
        if safe_to_adopt and len(core_missing) <= 1 and len(files_to_review) <= 4:
            recommended = "adopt-in-place"
        else:
            recommended = "re-bootstrap-from-existing"

    blocking_issues: list[str] = []
    if not safe_to_adopt:
        blocking_issues.extend(f"adopt-in-place: {item}" for item in adopt_blockers)
    if not safe_to_rebootstrap:
        blocking_issues.extend(f"re-bootstrap-from-existing: {item}" for item in rebootstrap_blockers)

    status = "ready"
    if requested_strategy == "adopt-in-place" and not safe_to_adopt:
        status = "manual_review_required"
    elif requested_strategy == "re-bootstrap-from-existing" and not safe_to_rebootstrap:
        status = "manual_review_required"
    elif requested_strategy == "auto" and not safe_to_adopt and not safe_to_rebootstrap:
        status = "blocked"
    elif profile_blockers or core_missing:
        status = "manual_review_required"

    return AssessmentReport(
        root=root,
        requested_strategy=requested_strategy,
        requested_profile=requested_profile,
        status=status,
        recommended_strategy=recommended,
        candidate_profile=candidate_profile,
        safe_to_adopt_in_place=safe_to_adopt,
        safe_to_rebootstrap=safe_to_rebootstrap,
        blocking_issues=tuple(blocking_issues),
        files_to_create=files_to_create,
        files_to_merge=files_to_merge,
        files_to_review_manually=files_to_review,
        proposed_transfer_set=proposed_transfer,
        adopt_blockers=tuple(adopt_blockers),
        rebootstrap_blockers=tuple(rebootstrap_blockers),
        git_repository=git_state.repository,
        clean_git_tree=git_state.clean,
        nested_obsidian=nested_obsidian,
        conflicting_claude=conflicting_claude,
        exact_profiles=exact_profiles,
        missing_by_profile=missing_by_profile,
    )


def report_as_dict(report: AssessmentReport) -> dict[str, object]:
    return {
        "root": str(report.root),
        "requested_strategy": report.requested_strategy,
        "requested_profile": report.requested_profile,
        "status": report.status,
        "recommended_strategy": report.recommended_strategy,
        "candidate_profile": report.candidate_profile,
        "safe_to_adopt_in_place": report.safe_to_adopt_in_place,
        "safe_to_rebootstrap": report.safe_to_rebootstrap,
        "blocking_issues": list(report.blocking_issues),
        "files_to_create": list(report.files_to_create),
        "files_to_merge": list(report.files_to_merge),
        "files_to_review_manually": list(report.files_to_review_manually),
        "proposed_transfer_set": list(report.proposed_transfer_set),
        "adopt_blockers": list(report.adopt_blockers),
        "rebootstrap_blockers": list(report.rebootstrap_blockers),
        "git_repository": report.git_repository,
        "clean_git_tree": report.clean_git_tree,
        "nested_obsidian": report.nested_obsidian,
        "conflicting_claude": report.conflicting_claude,
        "exact_profiles": list(report.exact_profiles),
        "missing_by_profile": {key: list(value) for key, value in report.missing_by_profile.items()},
    }


def format_report(report: AssessmentReport) -> str:
    lines = [
        f"status={report.status}",
        f"recommended_strategy={report.recommended_strategy}",
        f"candidate_profile={report.candidate_profile or 'unknown'}",
        f"safe_to_adopt_in_place={'yes' if report.safe_to_adopt_in_place else 'no'}",
        f"safe_to_rebootstrap={'yes' if report.safe_to_rebootstrap else 'no'}",
        f"git_repository={'yes' if report.git_repository else 'no'}",
        f"clean_git_tree={'yes' if report.clean_git_tree else 'no'}",
    ]
    if report.blocking_issues:
        lines.append("blocking_issues:")
        lines.extend(f"- {item}" for item in report.blocking_issues)
    if report.files_to_create:
        lines.append("files_to_create:")
        lines.extend(f"- {item}" for item in report.files_to_create)
    if report.files_to_merge:
        lines.append("files_to_merge:")
        lines.extend(f"- {item}" for item in report.files_to_merge)
    if report.files_to_review_manually:
        lines.append("files_to_review_manually:")
        lines.extend(f"- {item}" for item in report.files_to_review_manually)
    if report.proposed_transfer_set:
        lines.append("proposed_transfer_set:")
        lines.extend(f"- {item}" for item in report.proposed_transfer_set)
    lines.append("No files were changed.")
    return "\n".join(lines)


def render_artifact(contract_root: Path, destination: str, project_name: str) -> str:
    today = date.today().isoformat()
    if destination == ".gitignore":
        return "\n".join((
            ".DS_Store",
            "Thumbs.db",
            ".trash/",
            "CLAUDE.local.md",
            ".claude/settings.local.json",
            ".claude/scheduled_tasks.lock",
            "",
        ))
    if destination == ".gitattributes":
        return "\n".join((
            "* text=auto",
            "*.sh text eol=lf",
            "*.ps1 text eol=crlf",
            "*.md text eol=lf",
            "*.json text eol=lf",
            "",
        ))
    if destination == ".editorconfig":
        return """# EditorConfig — https://editorconfig.org
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false

[*.ps1]
end_of_line = crlf
indent_size = 4

[Makefile]
indent_style = tab

[*.go]
indent_style = tab
"""
    if destination == "CLAUDE.md":
        return "@AGENTS.md\n"
    rows = load_artifacts(contract_root)
    source = next((row.source for row in rows if row.destination == destination), None)
    if source is None or source == "@generated":
        raise StandardizationConfigError(f"Cannot render unknown artifact: {destination}")
    template = (contract_root / "templates" / "new-project" / source).read_text(encoding="utf-8")
    return template.replace("<PROJECT_NAME>", project_name).replace("<YYYY-MM-DD>", today)


def index_row_for(artifact: Artifact) -> Optional[str]:
    if artifact.root_purpose == "-" or not artifact.destination.endswith(".md"):
        return None
    link_path = artifact.destination[:-3]
    return f"| [[{link_path}|{artifact.destination}]] | {artifact.root_purpose} |\n"


def docs_link_for(artifact: Artifact) -> Optional[str]:
    if artifact.docs_section == "-" or artifact.docs_label == "-" or not artifact.destination.endswith(".md"):
        return None
    link_path = artifact.destination[:-3]
    return f"- [[{link_path}|{artifact.docs_label}]]"


def ensure_index_text(current: str, artifacts: Sequence[Artifact]) -> str:
    updated = current
    for artifact in artifacts:
        row = index_row_for(artifact)
        if row is None:
            continue
        if f"[[{artifact.destination[:-3]}" in updated:
            continue
        updated += row
    return updated


def ensure_docs_readme_text(current: str, artifacts: Sequence[Artifact]) -> str:
    updated = current.rstrip("\n")
    for artifact in artifacts:
        bullet = docs_link_for(artifact)
        if bullet is None or bullet in updated:
            continue
        heading = f"## {artifact.docs_section}"
        if heading not in updated:
            updated += f"\n\n{heading}\n\n{bullet}"
            continue
        sections = updated.split("\n")
        insert_at = None
        heading_index = next((idx for idx, line in enumerate(sections) if line.strip() == heading), None)
        if heading_index is None:
            updated += f"\n\n{heading}\n\n{bullet}"
            continue
        insert_at = len(sections)
        for idx in range(heading_index + 1, len(sections)):
            if sections[idx].startswith("## "):
                insert_at = idx
                break
        sections.insert(insert_at, bullet)
        updated = "\n".join(sections)
    return updated + "\n"


def project_name_from_root(root: Path) -> str:
    return root.name


def build_adopt_in_place_plan(root: Path, contract_root: Path, report: AssessmentReport) -> ApplyPlan:
    blockers: list[str] = []
    if report.recommended_strategy != "adopt-in-place" and report.requested_strategy != "adopt-in-place":
        blockers.append("Assessment does not recommend adopt-in-place for this project")
    if not report.safe_to_adopt_in_place:
        blockers.extend(report.adopt_blockers)
    if report.candidate_profile is None:
        blockers.append("Candidate profile is unknown")
    if blockers:
        return ApplyPlan(
            status="blocked",
            strategy="adopt-in-place",
            profile=report.candidate_profile or "unknown",
            summary="In-place standardization plan is blocked.",
            files=(),
            blockers=tuple(dict.fromkeys(blockers)),
            fingerprint="",
        )

    rows = load_artifacts(contract_root)
    selected = [row for row in rows if PROFILE_RANKS[row.minimum_profile] <= PROFILE_RANKS[report.candidate_profile]]
    by_destination = {row.destination: row for row in selected}
    files: list[FilePlan] = []
    project_name = project_name_from_root(root)
    for destination in report.files_to_create:
        files.append(FilePlan(
            path=root / destination,
            action="create",
            content=render_artifact(contract_root, destination, project_name),
            existed=False,
        ))

    final_existing = {row.destination for row in selected if (root / row.destination).exists()} | set(report.files_to_create)
    final_artifacts = [row for row in selected if row.destination in final_existing]

    index_path = root / "INDEX.md"
    if index_path.exists():
        current = index_path.read_text(encoding="utf-8")
        desired = ensure_index_text(current, final_artifacts)
        if desired != current:
            files.append(FilePlan(index_path, "update", desired, True))

    docs_readme = root / "docs" / "README.md"
    if docs_readme.exists():
        current = docs_readme.read_text(encoding="utf-8")
        desired = ensure_docs_readme_text(current, final_artifacts)
        if desired != current:
            files.append(FilePlan(docs_readme, "update", desired, True))

    payload = {
        "root": str(root),
        "strategy": "adopt-in-place",
        "profile": report.candidate_profile,
        "files": [
            {
                "path": file.path.relative_to(root).as_posix(),
                "action": file.action,
                "sha256": hashlib.sha256(file.content.encode("utf-8")).hexdigest(),
            }
            for file in sorted(files, key=lambda item: item.path.as_posix())
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ApplyPlan(
        status="ready",
        strategy="adopt-in-place",
        profile=report.candidate_profile,
        summary="Create only missing safe managed files and add missing index links.",
        files=tuple(sorted(files, key=lambda item: item.path.as_posix())),
        blockers=(),
        fingerprint=fingerprint,
    )


def format_apply_plan(plan: ApplyPlan, root: Path) -> str:
    lines = [
        f"status={plan.status}",
        f"strategy={plan.strategy}",
        f"profile={plan.profile}",
        plan.summary,
    ]
    if plan.blockers:
        lines.append("blocking_issues:")
        lines.extend(f"- {item}" for item in plan.blockers)
    if plan.files:
        lines.append("planned_changes:")
        for file in plan.files:
            lines.append(f"- {file.action}: {file.path.relative_to(root).as_posix()}")
    if plan.fingerprint:
        lines.append(f"fingerprint={plan.fingerprint}")
    lines.append("No files were changed.")
    return "\n".join(lines)


def apply_plan(plan: ApplyPlan) -> list[Path]:
    if plan.status != "ready":
        raise StandardizationApplyError("Cannot apply a blocked plan")
    changed: list[Path] = []
    for file in plan.files:
        file.path.parent.mkdir(parents=True, exist_ok=True)
        file.path.write_text(file.content, encoding="utf-8")
        changed.append(file.path)
    return changed


def post_apply_report(root: Path, contract_root: Path, profile: str) -> tuple[str, int]:
    validator = load_validator_module(contract_root)
    kind, resolved_profile, findings = validator.validate(root, contract_root, "project", profile, False)
    validation_lines = [""]
    validation_lines.append("VALIDATION:")
    from io import StringIO
    buffer = StringIO()
    original_stdout = sys.stdout
    try:
        sys.stdout = buffer
        validator.print_report(root, kind, resolved_profile, findings)
    finally:
        sys.stdout = original_stdout
    validation_lines.append(buffer.getvalue().rstrip("\n"))
    error_count = sum(1 for item in findings if item.severity == "ERROR")

    migration = load_migration_module(contract_root)
    version = migration.read_standard_version(contract_root)
    migrations = migration.read_migrations(contract_root, version)
    plan = migration.project_plan(root, contract_root, profile, migrations, version)
    validation_lines.append("")
    validation_lines.append("NEXT METADATA PLAN:")
    validation_lines.append(migration.format_plan(plan).rstrip("\n"))
    return "\n".join(validation_lines), error_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Planner for standardizing an existing project.")
    parser.add_argument("--root", required=True, help="Existing project root")
    parser.add_argument("--contract-root", default=str(Path(__file__).resolve().parent.parent))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply safe in-place standardization changes")
    mode.add_argument("--plan-adopt", action="store_true", help="Show a reviewable adopt-in-place apply plan")
    parser.add_argument(
        "--strategy",
        choices=("auto", "adopt-in-place", "re-bootstrap-from-existing"),
        default="auto",
    )
    parser.add_argument(
        "--profile",
        choices=("auto", "minimal", "software", "operated", "all"),
        default="auto",
    )
    parser.add_argument("--fingerprint", help="Fingerprint from a reviewed apply plan")
    parser.add_argument("--yes", action="store_true", help="Confirm apply")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if sys.version_info < MIN_PYTHON:
        print("Python 3.9+ is required.", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    try:
        report = assess_project(
            Path(args.root).resolve(),
            Path(args.contract_root).resolve(),
            args.strategy,
            args.profile,
        )
    except StandardizationConfigError as exc:
        print(f"Standardization planner error: {exc}", file=sys.stderr)
        return 2
    if args.apply or args.plan_adopt:
        plan = build_adopt_in_place_plan(Path(args.root).resolve(), Path(args.contract_root).resolve(), report)
        if args.apply:
            if not args.yes:
                print("Apply requires --yes.", file=sys.stderr)
                return 2
            if not args.fingerprint:
                print("Apply requires --fingerprint from a reviewed plan.", file=sys.stderr)
                return 2
            if plan.status != "ready":
                print(format_apply_plan(plan, Path(args.root).resolve()))
                return 1
            if args.fingerprint != plan.fingerprint:
                print("Fingerprint mismatch; rerun the plan and review current changes.", file=sys.stderr)
                return 1
            try:
                changed = apply_plan(plan)
                post_report, error_count = post_apply_report(Path(args.root).resolve(), Path(args.contract_root).resolve(), plan.profile)
            except (OSError, StandardizationApplyError, StandardizationConfigError) as exc:
                print(f"Standardization apply error: {exc}", file=sys.stderr)
                return 1
            print(f"Applied {len(changed)} change(s).")
            for path in changed:
                print(f"- {path.relative_to(Path(args.root).resolve()).as_posix()}")
            print(post_report)
            return 1 if error_count else 0
        if args.json:
            print(json.dumps({
                "assessment": report_as_dict(report),
                "apply_plan": {
                    "status": plan.status,
                    "strategy": plan.strategy,
                    "profile": plan.profile,
                    "summary": plan.summary,
                    "fingerprint": plan.fingerprint,
                    "blockers": list(plan.blockers),
                    "files": [
                        {
                            "path": file.path.relative_to(Path(args.root).resolve()).as_posix(),
                            "action": file.action,
                        }
                        for file in plan.files
                    ],
                },
            }, ensure_ascii=False, indent=2))
        else:
            print(format_apply_plan(plan, Path(args.root).resolve()))
        return 0 if plan.status == "ready" else 1
    if args.json:
        print(json.dumps(report_as_dict(report), ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
