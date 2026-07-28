#!/usr/bin/env python3
"""Check the external links of the 1C component catalog. Reports, never fails.

A source that moved is worth knowing about, but it is not a reason to stop a
build: the links point at vendor pages outside our control, and a network that
is down says nothing about the repository. So this prints what it found and
exits zero — a red build here would train people to ignore it.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

CATALOG = "docs/architecture/one-c/ENVIRONMENT_SETUP_PLAN.md"
LINK_RE = re.compile(r"https?://[^\s<>()\[\]\"'`]+")
TIMEOUT_SECONDS = 10


def links(root: Path, catalog: str = CATALOG) -> list[str]:
    path = root / catalog
    if not path.is_file():
        return []
    found = LINK_RE.findall(path.read_bytes().decode("utf-8"))
    return sorted({link.rstrip(".,;:") for link in found})


def probe(url: str, opener=urlopen) -> tuple[str, str]:
    """(status, detail). Every failure is a status, never an exception."""
    try:
        with opener(Request(url, method="HEAD", headers={"User-Agent": "new-project-rules"}),
                    timeout=TIMEOUT_SECONDS) as response:
            code = getattr(response, "status", 0) or 0
            return ("OK", str(code)) if code < 400 else ("MOVED", str(code))
    except URLError as error:
        return "UNREACHABLE", str(error.reason)[:80]
    except Exception as error:  # noqa: BLE001 - a report must survive anything
        return "UNREACHABLE", f"{type(error).__name__}: {error}"[:80]


def report(root: Path, opener=urlopen, network: bool = True) -> list[tuple[str, str, str]]:
    rows = []
    for url in links(root):
        if not network:
            rows.append((url, "SKIP", "проверка сети не запрашивалась"))
            continue
        status, detail = probe(url, opener)
        rows.append((url, status, detail))
    return rows


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--network", action="store_true",
                        help="actually reach the sources; without it every link is a SKIP")
    arguments = parser.parse_args()

    rows = report(Path(arguments.root).resolve(), network=arguments.network)
    if not rows:
        print("В каталоге компонентов нет внешних ссылок.")
        return 0
    for url, status, detail in rows:
        print(f"[{status:11}] {url} — {detail}")
    unreachable = sum(1 for _, status, _ in rows if status != "OK")
    print(f"Ссылок: {len(rows)}, требуют внимания: {unreachable}. Отчёт не влияет на код возврата.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
