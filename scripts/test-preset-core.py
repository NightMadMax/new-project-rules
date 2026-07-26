#!/usr/bin/env python3
"""Preset expansion and the core invariant it protects.

A preset is a name a person uses at creation; what the project stores is what
the preset expanded into. Two things must hold: both bootstrap implementations
expand it identically, and the resulting core cannot be quietly downgraded
later.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import project_metadata  # noqa: E402

spec = importlib.util.spec_from_file_location("presets", SCRIPTS / "presets.py")
assert spec and spec.loader
presets = importlib.util.module_from_spec(spec)
sys.modules["presets"] = presets
spec.loader.exec_module(presets)

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com",
}
failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def metadata_of(project: Path) -> dict:
    return json.loads((project / ".project-standard.json").read_text(encoding="utf-8"))


def tree_of(project: Path) -> list[str]:
    return sorted(
        str(path.relative_to(project)).replace("\\", "/")
        for path in project.rglob("*")
        if path.is_file() and ".git/" not in str(path.relative_to(project)).replace("\\", "/")
    )


def run_shell(destination: Path, *arguments: str):
    if not shutil.which("sh"):
        return None
    return subprocess.run(
        ["sh", (SCRIPTS / "bootstrap-new-project.sh").as_posix(), destination.as_posix(), "demo", *arguments],
        capture_output=True, text=True, env={**dict(__import__("os").environ), **GIT_IDENTITY},
    )


def run_shell_raw(*arguments: str):
    """Call the shell entry point with exactly these arguments."""
    if not shutil.which("sh"):
        return None
    return subprocess.run(
        ["sh", (SCRIPTS / "bootstrap-new-project.sh").as_posix(), *arguments],
        capture_output=True, text=True, env={**dict(__import__("os").environ), **GIT_IDENTITY},
    )


def run_powershell(destination: Path, *arguments: str):
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        return None
    script = (SCRIPTS / "bootstrap-new-project.ps1").as_posix()
    command = f"& '{script}' -Destination '{destination.as_posix()}' -ProjectName demo " + " ".join(arguments)
    return subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        capture_output=True, text=True, env={**dict(__import__("os").environ), **GIT_IDENTITY},
    )


# --- expansion contract ----------------------------------------------------

profile, capabilities, stacks = presets.resolve(ROOT, "1c", "minimal", [])
note(profile == "operated", f"a lighter profile must be raised to the floor, got {profile}")
note(capabilities == ["1c"], f"unexpected capabilities: {capabilities}")
note(stacks == ["1c"], f"unexpected stacks: {stacks}")

profile, capabilities, _ = presets.resolve(ROOT, "1c", "all", ["jira-confluence"])
note(profile == "all", "a higher profile must not be lowered")
note(capabilities == ["jira-confluence", "1c"], f"capabilities must merge without duplicates: {capabilities}")

try:
    presets.resolve(ROOT, "ghost", "minimal", [])
    failures.append("an unknown preset must be rejected")
except presets.PresetError:
    pass

# --- the manifest reader ---------------------------------------------------

HEADER = "preset\tmin_profile\tcapabilities\tbest_practices\n"


def manifest_case(name: str, body: str, expect: str | None) -> None:
    with tempfile.TemporaryDirectory() as raw:
        contract = Path(raw)
        (contract / "config").mkdir()
        (contract / "config/presets.tsv").write_bytes(body.encode("utf-8"))
        try:
            presets.read_presets(contract)
            issue = None
        except presets.PresetError as error:
            issue = str(error)
        if expect is None:
            note(issue is None, f"{name}: expected no error, got {issue}")
        else:
            note(issue is not None and expect in issue, f"{name}: expected '{expect}', got {issue}")


manifest_case("healthy manifest", HEADER + "1c\toperated\t1c\t1c\n", None)
manifest_case("bad header", "preset\tmin_profile\n1c\toperated\n", "Unexpected header")
manifest_case("row too short", HEADER + "1c\toperated\n", "does not match the header")
manifest_case("duplicate preset", HEADER + "1c\toperated\t1c\t1c\n1c\tall\t1c\t1c\n", "duplicate preset")
manifest_case("unknown profile", HEADER + "1c\tmystery\t1c\t1c\n", "unknown profile")
manifest_case("unknown capability", HEADER + "1c\toperated\tghost\t1c\n", "unknown capability")
manifest_case("unknown stack", HEADER + "1c\toperated\t1c\tghost\n", "unknown practice stack")
manifest_case("no presets", HEADER, "declares no presets")
manifest_case("missing manifest", "", "Unexpected header")

note(presets.split("-") == [], "a dash must mean 'nothing'")
note(presets.split("a,,b") == ["a", "b"], "empty entries must be dropped")

try:
    presets.resolve(Path("."), "1c", "mystery", [])
    failures.append("an unknown profile must be rejected")
except presets.PresetError:
    pass

# --- the core invariant ----------------------------------------------------

known = ["0001-adopt-project-standard"]
metadata = project_metadata.build_legacy_metadata(
    5, "software", "NightMadMax/new-project-rules", "0" * 40, known, capabilities=["1c"],
)
issues = project_metadata.validate_metadata(metadata, 5, "NightMadMax/new-project-rules", known)
note(any("requires profile" in issue for issue in issues), f"a downgraded core must be rejected: {issues}")

metadata["profile"] = "operated"
issues = project_metadata.validate_metadata(metadata, 5, "NightMadMax/new-project-rules", known)
note(not issues, f"an operated 1C project must validate: {issues}")

metadata["profile"] = "all"
note(
    not project_metadata.validate_metadata(metadata, 5, "NightMadMax/new-project-rules", known),
    "a higher profile must remain valid",
)

# --- the core follows the capability, not the preset -----------------------

core_rows = [
    line.split("\t")
    for line in (ROOT / "config/capability-core.tsv").read_text(encoding="utf-8").rstrip("\n").split("\n")[1:]
]
declared = {row[0]: {"min_profile": row[1], "stack": row[2]} for row in core_rows}
note(
    declared == project_metadata.CAPABILITY_CORE,
    f"config/capability-core.tsv and CAPABILITY_CORE disagree: {declared} vs {project_metadata.CAPABILITY_CORE}",
)

with tempfile.TemporaryDirectory() as raw:
    workspace = Path(raw)
    for label, runner, arguments in (
        ("shell", run_shell, ("minimal", "1c")),
        ("powershell", run_powershell, ("-Profile", "minimal", "-Capability", "1c")),
    ):
        destination = workspace / label
        result = runner(destination, *arguments)
        if result is None:
            continue
        note(result.returncode == 0, f"{label}: a positional capability must be accepted: {result.stderr[:200]}")
        if result.returncode != 0:
            continue
        data = metadata_of(destination)
        note(data["profile"] == "operated", f"{label}: the core must raise the profile, got {data['profile']}")
        manifest = destination / ".best-practices.json"
        note(manifest.is_file(), f"{label}: the core stack was not recorded without a preset")
        check = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate-project.py"), "--root", str(destination), "--report-only"],
            capture_output=True, text=True,
        )
        note("0 error(s)" in check.stdout, f"{label}: choosing a capability directly must not create an invalid project")


# --- a declined stack breaks the core -------------------------------------

with tempfile.TemporaryDirectory() as raw:
    destination = Path(raw) / "declined"
    result = run_shell(destination, "minimal", "--preset", "1c")
    if result is not None and result.returncode == 0:
        manifest = destination / ".best-practices.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["preferences"]["sections"]["1c"] = "optout"
        manifest.write_text(json.dumps(data), encoding="utf-8")
        check = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate-project.py"), "--root", str(destination), "--report-only"],
            capture_output=True, text=True,
        )
        note("capability.stack_declined" in check.stdout, f"a declined stack must break the core: {check.stdout[-200:]}")

        data = json.loads(json.dumps({"schema_version": 2, "preferences": {"global": "ask", "sections": {}}, "practices": {}}))
        manifest.write_text(json.dumps(data), encoding="utf-8")
        check = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate-project.py"), "--root", str(destination), "--report-only"],
            capture_output=True, text=True,
        )
        note("capability.stack_missing" in check.stdout, f"an unrecorded stack must break the core: {check.stdout[-200:]}")

        data["preferences"] = {"global": "optout", "sections": {"1c": "ask"}}
        manifest.write_text(json.dumps(data), encoding="utf-8")
        check = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate-project.py"), "--root", str(destination), "--report-only"],
            capture_output=True, text=True,
        )
        note("capability.stack_declined" in check.stdout, f"a globally declined base must break the core: {check.stdout[-200:]}")

        manifest.unlink()
        check = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate-project.py"), "--root", str(destination), "--report-only"],
            capture_output=True, text=True,
        )
        note("capability.stack_missing" in check.stdout, f"a missing manifest must break the core: {check.stdout[-200:]}")

        manifest.write_text("{not json", encoding="utf-8")
        check = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate-project.py"), "--root", str(destination), "--report-only"],
            capture_output=True, text=True,
        )
        note("capability.stack_unreadable" in check.stdout, f"an unreadable manifest must be reported: {check.stdout[-200:]}")


# --- argument handling ------------------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    workspace = Path(raw)
    empty_name = run_shell_raw((workspace / "empty-name").as_posix(), "", "minimal")
    if empty_name is not None:
        note(empty_name.returncode != 0, "shell: an empty project name must be rejected")
        note("must not be empty" in empty_name.stderr, f"shell: unclear message: {empty_name.stderr[:120]}")

    twice = run_shell(workspace / "twice", "minimal", "--preset", "1c", "--preset", "1c")
    if twice is not None:
        note(twice.returncode != 0, "shell: --preset given twice must be rejected")

    wrong_case = run_powershell(workspace / "case", "-Capability", "1C")
    if wrong_case is not None:
        note(wrong_case.returncode != 0, "powershell: capability names must be case-sensitive")

    wrong_case_shell = run_shell(workspace / "case-shell", "minimal", "1C")
    if wrong_case_shell is not None:
        note(wrong_case_shell.returncode != 0, "shell: capability names must be case-sensitive")


# --- both implementations agree -------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    workspace = Path(raw)
    results = {}
    for label, runner in (("shell", run_shell), ("powershell", run_powershell)):
        destination = workspace / label
        arguments = ["minimal", "--preset", "1c"] if label == "shell" else ["-Profile", "minimal", "-Preset", "1c"]
        result = runner(destination, *arguments)
        if result is None:
            print(f"SKIP: {label} is not available on this machine")
            continue
        if result.returncode != 0:
            failures.append(f"{label} bootstrap failed: {result.stderr.strip()[:300]}")
            continue
        results[label] = destination

        data = metadata_of(destination)
        note(data["profile"] == "operated", f"{label}: preset must raise the profile, got {data['profile']}")
        note(data["capabilities"] == ["1c"], f"{label}: unexpected capabilities {data['capabilities']}")

        manifest = destination / ".best-practices.json"
        note(manifest.is_file(), f"{label}: the preset stack was not recorded")
        if manifest.is_file():
            body = manifest.read_text(encoding="utf-8")
            sections = json.loads(body)["preferences"]["sections"]
            note(sections.get("1c") == "ask", f"{label}: stack must be connected, got {sections}")
            # The file belongs to best_practices_manifest.py; bootstrap must
            # write exactly what that tool would, or the first update rewrites it.
            canonical = json.dumps(json.loads(body), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            note(body == canonical, f"{label}: manifest is not in canonical form")

        check = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate-project.py"), "--root", str(destination), "--report-only"],
            capture_output=True, text=True,
        )
        note("0 error(s)" in check.stdout, f"{label}: a freshly created project must validate: {check.stdout[-300:]}")

    if len(results) == 2:
        shell_tree, powershell_tree = tree_of(results["shell"]), tree_of(results["powershell"])
        note(shell_tree == powershell_tree, "the two implementations produced different projects")
        note(
            metadata_of(results["shell"])["capabilities"] == metadata_of(results["powershell"])["capabilities"],
            "the two implementations recorded different capabilities",
        )
        note(
            (results["shell"] / ".best-practices.json").read_bytes()
            == (results["powershell"] / ".best-practices.json").read_bytes(),
            "the two implementations wrote different practice manifests",
        )

# --- rejections ------------------------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    workspace = Path(raw)
    for label, runner, arguments in (
        ("shell", run_shell, ("minimal", "--preset", "ghost")),
        ("powershell", run_powershell, ("-Preset", "ghost")),
        ("shell", run_shell, ("minimal", "ghost")),
        ("powershell", run_powershell, ("-Capability", "ghost")),
    ):
        destination = workspace / f"{label}-{arguments[-1]}-{len(list(workspace.iterdir()))}"
        result = runner(destination, *arguments)
        if result is None:
            continue
        note(result.returncode != 0, f"{label}: '{arguments[-1]}' must be rejected")
        note(not destination.exists() or not any(destination.iterdir()),
             f"{label}: a rejected run must leave nothing behind")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} preset core check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All preset core checks passed.")
