#!/usr/bin/env python3
"""Plan or apply the artifacts of one capability for a project.

Read-only by default, like every other planner in this repository: it prints
what would change and exits. Writing requires both `--apply` and `--yes`, so a
copy-pasted command cannot modify a project by accident.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import capability_artifacts  # noqa: E402
import capability_install  # noqa: E402
import validate_project_support as support  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan or apply capability artifacts for a project.")
    parser.add_argument("--project", required=True, help="project root")
    parser.add_argument("--capability", required=True, help="capability id, for example 1c")
    parser.add_argument("--contract-root", default=str(SCRIPTS.parent), help="rules repository root")
    parser.add_argument("--apply", action="store_true", help="write the planned changes")
    parser.add_argument("--yes", action="store_true", help="confirm writing")
    return parser


def main(argv: list[str] | None = None) -> int:
    # The Windows console is not UTF-8 by default, and a plan names paths and
    # explains itself. Without this the tool can die on its own report.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    project = Path(args.project).resolve()
    contract = Path(args.contract_root).resolve()

    if not project.is_dir():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2

    try:
        artifacts = support.release_artifacts(contract, args.capability)
        plan = capability_artifacts.build_plan(project, args.capability, artifacts)
        # The record travels with the files. Computing it before the plan is
        # applied is what lets a project that cannot host this capability be
        # refused while nothing has been written yet.
        plan = capability_artifacts.with_documents(
            plan, capability_install.documents(project, contract, args.capability), project)
    except (capability_artifacts.CapabilityArtifactsError, support.ManifestError,
            capability_install.InstallError) as error:
        print(f"Cannot plan: {error}", file=sys.stderr)
        return 1

    print(capability_artifacts.format_plan(plan))

    if plan.status == "conflict":
        return 1
    if not args.apply:
        return 0
    if not args.yes:
        print("Refusing to write without --yes.", file=sys.stderr)
        return 2

    try:
        capability_artifacts.apply_plan(project, plan)
    except capability_artifacts.CapabilityArtifactsError as error:
        print(f"Apply failed: {error}", file=sys.stderr)
        return 1
    print("Applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
