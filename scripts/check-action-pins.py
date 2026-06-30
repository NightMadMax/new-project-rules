#!/usr/bin/env python3
"""Reject mutable external references in GitHub Actions workflows."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Sequence


USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")
ACTION_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[^@\s]+)?@([0-9a-f]{40})$")
DOCKER_RE = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")


def workflow_files(root: Path) -> list[Path]:
    workflows = root / ".github" / "workflows"
    return sorted((*workflows.glob("*.yml"), *workflows.glob("*.yaml")))


def check_workflow(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"cannot read workflow: {exc}"]
    for number, line in enumerate(lines, 1):
        match = USES_RE.match(line)
        if not match:
            continue
        reference = match.group(1)
        if len(reference) >= 2 and reference[0] in {"'", '"'} and reference[-1] == reference[0]:
            reference = reference[1:-1]
        if reference.startswith("./"):
            continue
        if reference.startswith("docker://"):
            if not DOCKER_RE.fullmatch(reference):
                findings.append(f"{number}: docker action must use an immutable sha256 digest")
            continue
        if not ACTION_RE.fullmatch(reference):
            findings.append(f"{number}: external action must be pinned to a lowercase 40-hex commit SHA")
    return findings


def check_repository(root: Path) -> list[str]:
    files = workflow_files(root)
    if not files:
        return [".github/workflows contains no YAML workflows"]
    findings: list[str] = []
    for path in files:
        for finding in check_workflow(path):
            findings.append(f"{path.relative_to(root).as_posix()}:{finding}")
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check immutable GitHub Actions references.")
    parser.add_argument("--root", default=".", help="Repository root.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Repository root is not a directory: {root}", file=sys.stderr)
        return 2
    findings = check_repository(root)
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}")
        return 1
    print(f"Action pin check passed for {len(workflow_files(root))} workflow(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
