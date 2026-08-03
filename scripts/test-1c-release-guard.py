#!/usr/bin/env python3
"""The runtime must not act on a project that installed another release.

Delivery is versioned to the byte and refuses on drift. Runtime was not: the
scripts that decide whether a live infobase may be written are run out of a
`new-project-rules` checkout against a project directory, updated on different
days, and nothing compared them. These cases are about where the refusal lands —
a writer refuses, a diagnosis reports — and about the two states that must *not*
be treated as a mismatch.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


guard = load("one_c_release_guard", "one_c_release_guard.py")
doctor = load("one_c_doctor", "one_c_doctor.py")

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def project(root: Path, release_id: str | None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    data: dict = {"schema_version": 5}
    if release_id is not None:
        data["capability_releases"] = {"1c": {"version": "0.5.0", "release_id": release_id}}
    (root / ".project-standard.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root


def checkout(root: Path, release_id: str | None) -> Path:
    (root / "config").mkdir(parents=True, exist_ok=True)
    if release_id is not None:
        (root / "config/1c-release.json").write_text(
            json.dumps({"capability": "1c", "release_id": release_id}, ensure_ascii=False) + "\n",
            encoding="utf-8")
    return root


with tempfile.TemporaryDirectory() as raw:
    base = Path(raw)

    # --- the two states that are not a mismatch -----------------------------
    matched = guard.require_matching_release(
        project(base / "p1", DIGEST_A), checkout(base / "s1", DIGEST_A))
    note(matched == DIGEST_A, f"identical releases must agree, got {matched}")

    # A project without the capability has nothing to disagree about, and
    # answering "mismatch" there would make every fresh project look broken.
    none_installed = guard.require_matching_release(
        project(base / "p2", None), checkout(base / "s2", DIGEST_A))
    note(none_installed is None, f"a project without the capability must pass, got {none_installed}")

    # --- the mismatch itself -------------------------------------------------
    try:
        guard.require_matching_release(project(base / "p3", DIGEST_A), checkout(base / "s3", DIGEST_B))
        failures.append("two different releases must be refused")
    except guard.ReleaseMismatch as error:
        note(DIGEST_A[:12] in str(error) and DIGEST_B[:12] in str(error),
             f"the refusal must name both sides: {error}")

    # A checkout with no passport is a broken checkout, and the message must say
    # so rather than blame the project for a mismatch it cannot see.
    try:
        guard.require_matching_release(project(base / "p4", DIGEST_A), checkout(base / "s4", None))
        failures.append("an unreadable release passport must be refused")
    except guard.ReleaseMismatch as error:
        note("checkout" in str(error), f"the refusal must name the checkout: {error}")

    # --- where the refusal lands --------------------------------------------
    # The session lock authorises writes to a live infobase: it refuses.
    session_project = project(base / "p5", DIGEST_A)
    (session_project / "config").mkdir(parents=True, exist_ok=True)
    (session_project / "config/1c-projects.tsv").write_text(
        "project_id\tenvironment_id\tserver_port\tapplication_kind\tis_production\n"
        "erp\tdev\t6003\tordinary\tfalse\n", encoding="utf-8")
    def session(*command: str):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "one_c_session.py"), "--root", str(session_project),
             *command], capture_output=True, text=True, encoding="utf-8")

    for command in (["require"], ["acquire", "--base", "erp/dev", "--confirmed-by", "probe"]):
        result = session(*command)
        note(result.returncode != 0,
             f"{command[0]} must refuse a foreign release: {result.stdout} {result.stderr}")
        note("installed release" in result.stderr,
             f"{command[0]} must refuse for the release, not for something else: {result.stderr[:200]}")
        note("[REFUSED]" in result.stderr, f"the refusal must be recognisable: {result.stderr[:200]}")

    # And the guard must not lock the user in. `release` removes state and
    # `show` prints it: refusing those would leave someone holding a stale lock
    # with no way to clear it but deleting the file by hand.
    for command in ("release", "show"):
        result = session(command)
        note("installed release" not in result.stderr,
             f"{command} must not be blocked by the release guard: {result.stderr[:200]}")

    # The diagnosis never fails a run, so it reports the same fact as a row.
    rows = {row.component: row for row in doctor.report(session_project, names=())}
    note("release capability 1c" in rows, f"the diagnosis must carry the release row: {list(rows)}")
    note(rows["release capability 1c"].status == "FAIL",
         f"a foreign release must be a finding, not a pass: {rows.get('release capability 1c')}")
    note(bool(rows["release capability 1c"].action),
         "a row without a consequence is a number nobody acts on")

    clean = project(base / "p6", None)
    clean_rows = {row.component: row for row in doctor.report(clean, names=())}
    note(clean_rows["release capability 1c"].status == "SKIP",
         f"a project without the capability must not be a finding: {clean_rows['release capability 1c']}")


if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} release guard check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("Release guard checks passed.")
