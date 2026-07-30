#!/usr/bin/env python3
"""Expand the routing map over a pinned upstream checkout into ledger rows.

Maintainer-only and offline. The decisions live in `config/1c-routing.tsv` — one
row per group of upstream paths, each carrying the S-decision that put it there —
and this turns them into the per-file ledger the release contract wants.

Two failures matter more than the expansion itself, and both are silent
otherwise:

* **A file nobody routed.** Upstream adds a file, no pattern matches it, and it
  simply does not appear in the release. "Not mentioned" and "deliberately
  excluded" look identical in a diff a year later, so an unmatched file is an
  error, not a default.
* **A pattern nobody needs.** Upstream deletes a file and its route stays
  behind, describing a decision about nothing. A pattern that matches no file is
  an error for the same reason in the other direction.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import one_c_adaptations as adaptations  # noqa: E402
import one_c_agents as agents  # noqa: E402
import release_manifest as release  # noqa: E402

ADAPTERS = {"codex": "adapters/codex.yaml", "claude": "adapters/claude-code.yaml"}
ROUTING_NAME = "config/1c-routing.tsv"
ROUTING_FIELDS = ("pattern", "selector", "action", "action_id", "ownership", "target", "decision")
UPSTREAM_SOURCE = "ai_rules_1c"


def read_routing(contract_root: Path) -> list[dict[str, str]]:
    path = contract_root / ROUTING_NAME
    text = path.read_bytes().decode("utf-8")
    rows = list(csv.DictReader(text.splitlines(), delimiter="\t"))
    if not rows:
        raise release.ReleaseError(f"{ROUTING_NAME} holds no routes")
    for position, row in enumerate(rows, start=2):
        missing = [field for field in ROUTING_FIELDS if not row.get(field)]
        if missing:
            raise release.ReleaseError(f"{ROUTING_NAME}:{position} is missing {', '.join(missing)}")
        if row["action"] not in release.ACTIONS:
            raise release.ReleaseError(f"{ROUTING_NAME}:{position} has unknown action {row['action']}")
        if row["ownership"] not in release.OWNERSHIPS:
            raise release.ReleaseError(f"{ROUTING_NAME}:{position} has unknown ownership {row['ownership']}")
    return rows


def tracked_files(staging: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(staging), "-c", "core.quotePath=false", "ls-files", "-z"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise release.ReleaseError(f"cannot list staging: {result.stderr.strip()}")
    return sorted(name for name in result.stdout.split("\0") if name)


def blob(staging: Path, path: str) -> bytes:
    """The committed bytes, never the working copy.

    With `core.autocrlf=true` — the Windows default — a checkout rewrites line
    endings, so hashing the file on disk would pin the platform instead of the
    content: the same upstream commit would produce a different release_id on
    Windows and on Linux, and "same input, same identifier" would be false.
    """
    result = subprocess.run(["git", "-C", str(staging), "show", f"HEAD:{path}"], capture_output=True)
    if result.returncode != 0:
        raise release.ReleaseError(f"cannot read {path} from staging: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout


def matches(pattern: str, path: str) -> bool:
    """`**` means "this subtree"; everything else is one path segment."""
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-2])
    return fnmatch.fnmatchcase(path, pattern)


def target_of(route: dict[str, str], path: str) -> str:
    if route["action"] == "route":
        return "-"
    stem = Path(path).stem
    # `path` inside the group the pattern selected, so a skill keeps its own
    # directory layout under the canonical skills root.
    prefix = route["pattern"][:-3] + "/" if route["pattern"].endswith("/**") else ""
    tail = path[len(prefix):] if prefix and path.startswith(prefix) else path
    inner = path[len("content/skills/"):] if path.startswith("content/skills/") else tail
    return route["target"].format(stem=stem, tail=tail, path=inner)


def project_agent(staging: Path, path: str, client: str) -> tuple[str, str]:
    """Where an agent lands for this client, and the hash of what lands there.

    The adapter is the spec, so the output is a function of two upstream files
    and nothing else — which is what makes the hash reproducible on another
    machine.
    """
    adapter = blob(staging, ADAPTERS[client]).decode("utf-8")
    body = blob(staging, path).decode("utf-8")
    rendered = agents.compile_agent(body, adapter, client).encode("utf-8")
    return agents.target_for(Path(path), adapter), hashlib.sha256(rendered).hexdigest()


def expand(contract_root: Path, staging: Path) -> tuple[list[dict[str, str]], list[str]]:
    routes = read_routing(contract_root)
    files = tracked_files(staging)
    rows: list[dict[str, str]] = []
    unmatched: list[str] = []
    used: set[int] = set()

    for path in files:
        chosen = [(index, route) for index, route in enumerate(routes)
                  if matches(route["pattern"], path)]
        if not chosen:
            unmatched.append(path)
            continue
        # First match wins, so the specific route sits above the group route.
        index, _ = chosen[0]
        used.add(index)
        for position, route in chosen:
            if route["pattern"] != routes[index]["pattern"]:
                continue
            used.add(position)
            content = blob(staging, path)
            digest = hashlib.sha256(content).hexdigest()
            target_path, target_digest = target_of(route, path), "-"
            if route["action"] == "copy":
                target_digest = digest
            elif route["action"] == "compile" and route["action_id"] == "agent-projection":
                target_path, target_digest = project_agent(staging, path, route["selector"])
            elif route["action"] == "adapt":
                text = content.decode("utf-8")
                adapted = adaptations.adapt(contract_root, route["action_id"], path, text)
                target_digest = hashlib.sha256(adapted.encode("utf-8")).hexdigest()
            rows.append({
                "source": UPSTREAM_SOURCE,
                "source_path": path,
                "source_selector": route["selector"],
                "source_sha256": digest,
                "action": route["action"] if route["action"] == "copy" else f"{route['action']}:{route['action_id']}",
                "action_id": route["action_id"],
                "ownership": route["ownership"],
                "target_path": target_path,
                "target_sha256": target_digest,
            })

    stale = [route["pattern"] for index, route in enumerate(routes) if index not in used]
    problems = [f"upstream file has no route: {path}" for path in unmatched]
    problems += [f"route matches nothing in upstream: {pattern}" for pattern in stale]
    return rows, problems


def report(rows: list[dict[str, str]], files_count: int) -> None:
    by_action: dict[str, int] = {}
    for row in rows:
        by_action[row["action"].split(":")[0]] = by_action.get(row["action"].split(":")[0], 0) + 1
    sources = {row["source_path"] for row in rows}
    print(f"Upstream files: {files_count}; routed: {len(sources)}; ledger rows: {len(rows)}")
    for action in sorted(by_action):
        print(f"  {action:8} {by_action[action]}")
    pending = [row for row in rows if row["action"].startswith(("compile", "adapt")) and row["target_sha256"] == "-"]
    if pending:
        print(f"Rows still without an output hash: {len(pending)} "
              f"({', '.join(sorted({row['action'] for row in pending}))})")
        print("The ledger is not written while a declared output does not exist.")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract-root", default=str(SCRIPTS.parent))
    parser.add_argument("--staging", required=True, help="checkout of the pinned upstream commit")
    arguments = parser.parse_args(argv)

    try:
        rows, problems = expand(Path(arguments.contract_root).resolve(), Path(arguments.staging).resolve())
    except adaptations.AdaptationError as error:
        print(f"Adaptation does not apply: {error}", file=sys.stderr)
        return 1
    except release.ReleaseError as error:
        print(f"Routing is not usable: {error}", file=sys.stderr)
        return 2

    report(rows, len({row["source_path"] for row in rows}) + len([p for p in problems if "no route" in p]))
    for problem in problems:
        print(f"BLOCKED  {problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} routing problem(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
