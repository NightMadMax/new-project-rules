#!/usr/bin/env python3
"""Delivery classes: templates are substituted, payloads arrive byte for byte.

The test copies the rules repository into a scratch directory and appends
capability rows there, so the real manifest is never touched. A payload fixture
deliberately contains the placeholders and a NUL byte: substitution or text
processing would rewrite it and change its hash.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = "jira-confluence"
PAYLOAD = b"<PROJECT_NAME> <YYYY-MM-DD> <SCHEMA_VERSION>\n\x00\x01\x02 binary tail\n"
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
        ROOT, contract,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "venv", "node_modules"),
    )
    templates = contract / "templates" / "new-project" / "capabilities" / CAPABILITY
    (templates / "payload").mkdir(parents=True, exist_ok=True)
    (templates / "payload" / "VERBATIM.md").write_bytes(PAYLOAD)
    (templates / "payload" / "BINARY.bin").write_bytes(PAYLOAD)
    (templates / "payload" / "TEMPLATE.md").write_bytes(b"# <PROJECT_NAME>\n")

    manifest = contract / "config" / "capabilities.tsv"
    rows = manifest.read_text(encoding="utf-8").rstrip("\n").split("\n")
    for source, destination, payload_class in (
        ("payload/VERBATIM.md", "payload/VERBATIM.md", "verbatim"),
        ("payload/BINARY.bin", "payload/BINARY.bin", "binary"),
        ("payload/TEMPLATE.md", "payload/TEMPLATE.md", "template"),
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
    template = project / "payload" / "TEMPLATE.md"
    if not template.is_file():
        failures.append(f"{label}: template artifact was not delivered")
    elif "<PROJECT_NAME>" in template.read_text(encoding="utf-8"):
        failures.append(f"{label}: template placeholders were not substituted")


def run_shell(contract: Path, workspace: Path) -> None:
    destination = workspace / "sh-project"
    result = subprocess.run(
        ["sh", str(contract / "scripts" / "bootstrap-new-project.sh"),
         str(destination), "demo", "operated", CAPABILITY],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        failures.append(f"shell bootstrap failed: {result.stderr.strip()[:400]}")
        return
    check_project(destination, "shell")


def run_powershell(contract: Path, workspace: Path) -> None:
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        print("SKIP: PowerShell is not available on this machine")
        return
    destination = workspace / "ps-project"
    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command",
         f"& '{contract / 'scripts' / 'bootstrap-new-project.ps1'}' -ProjectName demo "
         f"-Destination '{destination}' -Profile operated -Capability {CAPABILITY}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        failures.append(f"PowerShell bootstrap failed: {result.stderr.strip()[:400]}")
        return
    check_project(destination, "PowerShell")


def run_unknown_class(contract: Path, workspace: Path) -> None:
    """An unknown class must stop the run instead of guessing a delivery mode."""
    manifest = contract / "config" / "capabilities.tsv"
    original = manifest.read_text(encoding="utf-8")
    manifest.write_text(original.replace("\tverbatim\n", "\tmystery\n", 1), encoding="utf-8")
    try:
        result = subprocess.run(
            ["sh", str(contract / "scripts" / "bootstrap-new-project.sh"),
             str(workspace / "rejected"), "demo", "operated", CAPABILITY],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            failures.append("shell bootstrap accepted an unknown payload class")
        if "payload class" not in (result.stderr + result.stdout):
            failures.append("shell bootstrap did not explain the unknown payload class")
    finally:
        manifest.write_text(original, encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        workspace = Path(raw)
        contract = prepare(workspace)
        run_shell(contract, workspace)
        run_powershell(contract, workspace)
        run_unknown_class(contract, workspace)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        print(f"{len(failures)} payload class check(s) failed.", file=sys.stderr)
        return 1
    print("All payload class checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
