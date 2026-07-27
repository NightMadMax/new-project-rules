#!/usr/bin/env python3
"""Render the 1C client projections. Reports by default, writes on --write."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from one_c_clients import ClientError, apply, plan  # noqa: E402


def main() -> int:
    # The Windows console is not UTF-8 by default, and a SKIP line explains
    # itself in Russian: without this the tool dies on its own report.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--write", action="store_true", help="write the projections")
    parser.add_argument("--client", default="all", choices=["all", "claude", "codex"],
                        help="render only the projections of one client")
    arguments = parser.parse_args()

    root = Path(arguments.root).resolve()
    try:
        changes = apply(root, arguments.client) if arguments.write else plan(root, arguments.client)
    except ClientError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 2

    for change in changes:
        print(f"[{change['action'].upper():9}] {change['path']}"
              + (f" — {change['content']}" if change["action"] == "skip" else ""))
    pending = [change for change in changes if change["action"] in ("create", "update")]
    if pending and not arguments.write:
        print(f"{len(pending)} projection(s) would change. Re-run with --write.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
