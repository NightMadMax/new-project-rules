#!/usr/bin/env python3
"""Build or verify a capability release from a local staging checkout.

Maintainer-only and offline: the staging directory is a checkout someone
already made, so neither this script nor a created project reaches the network.

Read-only by default. `--write` rewrites the passport and the ledger in
canonical form and stamps a new `release_id`; it refuses to do so unless every
staging source is present, unchanged and sitting on the pinned commit, because
a release identifier that blesses a mismatched input is worse than none.
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


def git_output(staging: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(staging), "-c", "core.quotePath=false", *arguments],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise release.ReleaseError(f"git {' '.join(arguments)} failed in staging: {result.stderr.strip()}")
    return result.stdout


def tracked_files(staging: Path) -> list[str]:
    """Files git tracks in staging: the same set a reviewer would see.

    NUL-separated: a path with a non-ASCII name would otherwise arrive
    C-quoted, and every such file would look both missing and unexpected.
    """
    return sorted(name for name in git_output(staging, "ls-files", "-z").split("\0") if name)


def check_staging_state(staging: Path, source: dict) -> list[str]:
    """A pinned source is only pinned if staging actually sits on that commit."""
    findings: list[str] = []
    toplevel = Path(git_output(staging, "rev-parse", "--show-toplevel").strip()).resolve()
    if toplevel != staging.resolve():
        findings.append(f"staging is inside another repository ({toplevel}), not its root")
        return findings
    head = git_output(staging, "rev-parse", "HEAD").strip()
    if head != source["commit"]:
        findings.append(f"staging is on {head[:12]}, but the release pins {source['commit'][:12]}")
    if git_output(staging, "status", "--porcelain").strip():
        findings.append("staging has uncommitted changes; a release cannot be built from it")
    return findings


def digest_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(staging: Path, rows: list[dict[str, str]], source_name: str) -> list[str]:
    """Every tracked file must have a row, and every row must match its file."""
    findings: list[str] = []
    rows = [row for row in rows if row["source"] == source_name]
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
    parser.add_argument(
        "--staging", action="append", default=[], metavar="NAME=PATH",
        help="local checkout of a pinned source, for example ai_rules_1c=../staging",
    )
    parser.add_argument("--write", action="store_true", help="recompute release_id and write it")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    contract = Path(args.contract_root).resolve()

    try:
        findings = release.check_release(contract)
        passport = release.read_release(contract)
        rows = release.read_artifacts(contract)
        by_name = {source["name"]: source for source in passport["sources"]}
        for pair in args.staging:
            name, separator, path = pair.partition("=")
            if not separator:
                print(f"--staging expects NAME=PATH, got '{pair}'", file=sys.stderr)
                return 2
            if name not in by_name:
                print(f"Unknown source '{name}'", file=sys.stderr)
                return 2
            staging = Path(path).resolve()
            findings.extend(check_staging_state(staging, by_name[name]))
            findings.extend(compare(staging, rows, name))
    except release.ReleaseError as error:
        print(f"Release is not buildable: {error}", file=sys.stderr)
        return 1

    if args.write:
        missing = sorted({source["name"] for source in passport["sources"]} - {pair.split("=")[0] for pair in args.staging})
        if missing:
            print(f"Refusing to write without staging for: {', '.join(missing)}", file=sys.stderr)
            return 2
        for finding in findings:
            print(f"FAIL: {finding}", file=sys.stderr)
        if findings:
            print("Refusing to stamp a release over unresolved findings.", file=sys.stderr)
            return 1
        passport["inventory_count"] = len(rows)
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
