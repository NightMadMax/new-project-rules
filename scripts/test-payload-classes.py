#!/usr/bin/env python3
"""Delivery classes: templates are substituted, payloads arrive byte for byte.

The test copies the rules repository into a scratch directory and appends
capability rows there, so the real manifest is never touched. A payload fixture
deliberately contains the placeholders and a NUL byte: substitution or text
processing would rewrite it and change its hash.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = "jira-confluence"
# Invalid UTF-8 on purpose: bytes that survive a text round-trip would let a
# Get-Content/Set-Content style regression pass unnoticed. CRLF is here to catch
# line-ending normalisation, including the one Git would apply on commit.
PAYLOAD = b"<PROJECT_NAME> <YYYY-MM-DD>\r\n\xff\xfe\x00\x80 binary tail\r\n"
failures: list[str] = []


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(workspace: Path) -> Path:
    """Copy the working tree, not HEAD.

    A git worktree would check out the last commit and quietly test the old
    bootstrap; the point here is to exercise the code as it stands.
    """
    contract = workspace / "rules"
    shutil.copytree(
        ROOT, contract, symlinks=True,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "venv", "node_modules"),
    )
    templates = contract / "templates" / "new-project" / "capabilities" / CAPABILITY
    (templates / "payload").mkdir(parents=True, exist_ok=True)
    (templates / "payload" / "VERBATIM.md").write_bytes(PAYLOAD)
    (templates / "payload" / "BINARY.bin").write_bytes(PAYLOAD)
    (templates / "payload" / "TEMPLATE.md").write_bytes(b"# <PROJECT_NAME>\n")
    (templates / "payload" / "DASH.md").write_bytes(b"# <PROJECT_NAME>\n")
    executable = templates / "payload" / "tool.sh"
    executable.write_bytes(b"#!/bin/sh\necho tool\n")
    executable.chmod(0o755)

    manifest = contract / "config" / "capabilities.tsv"
    rows = manifest.read_text(encoding="utf-8").rstrip("\n").split("\n")
    for source, destination, payload_class in (
        ("payload/VERBATIM.md", "payload/VERBATIM.md", "verbatim"),
        ("payload/BINARY.bin", "payload/BINARY.bin", "binary"),
        ("payload/TEMPLATE.md", "payload/TEMPLATE.md", "template"),
        ("payload/DASH.md", "payload/DASH.md", "-"),
        ("payload/tool.sh", "payload/tool.sh", "verbatim"),
    ):
        rows.append("\t".join([
            CAPABILITY, f"capabilities/{CAPABILITY}/{source}", destination, "-", "-", "-", payload_class,
        ]))
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")

    # Bootstrap records the rules commit as provenance, so the copy needs one.
    git = ["git", "-C", str(contract), "-c", "user.name=test", "-c", "user.email=test@example.com"]
    subprocess.run(git[:3] + ["init"], check=True, capture_output=True)
    subprocess.run(git[:3] + ["add", "-A"], check=True, capture_output=True)
    subprocess.run(git + ["commit", "-m", "payload fixtures"], check=True, capture_output=True)
    return contract


def check_project(project: Path, label: str) -> None:
    for name in ("payload/VERBATIM.md", "payload/BINARY.bin"):
        delivered = project / name
        if not delivered.is_file():
            failures.append(f"{label}: {name} was not delivered")
            continue
        if digest(delivered.read_bytes()) != digest(PAYLOAD):
            failures.append(f"{label}: {name} was modified in delivery")

    # Both spellings of the default class must still be substituted.
    for name in ("payload/TEMPLATE.md", "payload/DASH.md"):
        template = project / name
        if not template.is_file():
            failures.append(f"{label}: {name} was not delivered")
        elif "<PROJECT_NAME>" in template.read_bytes().decode("utf-8"):
            failures.append(f"{label}: {name} placeholders were not substituted")

    tool = project / "payload" / "tool.sh"
    if not tool.is_file():
        failures.append(f"{label}: executable payload was not delivered")
    elif os.name != "nt" and not os.access(tool, os.X_OK):
        failures.append(f"{label}: executable payload lost its exec bit")

    # Byte-exactness must survive the commit bootstrap makes, not just the copy.
    committed = subprocess.run(
        ["git", "-C", str(project), "show", "HEAD:payload/VERBATIM.md"],
        capture_output=True,
    )
    if committed.returncode != 0:
        failures.append(f"{label}: payload is not in the initial commit")
    elif digest(committed.stdout) != digest(PAYLOAD):
        failures.append(f"{label}: payload was normalised when committed")


def shell_bootstrap(contract: Path, destination: Path):
    """Run the POSIX entry point; forward slashes keep it usable on Windows."""
    if not shutil.which("sh"):
        print("SKIP: sh is not available on this machine")
        return None
    return subprocess.run(
        ["sh", (contract / "scripts" / "bootstrap-new-project.sh").as_posix(),
         destination.as_posix(), "demo", "operated", CAPABILITY],
        capture_output=True, text=True,
    )


def powershell_bootstrap(contract: Path, destination: Path):
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        print("SKIP: PowerShell is not available on this machine")
        return None
    script = (contract / "scripts" / "bootstrap-new-project.ps1").as_posix()
    return subprocess.run(
        [pwsh, "-NoProfile", "-Command",
         f"& '{script}' -ProjectName demo -Destination '{destination.as_posix()}' "
         f"-Profile operated -Capability {CAPABILITY}"],
        capture_output=True, text=True,
    )


def run_bootstrap(contract: Path, workspace: Path, runner, label: str) -> None:
    destination = workspace / f"{label}-project"
    result = runner(contract, destination)
    if result is None:
        return
    if result.returncode != 0:
        failures.append(f"{label} bootstrap failed: {result.stderr.strip()[:400]}")
        return
    check_project(destination, label)


def run_unknown_class(contract: Path, workspace: Path, runner, label: str) -> None:
    """An unknown class must stop the run instead of guessing a delivery mode."""
    manifest = contract / "config" / "capabilities.tsv"
    original = manifest.read_text(encoding="utf-8")
    manifest.write_text(original.replace("\tverbatim\n", "\tmystery\n", 1), encoding="utf-8")
    destination = workspace / f"rejected-{label}"
    try:
        result = runner(contract, destination)
        if result is None:
            return
        if result.returncode == 0:
            failures.append(f"{label}: an unknown payload class was accepted")
        if "payload class" not in (result.stderr + result.stdout):
            failures.append(f"{label}: the unknown payload class was not explained")
        if destination.exists() and any(destination.iterdir()):
            failures.append(f"{label}: a rejected run left files behind")
    finally:
        manifest.write_text(original, encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        workspace = Path(raw)
        contract = prepare(workspace)
        runners = ((shell_bootstrap, "shell"), (powershell_bootstrap, "powershell"))
        for runner, label in runners:
            run_bootstrap(contract, workspace, runner, label)
        for runner, label in runners:
            run_unknown_class(contract, workspace, runner, label)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"{len(failures)} payload class check(s) failed.", file=sys.stderr)
        return 1
    print("All payload class checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
