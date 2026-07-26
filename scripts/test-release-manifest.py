#!/usr/bin/env python3
"""Tests for the release passport, the artifact ledger and the builder."""

from __future__ import annotations

import hashlib
import importlib.util
import os
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
        "source": "ai_rules_1c",
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
        "dependencies": [{"name": "Node.js", "class": "conditional", "reason": "md-to-docx"}],
        "mcp_roles": [{"role": "syntax", "provider_id": "1c-syntax-checker-mcp", "tier": "initial"}],
        "binaries": [{"name": "toolkit-read-only.epf", "sha256": "b" * 64, "application_kind": "ordinary"}],
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

# The identifier must depend on the ledger, not only on the passport.
note(
    release.compute_release_id(passport(), [row()])
    != release.compute_release_id(passport(), [row(target_path="b.md", body=b"one\n")]),
    "release_id must change when the ledger changes",
)

# Canonical serialisation is what release_id is defined over: pin its shape.
canonical = release.canonical_json({"b": 1, "a": "\u0446"})
note(canonical == '{\n  "a": "\u0446",\n  "b": 1\n}\n', f"canonical json changed shape: {canonical!r}")



def raw_ledger_case(name: str, body: str, expect: str) -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "config").mkdir()
        (root / release.ARTIFACTS_NAME).write_bytes(body.encode("utf-8"))
        try:
            release.read_artifacts(root)
            issue = None
        except release.ReleaseError as error:
            issue = str(error)
        note(issue is not None and expect in issue, f"{name}: expected '{expect}', got {issue}")


# A quoted field parses fine but would not survive being written back.
header = "\t".join(release.ARTIFACT_FIELDS)
quoted = "\t".join([
    "ai_rules_1c", '"content/a\tb.md"', "-", digest(b"one\n"), "copy", "-",
    "project-managed", "a.md", digest(b"one\n"),
])
raw_ledger_case("quoted field with a separator", f"{header}\n{quoted}\n", "separator or quote")
raw_ledger_case("wrong header", "source\tsource_path\n" + "x\ty\n", "Unexpected header")
raw_ledger_case("header only", header + "\n", "declares no artifacts")
ledger_case("target hash is not hex", [row(action="adapt", action_id="fix", target_sha256="zz")], "target_sha256 must be")

# A BOM must not read as a broken header.
bom_row = "\t".join([
    "ai_rules_1c", "content/a.md", "-", digest(b"one\n"), "copy", "-",
    "project-managed", "a.md", digest(b"one\n"),
])
with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    (root / "config").mkdir()
    (root / release.ARTIFACTS_NAME).write_bytes(("\ufeff" + f"{header}\n{bom_row}\n").encode("utf-8"))
    try:
        note(len(release.read_artifacts(root)) == 1, "a ledger with a BOM must be readable")
    except release.ReleaseError as error:
        failures.append(f"a ledger with a BOM must be readable, got {error}")
ledger_case("empty source path", [row(source_path="")], "unsafe source_path")
ledger_case("escaping source path", [row(source_path="../etc/passwd")], "unsafe source_path")
ledger_case("absolute target path", [row(target_path="/etc/hosts")], "unsafe target_path")
ledger_case(
    "two rows into one target",
    [row(source_path="content/a.md"), row(source_path="content/b.md")],
    "deliver into",
)

note(
    any("name must be" in issue for issue in release.validate_release(
        passport(sources=[{"name": {"a": 1}, "repository": "a/b", "commit": "1" * 40}]))),
    "a malformed source name must be a finding, not a crash",
)
note(any("schema_version" in issue for issue in release.validate_release(passport(schema_version=2))), "schema_version is pinned")
note(any("capability" in issue for issue in release.validate_release(passport(capability=""))), "capability must be non-empty")
note(any("inventory_count" in issue for issue in release.validate_release(passport(inventory_count=-1))), "inventory_count must be non-negative")
note(any("SemVer" in issue for issue in release.validate_release(passport(version="01.0.0"))), "SemVer must reject leading zeroes")
note(any("sources" in issue for issue in release.validate_release(passport(sources=[]))), "sources must not be empty")
note(any("dependencies" in issue for issue in release.validate_release(passport(dependencies=[{"name": "x", "class": "maybe", "reason": "y"}]))), "dependency class is checked")
note(any("sha256" in issue for issue in release.validate_release(passport(binaries=[{"name": "x", "sha256": "z", "application_kind": "ordinary"}]))), "binary hash is checked")

# --- the builder against a staging checkout --------------------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw) / "rules"
    staging = Path(raw) / "staging"
    (staging / "content").mkdir(parents=True)
    (staging / "content/a.md").write_bytes(b"one\n")
    subprocess.run(["git", "-C", str(staging), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(staging), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(staging), "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "-qm", "staging"], check=True, capture_output=True,
    )
    head = subprocess.run(
        ["git", "-C", str(staging), "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()

    rows = [row()]
    pinned = passport(sources=[{"name": "ai_rules_1c", "repository": "comol/ai_rules_1c", "commit": head}])
    write_release(root, pinned, rows)

    check = subprocess.run(
        [sys.executable, str(SCRIPTS / "build-capability-release.py"),
         "--contract-root", str(root), "--staging", f"ai_rules_1c={staging}"],
        capture_output=True, text=True,
    )
    note(check.returncode == 0, f"a matching staging must pass: {check.stderr[-300:]}")

    (staging / "content/b.md").write_bytes(b"two\n")
    subprocess.run(["git", "-C", str(staging), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(staging), "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "-qm", "new file"], check=True, capture_output=True,
    )
    check = subprocess.run(
        [sys.executable, str(SCRIPTS / "build-capability-release.py"),
         "--contract-root", str(root), "--staging", f"ai_rules_1c={staging}"],
        capture_output=True, text=True,
    )
    note(check.returncode != 0, "a new upstream file must fail the build")
    note("has no row" in check.stderr, f"the new file must be named: {check.stderr[-200:]}")

    (staging / "content/b.md").unlink()
    (staging / "content/a.md").write_bytes(b"edited upstream\n")
    subprocess.run(["git", "-C", str(staging), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(staging), "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "-qm", "edit"], check=True, capture_output=True,
    )
    check = subprocess.run(
        [sys.executable, str(SCRIPTS / "build-capability-release.py"),
         "--contract-root", str(root), "--staging", f"ai_rules_1c={staging}"],
        capture_output=True, text=True,
    )
    note(check.returncode != 0, "a changed source must fail the build")
    note("source changed" in check.stderr, f"the changed file must be named: {check.stderr[-200:]}")

# --- writing a release is guarded -----------------------------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw) / "rules"
    staging = Path(raw) / "staging"
    staging.mkdir()
    (staging / "a.md").write_bytes(b"one\n")
    subprocess.run(["git", "-C", str(staging), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(staging), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(staging), "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "-qm", "staging"], check=True, capture_output=True,
    )
    head = subprocess.run(
        ["git", "-C", str(staging), "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    rows = [row(source_path="a.md")]
    write_release(root, passport(sources=[{"name": "ai_rules_1c", "repository": "a/b", "commit": head}]), rows)

    def build(*arguments: str):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "build-capability-release.py"), "--contract-root", str(root), *arguments],
            capture_output=True, text=True,
        )

    before = (root / release.RELEASE_NAME).read_bytes()
    result = build("--write")
    note(result.returncode != 0, "writing without staging must be refused")
    note((root / release.RELEASE_NAME).read_bytes() == before, "a refused write must not touch the release")

    # An inventory that disagrees must not be blessed with a fresh id.
    write_release(root, passport(inventory_count=9, sources=[{"name": "ai_rules_1c", "repository": "a/b", "commit": head}]), rows)
    before = (root / release.RELEASE_NAME).read_bytes()
    result = build("--staging", f"ai_rules_1c={staging}", "--write")
    note(result.returncode != 0, "writing over findings must be refused")
    note((root / release.RELEASE_NAME).read_bytes() == before, "a refused write must not touch the release")

    # A staging on the wrong commit is not the pinned source.
    (staging / "b.md").write_bytes(b"two\n")
    subprocess.run(["git", "-C", str(staging), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(staging), "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "-qm", "moved"], check=True, capture_output=True,
    )
    result = build("--staging", f"ai_rules_1c={staging}")
    note(result.returncode != 0, "a staging on another commit must fail")
    note("but the release pins" in result.stderr, f"the commit mismatch must be named: {result.stderr[-200:]}")

    result = build("--staging", str(staging))
    note(result.returncode == 2, "--staging without a name must be rejected")


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

    # A stub git keeps the suite offline and lets both answers be tested.
    # Windows resolves a bare "git" through PATHEXT, so the stub has to be a
    # .cmd there; a POSIX shell script would be ignored and the real git would
    # answer - which is exactly the network call this test must not make.
    stub = root / "stub"
    stub.mkdir()
    if os.name == "nt":
        (stub / "git.cmd").write_text("@echo off\r\necho %FAKE_HEAD%\tHEAD\r\n", encoding="utf-8")
    else:
        (stub / "git").write_text("#!/bin/sh\nprintf '%s\\tHEAD\\n' \"$FAKE_HEAD\"\n", encoding="utf-8")
        (stub / "git").chmod(0o755)
    environment = {**dict(os.environ), "PATH": str(stub) + os.pathsep + os.environ["PATH"]}

    for head, expected in ((("1" * 40), "up to date"), (("2" * 40), "upstream")):
        check = subprocess.run(
            [sys.executable, str(SCRIPTS / "check-upstream-sources.py"), "--contract-root", str(root), "--report-only"],
            capture_output=True, text=True, env={**environment, "FAKE_HEAD": head},
        )
        note(check.returncode == 0, f"the upstream check must stay report-only: {check.stderr[-200:]}")
        note(expected in check.stdout, f"expected '{expected}' in the report, got {check.stdout[:200]}")
    note((root / release.RELEASE_NAME).read_bytes() == before, "the upstream check must not modify the release")


if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} release manifest test(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All release manifest tests passed.")
