#!/usr/bin/env python3
"""Build or verify a capability release from a local staging checkout.

Maintainer-only and offline: the staging directory is a checkout someone
already made, so neither this script nor a created project reaches the network.

Read-only by default. `--write` recomputes the passport and the ledger from
staging; without it the command only reports what would change, which is what
CI and a reviewer need.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import release_manifest as release  # noqa: E402


def tracked_files(staging: Path) -> list[str]:
    """Files git tracks in staging: the same set a reviewer would see."""
    result = subprocess.run(
        ["git", "-C", str(staging), "ls-files"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise release.ReleaseError(f"Cannot list staging files: {result.stderr.strip()}")
    return sorted(line for line in result.stdout.splitlines() if line)


def digest_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(staging: Path, rows: list[dict[str, str]]) -> list[str]:
    """Every tracked file must have a row, and every row must match its file."""
    findings: list[str] = []
    declared = {row["source_path"] for row in rows}
    present = set(tracked_files(staging))

    for missing in sorted(present - declared):
        findings.append(f"tracked file has no row: {missing}")
    for extra in sorted(declared - present):
        findings.append(f"row points at a file that is not in staging: {extra}")

    for row in rows:
        path = staging / row["source_path"]
        if not path.is_file():
            continue
        actual = digest_of(path)
        if actual != row["source_sha256"]:
            findings.append(f"source changed since the release was built: {row['source_path']}")
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or verify a capability release.")
    parser.add_argument("--contract-root", default=str(SCRIPTS.parent), help="rules repository root")
    parser.add_argument("--staging", help="local checkout of the pinned source")
    parser.add_argument("--write", action="store_true", help="recompute release_id and write it")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    contract = Path(args.contract_root).resolve()

    try:
        findings = release.check_release(contract)
        passport = release.read_release(contract)
        rows = release.read_artifacts(contract)
        if args.staging:
            findings.extend(compare(Path(args.staging).resolve(), rows))
    except release.ReleaseError as error:
        print(f"Release is not buildable: {error}", file=sys.stderr)
        return 1

    if args.write:
        passport["release_id"] = release.compute_release_id(passport, rows)
        (contract / release.RELEASE_NAME).write_bytes(release.canonical_json(passport).encode("utf-8"))
        (contract / release.ARTIFACTS_NAME).write_bytes(release.artifacts_text(rows).encode("utf-8"))
        print(f"Wrote release {passport['version']} ({passport['release_id'][:12]}…)")
        return 0

    for finding in findings:
        print(f"FAIL: {finding}", file=sys.stderr)
    if findings:
        print(f"{len(findings)} release check(s) failed.", file=sys.stderr)
        return 1
    print(f"Release {passport['version']} ({passport['release_id'][:12]}…) is consistent: {len(rows)} artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
