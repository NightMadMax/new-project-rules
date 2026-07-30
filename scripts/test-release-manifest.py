#!/usr/bin/env python3
"""Tests for the release passport, the artifact ledger and the builder."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
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
        "sources": [
            {"name": "ai_rules_1c", "repository": "comol/ai_rules_1c", "commit": "1" * 40},
            {"name": "best-practices", "repository": "NightMadMax/best-practices", "commit": "2" * 40},
        ],
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
    pinned = passport(sources=[
        {"name": "ai_rules_1c", "repository": "comol/ai_rules_1c", "commit": head},
        {"name": "best-practices", "repository": "NightMadMax/best-practices", "commit": "2" * 40},
    ])
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

# --- the gate runs on the checkout the build is given ----------------------


def git_staging(path: Path, files: dict[str, str]) -> str:
    for name, body in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body.encode("utf-8"))
    subprocess.run(["git", "-C", str(path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "-qm", "staging"], check=True, capture_output=True,
    )
    return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


ACCEPTED = ("---\nid: PC-2026-000000000000\nstatus: accepted\n"
            "evidence: \"два подтверждения\"\n---\n\n# Практика\n")
EMPTY_INDEX = "# Индекс\n\nПринятых практик пока нет.\n"

for case, files, expect_zero in (
    ("an empty stack blocks the build", {"practices/1c/README.md": EMPTY_INDEX}, False),
    ("an accepted practice lets it through",
     {"practices/1c/README.md": EMPTY_INDEX, "practices/1c/PC-2026-000000000000-x.md": ACCEPTED}, True),
):
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw) / "rules"
        upstream = Path(raw) / "upstream"
        (upstream / "content").mkdir(parents=True)
        upstream_head = git_staging(upstream, {"content/a.md": "one\n"})
        practices = Path(raw) / "best-practices"
        practices.mkdir()
        practices_head = git_staging(practices, files)

        write_release(root, passport(sources=[
            {"name": "ai_rules_1c", "repository": "comol/ai_rules_1c", "commit": upstream_head},
            {"name": "best-practices", "repository": "NightMadMax/best-practices", "commit": practices_head},
        ]), [row()])

        check = subprocess.run(
            [sys.executable, str(SCRIPTS / "build-capability-release.py"),
             "--contract-root", str(root),
             "--staging", f"ai_rules_1c={upstream}", "--staging", f"best-practices={practices}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        note((check.returncode == 0) == expect_zero,
             f"{case}: exit {check.returncode}, {check.stderr[-300:]}")
        if not expect_zero:
            note("practices/1c" in check.stderr, f"{case}: the stack must be named: {check.stderr[-200:]}")
            note("blocked" in check.stdout, f"{case}: the status must be printed: {check.stdout[-200:]}")


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

    # Import the checker and replace its command runner: a PATH stub cannot
    # work here, because a Python subprocess on Windows resolves a bare "git"
    # only to git.exe. Faking at the seam keeps the suite offline everywhere.
    upstream_spec = importlib.util.spec_from_file_location("check_upstream", SCRIPTS / "check-upstream-sources.py")
    assert upstream_spec and upstream_spec.loader
    upstream = importlib.util.module_from_spec(upstream_spec)
    sys.modules["check_upstream"] = upstream
    upstream_spec.loader.exec_module(upstream)

    class FakeResult:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    for head, expected in ((("1" * 40), "up to date"), (("2" * 40), "upstream")):
        calls: list[list[str]] = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return FakeResult(f"{head}\tHEAD\n")

        real_run = upstream.subprocess.run
        upstream.subprocess.run = fake_run
        captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(captured):
                code = upstream.main(["--contract-root", str(root), "--report-only"])
        finally:
            upstream.subprocess.run = real_run
        note(code == 0, f"the upstream check must stay report-only, got {code}")
        note(expected in captured.getvalue(), f"expected '{expected}' in the report, got {captured.getvalue()[:200]}")
        note(bool(calls), "the upstream check must actually ask git")

    # Without --report-only a moved source is a signal a person can act on.
    def moved_run(command, **kwargs):
        return FakeResult(f"{'2' * 40}\tHEAD\n")

    real_run = upstream.subprocess.run
    upstream.subprocess.run = moved_run
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            code = upstream.main(["--contract-root", str(root)])
    finally:
        upstream.subprocess.run = real_run
    note(code == 1, f"drift must be reported with a non-zero code, got {code}")

    note((root / release.RELEASE_NAME).read_bytes() == before, "the upstream check must not modify the release")


# --- the mandatory core stack must hold a practice (decision 1.29) ----------


def practice(status: str, evidence: str = "две проверки") -> str:
    return (
        "---\n"
        "id: PC-2026-000000000000\n"
        f"status: {status}\n"
        f"evidence: \"{evidence}\"\n"
        "---\n\n# Практика\n"
    )


with tempfile.TemporaryDirectory() as raw:
    checkout = Path(raw)
    stack = checkout / release.PRACTICE_DIRECTORY

    # The directory does not exist at all: the checkout is not a Best Practices
    # base, and saying "no practice" would describe the wrong problem.
    note(release.release_status(release.practice_gate(checkout)) == "blocked",
         "a missing practices directory must block the release")
    note(any("does not exist" in finding for finding in release.practice_gate(checkout)),
         "the finding must name the missing directory")

    stack.mkdir(parents=True)
    (stack / "README.md").write_bytes("# Индекс\n".encode("utf-8"))
    note(any("holds no practice" in finding for finding in release.practice_gate(checkout)),
         "an index without practices must block: the README is not a practice")

    # A trial practice is a promise, not a delivery: E1 is one confirmation.
    (stack / "PC-2026-000000000000-trial.md").write_bytes(practice("trial").encode("utf-8"))
    findings = release.practice_gate(checkout)
    note(release.release_status(findings) == "blocked", "a trial practice must not open the gate")
    note(any("status=trial" in finding for finding in findings),
         f"the finding must name what was found instead: {findings}")

    # Accepted with an empty evidence field is a status somebody typed, not a
    # confirmation somebody has.
    (stack / "PC-2026-000000000000-trial.md").unlink()
    (stack / "PC-2026-000000000001-empty.md").write_bytes(practice("accepted", "").encode("utf-8"))
    note(release.release_status(release.practice_gate(checkout)) == "blocked",
         "an accepted practice without evidence must not open the gate")

    (stack / "PC-2026-000000000002-real.md").write_bytes(practice("accepted").encode("utf-8"))
    note(release.practice_gate(checkout) == [], "an accepted practice with evidence opens the gate")

# --- the gate cannot be skipped by not mentioning it ------------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    unpinned = passport(sources=[{"name": "ai_rules_1c", "repository": "comol/ai_rules_1c", "commit": "1" * 40}])
    write_release(root, unpinned, [row()])
    findings = release.check_release(root)
    note(any("mandatory core stack" in finding for finding in findings),
         f"a passport that does not pin Best Practices must be blocked: {findings}")
    note(release.release_status(findings) == "blocked", "the unpinned core stack must block, not warn")


# --- three outcomes, not one list ------------------------------------------

note(release.release_status([]) == "ready", "no findings means ready")
note(release.release_status([release.Finding(release.REVIEW, "content changed")]) == "review-required",
     "a review finding alone must not read as blocked")
note(release.release_status([
    release.Finding(release.REVIEW, "content changed"),
    release.Finding(release.BLOCKED, "inventory is incomplete"),
]) == "blocked", "one blocking finding decides the outcome")
# An unclassified finding is not a finding somebody decided was safe.
note(release.release_status(["a plain string"]) == "blocked", "a finding without severity must block")
note(all(getattr(finding, "severity", None) == release.BLOCKED
         for finding in release.check_release(Path(tempfile.gettempdir()) / "no-such-release-root")),
     "an unreadable release is a blocking finding")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} release manifest test(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All release manifest tests passed.")
