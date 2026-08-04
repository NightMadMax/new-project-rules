#!/usr/bin/env python3
"""Run the regression suites: discovered, not listed, and shardable.

The set of suites used to be written out three times — once per CI job — and a
new test reached every platform only if someone remembered all three lists.
Defects 228 and 259 were both that. A list cannot be sharded either: splitting
thirty-one names across three runners by hand is the same defect with more
copies. So the set is discovered from the filesystem, and being a
`scripts/test-*.py` is what puts a suite in CI.

Sharding exists because of where the time goes. On Windows this suite takes
minutes while the same work on Ubuntu takes seconds: every heavy test runs a
full bootstrap, and process creation there is expensive. Splitting the work
across runners attacks the wall clock directly, which no per-test optimisation
can.

The weights below only balance the shards. A wrong weight costs an unbalanced
split, never a skipped test — every discovered suite lands in exactly one shard
whatever the numbers say.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

SCRIPTS = Path(__file__).resolve().parent

# A suite that cannot be run by discovery alone, and why. Anything listed here
# must be run somewhere else, and the skills contract test checks that it is.
NEEDS_ARGUMENTS = {
    "test-best-practices-e2e.py":
        "requires --best-practices-root; the cross-repo-e2e job runs it against the pinned checkout",
}

# Measured on the Windows runner, 2026-08-03. Only the heavy ones are listed;
# everything else counts as 1. These numbers move the split, not the coverage.
WEIGHTS = {
    "test-preset-core.py": 318,
    "test-payload-classes.py": 96,
    "test-one-c-scaffold.py": 60,
    "test-standardize-existing-project.py": 21,
    "test-validator.py": 21,
    "test-1c-clients.py": 17,
    "test-migration-planner.py": 13,
    "test-1c-doctor.py": 20,
}
DEFAULT_WEIGHT = 5


def discover(scripts: Path = SCRIPTS) -> list[Path]:
    return [path for path in sorted(scripts.glob("test-*.py"))
            if path.name not in NEEDS_ARGUMENTS]


def shard(suites: Sequence[Path], index: int, total: int) -> list[Path]:
    """Split by longest-processing-time first, so one heavy suite does not
    decide the wall clock of the whole job."""
    if total == 1:
        return list(suites)
    if not 1 <= index <= total:
        raise SystemExit(f"shard {index} is outside 1..{total}")
    buckets: list[tuple[int, int, list[Path]]] = [(0, position, []) for position in range(total)]
    for path in sorted(suites, key=lambda p: (-WEIGHTS.get(p.name, DEFAULT_WEIGHT), p.name)):
        buckets.sort(key=lambda bucket: (bucket[0], bucket[1]))
        load, position, members = buckets[0]
        members.append(path)
        buckets[0] = (load + WEIGHTS.get(path.name, DEFAULT_WEIGHT), position, members)
    buckets.sort(key=lambda bucket: bucket[1])
    return sorted(buckets[index - 1][2])


def run(suites: Sequence[Path]) -> int:
    failures: list[str] = []
    for path in suites:
        started = time.monotonic()
        result = subprocess.run([sys.executable, str(path)])
        elapsed = time.monotonic() - started
        verdict = "ok" if result.returncode == 0 else f"FAILED ({result.returncode})"
        # The duration is printed for every suite: the last time this job was
        # slow, finding out which test owned the minutes meant parsing the log.
        print(f"[{elapsed:6.1f}s] {path.name} {verdict}", flush=True)
        if result.returncode != 0:
            failures.append(path.name)
    if failures:
        # Every suite runs even after one fails. A run that stops at the first
        # failure hides the rest, and on a platform you cannot reach that costs
        # a whole CI cycle per defect.
        print(f"\n{len(failures)} suite(s) failed: {', '.join(failures)}", file=sys.stderr)
        return 1
    print(f"\n{len(suites)} suite(s) passed.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard", type=int, default=1, help="which shard to run, 1-based")
    parser.add_argument("--of", type=int, default=1, help="how many shards the suite is split into")
    parser.add_argument("--list", action="store_true", help="print the shard and exit")
    args = parser.parse_args(argv)

    suites = discover()
    if not suites:
        print("no test suites were discovered; that is a broken checkout, not an empty run",
              file=sys.stderr)
        return 1
    selected = shard(suites, args.shard, args.of)
    if args.list:
        for path in selected:
            print(path.name)
        return 0
    print(f"shard {args.shard}/{args.of}: {len(selected)} of {len(suites)} suite(s)", flush=True)
    return run(selected)


if __name__ == "__main__":
    raise SystemExit(main())
