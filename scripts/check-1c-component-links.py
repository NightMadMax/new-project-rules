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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CATALOG = "docs/architecture/one-c/ENVIRONMENT_SETUP_PLAN.md"
# The machine-readable catalog carries the links the setup prompt actually
# shows; checking only the prose table would leave those unchecked.
CATALOGS = (CATALOG, "config/1c-components.tsv")
LINK_RE = re.compile(r"https?://[^\s<>()\[\]\"'`]+")
TIMEOUT_SECONDS = 10


def links(root: Path, catalog: str | tuple[str, ...] = CATALOGS) -> list[str]:
    sources = (catalog,) if isinstance(catalog, str) else catalog
    found: set[str] = set()
    for source in sources:
        path = root / source
        if path.is_file():
            found.update(LINK_RE.findall(path.read_bytes().decode("utf-8")))
    return sorted({link.rstrip(".,;:") for link in found})


def fetch(url: str, method: str, opener) -> tuple[str, str]:
    with opener(Request(url, method=method, headers={"User-Agent": "new-project-rules"}),
                timeout=TIMEOUT_SECONDS) as response:
        code = getattr(response, "status", 0) or 0
        return ("OK", str(code)) if code < 400 else ("MOVED", str(code))


def probe(url: str, opener=urlopen) -> tuple[str, str]:
    """(status, detail). Every failure is a status, never an exception.

    "The source moved" is the whole reason this report exists, so it has to be
    distinguishable from "there is no network". A 404 arrives as an exception,
    not as a response, and HTTPError is a URLError — catching the general case
    first would file every moved page under "unreachable".
    """
    try:
        return fetch(url, "HEAD", opener)
    except HTTPError as error:
        # Vendor portals often refuse HEAD outright; that says nothing about
        # whether the page is there.
        if error.code in (403, 405, 501):
            try:
                return fetch(url, "GET", opener)
            except HTTPError as retry:
                return "MOVED", f"{retry.code} {retry.reason}"[:80]
            except URLError as retry:
                return "UNREACHABLE", str(retry.reason)[:80]
            except Exception as retry:  # noqa: BLE001 - a report must survive anything
                return "UNREACHABLE", f"{type(retry).__name__}: {retry}"[:80]
        return "MOVED", f"{error.code} {error.reason}"[:80]
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
