#!/usr/bin/env python3
"""Validate the pinned Best Practices compatibility contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_SKILLS = {
    ".agents/skills/apply-best-practices/SKILL.md",
    ".agents/skills/harvest-practice-candidates/SKILL.md",
    ".agents/skills/review-practice-candidates/SKILL.md",
}
REQUIRED_CONSUMER_INTERFACE_FILES = {
    "docs/architecture/decisions/ADR-0006-versioned-consumer-manifest.md",
    "docs/reference/PRACTICE_SCHEMA.md",
    "scripts/practice_report.py",
    "scripts/migrate_consumer_manifest.py",
}


def load_contract(path: Path) -> Dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("contract root must be an object")
    return data


def validate_contract(data: Mapping[str, object]) -> List[str]:
    problems: List[str] = []
    if data.get("schema_version") != 1:
        problems.append("schema_version must be 1")
    if data.get("repository") != "NightMadMax/best-practices":
        problems.append("repository must identify NightMadMax/best-practices")
    if not isinstance(data.get("source_commit"), str) or not SHA_RE.fullmatch(str(data.get("source_commit"))):
        problems.append("source_commit must be a full lowercase commit SHA")
    if data.get("supported_practice_statuses") != ["accepted"]:
        problems.append("only accepted practices may be promotion sources")
    retired = data.get("retired_routes")
    if not isinstance(retired, list) or not retired or not all(isinstance(item, str) for item in retired):
        problems.append("retired_routes must be a non-empty string list")
    surfaces = data.get("active_routing_surfaces")
    if not isinstance(surfaces, list) or not surfaces or not all(isinstance(item, str) for item in surfaces):
        problems.append("active_routing_surfaces must be a non-empty string list")
    governance = data.get("governance")
    if not isinstance(governance, dict) or governance.get("default_branch") != "main" or governance.get("requires_protection") is not True:
        problems.append("governance must require protection for main")

    decision = data.get("npr_decision")
    if not isinstance(decision, dict):
        problems.append("npr_decision must be an object")
    else:
        if not isinstance(decision.get("path"), str) or ".." in Path(str(decision.get("path"))).parts:
            problems.append("npr_decision.path must be repository-relative")
        if not isinstance(decision.get("sha256"), str) or not SHA256_RE.fullmatch(str(decision.get("sha256"))):
            problems.append("npr_decision.sha256 must be lowercase SHA-256")
        literals = decision.get("required_literals")
        if not isinstance(literals, list) or not literals or not all(isinstance(item, str) for item in literals):
            problems.append("npr_decision.required_literals must be a non-empty string list")

    required_files = data.get("required_files")
    if not isinstance(required_files, dict):
        problems.append("required_files must be an object")
        required_files = {}
    missing_skills = REQUIRED_SKILLS - set(required_files)
    if missing_skills:
        problems.append(f"required_files misses skills: {', '.join(sorted(missing_skills))}")
    missing_interface = REQUIRED_CONSUMER_INTERFACE_FILES - set(required_files)
    if missing_interface:
        problems.append(
            "required_files misses consumer interface: "
            + ", ".join(sorted(missing_interface))
        )
    for path, digest in required_files.items():
        if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts:
            problems.append(f"unsafe required file path: {path!r}")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            problems.append(f"invalid sha256 for {path!r}")

    promotion = data.get("promotion_source")
    if not isinstance(promotion, dict):
        problems.append("promotion_source must be an object")
    else:
        path = promotion.get("path")
        if not isinstance(path, str) or path not in required_files:
            problems.append("promotion_source.path must reference a pinned required file")
        if promotion.get("required_status") != "accepted":
            problems.append("promotion_source.required_status must be accepted")
        if not isinstance(promotion.get("id"), str) or not str(promotion.get("id")).startswith("PC-"):
            problems.append("promotion_source.id must be a practice ID")
    return problems


def verify_npr_decision(data: Mapping[str, object], root: Path) -> List[str]:
    problems = validate_contract(data)
    if problems:
        return problems
    decision = data["npr_decision"]
    assert isinstance(decision, dict)
    path = root / str(decision["path"])
    if not path.is_file():
        return [f"missing NPR decision: {path.relative_to(root)}"]
    content = path.read_text(encoding="utf-8")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != decision["sha256"]:
        problems.append("NPR decision hash differs from reviewed contract")
    for literal in decision["required_literals"]:
        if literal not in content:
            problems.append(f"NPR decision misses required consequence: {literal}")
    return problems


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _frontmatter(path: Path) -> Dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}
    fields: Dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        if ":" in line and not line[:1].isspace():
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"')
    return fields


def verify_checkout(data: Mapping[str, object], root: Path) -> List[str]:
    problems = validate_contract(data)
    if problems:
        return problems
    if not (root / ".git").exists():
        return [f"Best Practices checkout is not a git repository: {root}"]
    try:
        head = _git(root, "rev-parse", "HEAD")
        remote = _git(root, "remote", "get-url", "origin")
    except subprocess.CalledProcessError as error:
        return [f"cannot inspect Best Practices checkout: {error}"]
    if head != data["source_commit"]:
        problems.append(f"checkout HEAD {head} does not match pinned {data['source_commit']}")
    if not remote.rstrip(".git").endswith(str(data["repository"])):
        problems.append(f"unexpected Best Practices origin: {remote}")

    required_files = data["required_files"]
    assert isinstance(required_files, dict)
    for relative, expected in required_files.items():
        path = root / relative
        if not path.is_file():
            problems.append(f"missing pinned file: {relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            problems.append(f"sha256 mismatch: {relative}")

    promotion = data["promotion_source"]
    assert isinstance(promotion, dict)
    fields = _frontmatter(root / str(promotion["path"]))
    if fields.get("id") != promotion["id"]:
        problems.append("promotion source ID does not match pinned contract")
    if fields.get("status") != promotion["required_status"]:
        problems.append("promotion source is not accepted")
    retired = data["retired_routes"]
    surfaces = data["active_routing_surfaces"]
    assert isinstance(retired, list) and isinstance(surfaces, list)
    for relative in surfaces:
        path = root / relative
        if not path.is_file():
            problems.append(f"missing active routing surface: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for route in retired:
            if route in text:
                problems.append(f"retired route {route!r} remains in {relative}")
    return problems


def verify_latest_commit(data: Mapping[str, object], latest_commit: str) -> List[str]:
    problems = validate_contract(data)
    if problems:
        return problems
    if not SHA_RE.fullmatch(latest_commit):
        return ["Best Practices main did not resolve to a full commit SHA"]
    if latest_commit != data["source_commit"]:
        return [
            f"Best Practices pin {data['source_commit']} is behind main {latest_commit}; "
            "review the BP diff and update the pin explicitly"
        ]
    return []


def resolve_remote_main(data: Mapping[str, object]) -> str:
    git = shutil.which("git")
    if not git:
        raise RuntimeError("Git is unavailable")
    repository = str(data["repository"])
    result = subprocess.run(
        [git, "ls-remote", "--exit-code", f"https://github.com/{repository}.git", "refs/heads/main"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("cannot resolve Best Practices main")
    return result.stdout.split()[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "config" / "best-practices-contract.json",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--best-practices-root", type=Path)
    source.add_argument("--check-latest", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    data = load_contract(args.contract)
    problems = verify_npr_decision(data, args.contract.resolve().parents[1])
    checkout_problems = (
        verify_checkout(data, args.best_practices_root.resolve())
        if args.best_practices_root
        else validate_contract(data)
    )
    problems.extend(problem for problem in checkout_problems if problem not in problems)
    if args.check_latest and not problems:
        try:
            latest_commit = resolve_remote_main(data)
        except RuntimeError as exc:
            problems.append(str(exc))
        else:
            problems.extend(verify_latest_commit(data, latest_commit))
    for problem in problems:
        print(f"ERROR: {problem}")
    if problems:
        return 1
    print("Best Practices compatibility contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
