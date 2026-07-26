#!/usr/bin/env python3
"""Tests for the release passport, the artifact ledger and the builder."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("release_manifest", SCRIPTS / "release_manifest.py")
assert spec and spec.loader
release = importlib.util.module_from_spec(spec)
sys.modules["release_manifest"] = release
spec.loader.exec_module(release)

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def row(**overrides) -> dict[str, str]:
    body = overrides.pop("body", b"one\n")
    base = {
        "source_path": "content/a.md",
        "source_selector": "-",
        "source_sha256": digest(body),
        "action": "copy",
        "action_id": "-",
        "ownership": "project-managed",
        "target_path": "a.md",
        "target_sha256": digest(body),
    }
    base.update(overrides)
    return base


def passport(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "capability": "1c",
        "version": "0.1.0",
        "release_id": "0" * 64,
        "inventory_count": 1,
        "sources": [{"name": "ai_rules_1c", "repository": "comol/ai_rules_1c", "commit": "1" * 40}],
    }
    base.update(overrides)
    return base


def write_release(root: Path, document: dict, rows: list[dict[str, str]], fix_id: bool = True) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    if fix_id:
        document = dict(document)
        document["release_id"] = release.compute_release_id(document, rows)
    (root / release.RELEASE_NAME).write_bytes(release.canonical_json(document).encode("utf-8"))
    (root / release.ARTIFACTS_NAME).write_bytes(release.artifacts_text(rows).encode("utf-8"))


# --- passport --------------------------------------------------------------

note(not release.validate_release(passport()), "a healthy passport must validate")
note(any("SemVer" in issue for issue in release.validate_release(passport(version="1.0"))), "version must be SemVer")
note(any("release_id" in issue for issue in release.validate_release(passport(release_id="abc"))), "release_id must be a digest")
note(any("unknown keys" in issue for issue in release.validate_release(dict(passport(), extra=1))), "unknown keys must be reported")
note(any("missing keys" in issue for issue in release.validate_release({"schema_version": 1})), "missing keys must be reported")
note(
    any("commit" in issue for issue in release.validate_release(
        passport(sources=[{"name": "x", "repository": "a/b", "commit": "short"}]))),
    "a source commit must be a full id",
)
note(
    any("repeat a name" in issue for issue in release.validate_release(passport(sources=[
        {"name": "x", "repository": "a/b", "commit": "1" * 40},
        {"name": "x", "repository": "c/d", "commit": "2" * 40},
    ]))),
    "duplicate source names must be reported",
)

# --- ledger ----------------------------------------------------------------

def ledger_case(name: str, rows: list[dict[str, str]], expect: str | None) -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "config").mkdir()
        (root / release.ARTIFACTS_NAME).write_bytes(release.artifacts_text(rows).encode("utf-8"))
        try:
            release.read_artifacts(root)
            issue = None
        except release.ReleaseError as error:
            issue = str(error)
        if expect is None:
            note(issue is None, f"{name}: expected no error, got {issue}")
        else:
            note(issue is not None and expect in issue, f"{name}: expected '{expect}', got {issue}")


ledger_case("healthy ledger", [row()], None)
ledger_case("unknown action", [row(action="delete")], "unknown action")
ledger_case("unknown ownership", [row(ownership="mine")], "unknown ownership")
ledger_case("copy that changes bytes", [row(target_sha256=digest(b"other"))], "copy must not change the file")
ledger_case("adapt without an id", [row(action="adapt", target_sha256=digest(b"other"))], "requires an action_id")
ledger_case(
    "route with an output",
    [row(action="route", action_id="renderer", target_path="a.md")],
    "route produces no output",
)
ledger_case("route without an owner", [row(action="route", action_id="", target_path="-", target_sha256="-")], "requires an owner")
ledger_case("duplicate source", [row(), row()], "duplicate source")
ledger_case("bad source digest", [row(source_sha256="abc")], "source_sha256 must be")

# --- identity and completeness --------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    rows = [row()]
    write_release(root, passport(), rows)
    note(not release.check_release(root), f"a consistent release must pass: {release.check_release(root)}")

    first = release.read_release(root)["release_id"]
    write_release(root, passport(), rows)
    note(release.read_release(root)["release_id"] == first, "the same input must produce the same release_id")

    write_release(root, passport(version="0.2.0"), rows)
    note(release.read_release(root)["release_id"] != first, "a changed passport must change release_id")

    write_release(root, passport(inventory_count=7), rows)
    note(any("inventory is incomplete" in item for item in release.check_release(root)), "a short inventory must be reported")

    write_release(root, passport(), rows, fix_id=False)
    note(any("release_id does not match" in item for item in release.check_release(root)), "a stale release_id must be reported")

# The identifier must not depend on the order rows happened to be built in.
unordered = [row(source_path="content/b.md"), row(source_path="content/a.md")]
note(
    release.compute_release_id(passport(inventory_count=2), unordered)
    == release.compute_release_id(passport(inventory_count=2), list(reversed(unordered))),
    "release_id must not depend on row order",
)

# --- the builder against a staging checkout --------------------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw) / "rules"
    staging = Path(raw) / "staging"
    (staging / "content").mkdir(parents=True)
    (staging / "content/a.md").write_bytes(b"one\n")
    subprocess.run(["git", "-C", str(staging), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(staging), "add", "-A"], check=True, capture_output=True)

    rows = [row()]
    write_release(root, passport(), rows)

    check = subprocess.run(
        [sys.executable, str(SCRIPTS / "build-capability-release.py"),
         "--contract-root", str(root), "--staging", str(staging)],
        capture_output=True, text=True,
    )
    note(check.returncode == 0, f"a matching staging must pass: {check.stderr[-300:]}")

    (staging / "content/b.md").write_bytes(b"two\n")
    subprocess.run(["git", "-C", str(staging), "add", "-A"], check=True, capture_output=True)
    check = subprocess.run(
        [sys.executable, str(SCRIPTS / "build-capability-release.py"),
         "--contract-root", str(root), "--staging", str(staging)],
        capture_output=True, text=True,
    )
    note(check.returncode != 0, "a new upstream file must fail the build")
    note("has no row" in check.stderr, f"the new file must be named: {check.stderr[-200:]}")

    (staging / "content/b.md").unlink()
    (staging / "content/a.md").write_bytes(b"edited upstream\n")
    subprocess.run(["git", "-C", str(staging), "add", "-A"], check=True, capture_output=True)
    check = subprocess.run(
        [sys.executable, str(SCRIPTS / "build-capability-release.py"),
         "--contract-root", str(root), "--staging", str(staging)],
        capture_output=True, text=True,
    )
    note(check.returncode != 0, "a changed source must fail the build")
    note("source changed" in check.stderr, f"the changed file must be named: {check.stderr[-200:]}")

# --- the upstream check reports and changes nothing -------------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    check = subprocess.run(
        [sys.executable, str(SCRIPTS / "check-upstream-sources.py"), "--contract-root", str(root), "--report-only"],
        capture_output=True, text=True,
    )
    note(check.returncode == 0, "the upstream check must not fail without a release")
    note("nothing to compare" in check.stdout, f"it must say why it did nothing: {check.stdout[:200]}")

    write_release(root, passport(), [row()])
    before = (root / release.RELEASE_NAME).read_bytes()
    check = subprocess.run(
        [sys.executable, str(SCRIPTS / "check-upstream-sources.py"), "--contract-root", str(root), "--report-only"],
        capture_output=True, text=True,
    )
    note(check.returncode == 0, f"the upstream check must stay report-only: {check.stderr[-200:]}")
    note((root / release.RELEASE_NAME).read_bytes() == before, "the upstream check must not modify the release")


if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} release manifest test(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All release manifest tests passed.")
