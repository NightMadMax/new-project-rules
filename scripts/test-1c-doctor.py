#!/usr/bin/env python3
"""The diagnosis must stay inside its allowlist and must not carry a value out.

Both rules were text in a skill, and text is followed by whoever reads it. The
credential that started this came out of a session file during a broad walk of a
user profile, so "reads only what it declared" is checked by refusal, not by
inspection of the output.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("one_c_doctor", SCRIPTS / "one_c_doctor.py")
assert spec and spec.loader
doctor = importlib.util.module_from_spec(spec)
sys.modules["one_c_doctor"] = doctor
spec.loader.exec_module(doctor)

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


# --- what may be opened ------------------------------------------------------

for relative in (".dev.env", "config/1c-projects.tsv", "configurations/launch/toolkit.launch"):
    note(doctor.allowed(relative), f"the allowlist must include {relative}")

for relative in (
    "../outside.md",                      # escaping the project
    "/etc/passwd",                        # absolute
    ".claude/state/session.json",         # state, where the credential came from
    ".codex/sessions/last.json",
    "logs/agent.log",
    "backups/dev.env",
    "README.md",                          # simply not declared
):
    note(not doctor.allowed(relative), f"the allowlist must refuse {relative}")

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    (root / ".claude/state").mkdir(parents=True)
    (root / ".claude/state/session.json").write_bytes(b'{"token": "ghp_secret"}')
    try:
        doctor.read(root, ".claude/state/session.json")
        failures.append("reading outside the allowlist must be refused, not merely avoided")
    except PermissionError:
        pass

    # --- a value never reaches the report ------------------------------------
    (root / ".dev.env").write_bytes(
        "\n".join([
            "# comment",
            "DEFAULT_PASSWORD=hunter2",
            "API_TOKEN=abcdef123456",
            "CONNECTION=Srvr=host;Ref=erp;",  # noscan - фикстура: сканер обязан её видеть, репозиторий - нет
            "EMPTY_SECRET=",
            "VERIFICATION_DEPTH=full",
        ]).encode("utf-8")
    )
    lines = doctor.settings(root)
    joined = "\n".join(lines)
    for value in ("hunter2", "abcdef123456", "host", "erp"):
        note(value not in joined, f"the value '{value}' must never reach the report: {joined}")
    note(any(line.startswith("DEFAULT_PASSWORD") and doctor.MASK in line for line in lines),
         f"a set secret must be reported as set: {lines}")
    note(any("EMPTY_SECRET" in line and "не задан" in line for line in lines),
         f"an empty secret must be reported as unset: {lines}")
    note(any(line == "VERIFICATION_DEPTH=full" for line in lines),
         f"an ordinary setting must survive unchanged: {lines}")
    note(not any(line.startswith("#") for line in lines), "comments are not settings")

    # --- every row says what it means and what to do -------------------------
    rows = doctor.report(root, names=("docker",))
    note(all(row.status in ("OK", "SKIP", "FAIL") for row in rows), f"unknown status: {rows}")
    note(all(row.action for row in rows), f"a row without a consequence is a number nobody acts on: {rows}")
    note(any(row.component == "реестр баз" for row in rows), "the registry must appear in the report")

    # A missing tool is a SKIP: the project is not broken by an absent optional.
    absent = doctor.tools(names=("no-such-tool",))
    note(absent[0].status == "SKIP", f"a missing tool must be SKIP, not FAIL: {absent}")

    rendered = doctor.render(rows)
    note("hunter2" not in rendered and "ghp_" not in rendered,
         "the rendered report must not carry a secret")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} doctor check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("Doctor checks passed.")
