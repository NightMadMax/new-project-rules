#!/usr/bin/env python3
"""Report whether a pinned source moved. It never changes anything.

The weekly job that calls this only notifies: applying a new upstream commit is
a maintainer decision with a review, not a scheduled side effect.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import release_manifest as release  # noqa: E402


def remote_head(repository: str) -> str | None:
    """The upstream HEAD, or None when it cannot be read.

    A weekly notification must never fail the job: no network, a private
    repository or a hanging connection are all "unknown", not an error. The
    prompt is disabled so a credential request cannot block the runner.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", f"https://github.com/{repository}.git", "HEAD"],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.split()[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report upstream drift for pinned sources.")
    parser.add_argument("--contract-root", default=str(SCRIPTS.parent))
    parser.add_argument("--report-only", action="store_true", help="always exit 0")
    args = parser.parse_args(argv)

    contract = Path(args.contract_root).resolve()
    if not (contract / release.RELEASE_NAME).exists():
        print("No capability release is pinned yet; nothing to compare.")
        return 0

    try:
        passport = release.read_release(contract)
    except release.ReleaseError as error:
        print(f"Cannot read the release passport: {error}")
        return 0 if args.report_only else 1

    moved = []
    for source in passport["sources"]:
        head = remote_head(source["repository"])
        if head is None:
            print(f"- {source['name']}: upstream unreachable, skipped")
            continue
        if head != source["commit"]:
            moved.append(source)
            print(f"- {source['name']}: pinned {source['commit'][:12]}, upstream {head[:12]}")
        else:
            print(f"- {source['name']}: up to date")

    if moved:
        print("")
        print("A pinned source moved. Run the maintainer refresh deliberately; this job changes nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
