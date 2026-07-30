#!/usr/bin/env python3
"""Tests for scripts/cli_discovery.py — discovery by launchability.

Fixtures are real files started as real processes: the whole claim of the module
is that a name is not a tool, and a mocked "run" would prove nothing about it.
The Windows-only cases are the ones defect 61 was made of, so on other systems
they are reported as skipped rather than quietly passing.
"""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "cli_discovery.py"
spec = importlib.util.spec_from_file_location("cli_discovery", SCRIPT)
assert spec and spec.loader
discovery = importlib.util.module_from_spec(spec)
# Registered before execution: @dataclass resolves annotations through
# sys.modules, and a module loaded by path is not there unless it is put there.
sys.modules["cli_discovery"] = discovery
spec.loader.exec_module(discovery)

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []
skipped: list[str] = []
WINDOWS = os.name == "nt"


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def working_tool(directory: Path, name: str, output: str = "fixture 1.2.3") -> Path:
    """A binary that starts and answers, written the way the platform runs one."""
    if WINDOWS:
        path = directory / f"{name}.cmd"
        path.write_bytes(f"@echo off\r\necho {output}\r\n".encode("utf-8"))
    else:
        path = directory / name
        path.write_bytes(f"#!/bin/sh\necho '{output}'\n".encode("utf-8"))
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def failing_tool(directory: Path, name: str) -> Path:
    if WINDOWS:
        path = directory / f"{name}.cmd"
        path.write_bytes(b"@echo off\r\necho broken 1>&2\r\nexit /b 3\r\n")
    else:
        path = directory / name
        path.write_bytes(b"#!/bin/sh\necho broken >&2\nexit 3\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def alias_stub(directory: Path, name: str) -> Path:
    """The zero-byte App Execution Alias: resolves like a program, is not one."""
    path = directory / (f"{name}.exe" if WINDOWS else name)
    path.write_bytes(b"")
    if not WINDOWS:
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def environ(*directories: Path) -> dict[str, str]:
    return {
        "PATH": os.pathsep.join(str(directory) for directory in directories),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
    }


with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)

    # --- a working binary is found and reported with its version --------------
    good = root / "good"
    good.mkdir()
    working_tool(good, "tool-ok")
    result = discovery.discover(discovery.Tool(name="tool-ok"), environ(good))
    note(result.status == "ok", f"a startable tool must be ok, got {result.status}: {result.diagnostics}")
    note(result.version == "1.2.3", f"the version must come from what the tool printed, got '{result.version}'")

    # --- nothing anywhere is skipped, and the reason is in the report ---------
    empty = root / "empty"
    empty.mkdir()
    result = discovery.discover(discovery.Tool(name="tool-absent"), environ(empty))
    note(result.status == "skipped", f"an absent tool must be skipped, got {result.status}")
    note(bool(result.diagnostics), "a skipped tool must say what was tried")
    note(result.path == "", "a skipped tool must not report a path")

    # --- a candidate that starts and fails is a diagnostic, not a find --------
    broken = root / "broken"
    broken.mkdir()
    failing_tool(broken, "tool-broken")
    result = discovery.discover(discovery.Tool(name="tool-broken"), environ(broken))
    note(result.status == "skipped", "a non-zero exit code is not a working tool")
    note(any("3" in line for line in result.diagnostics),
         f"the exit code belongs in the diagnostics: {result.diagnostics}")

    # --- defect 61: the stub shadows the working binary on PATH --------------
    # This is the case the whole module exists for. The name resolves — and the
    # first hit cannot run, while the real one is further along the same PATH.
    shadow = root / "shadow"
    shadow.mkdir()
    alias_stub(shadow, "tool-shadowed")
    real = root / "real"
    real.mkdir()
    working_tool(real, "tool-shadowed", "shadowed 4.5.6")
    result = discovery.discover(discovery.Tool(name="tool-shadowed"), environ(shadow, real))
    note(result.status == "ok", f"the working binary behind the stub must win, got {result.diagnostics}")
    note(result.version == "4.5.6", f"the version must be the working binary's, got '{result.version}'")
    note(any("нулевой размер" in line for line in result.diagnostics),
         f"the rejected stub must be named in the diagnostics: {result.diagnostics}")

    # --- the stub is never started -------------------------------------------
    # Starting it opens the Store, which is worse than reporting nothing.
    only_stub = root / "only-stub"
    only_stub.mkdir()
    stub = alias_stub(only_stub, "tool-stub")
    note(discovery.rejected_before_start(stub) != "", "a zero-byte executable must be rejected before it starts")

    # --- installed but not on PATH: found through the declared fallback -------
    # The other half of defect 61: `codex` is absent from PATH on the machine
    # where a working binary sits in the user profile.
    installed = Path.home() / ".npr-discovery-fixture"
    installed.mkdir(exist_ok=True)
    try:
        binary = working_tool(installed, "tool-offpath", "offpath 7.8.9")
        tool = discovery.Tool(name="tool-offpath", fallbacks=(f"~/{installed.name}/{binary.name}",))
        result = discovery.discover(tool, environ(empty))
        note(result.status == "ok", f"a binary outside PATH must be found by fallback: {result.diagnostics}")
        note(result.path == str(binary), f"the fallback path must be reported, got '{result.path}'")
    finally:
        for leftover in installed.glob("*"):
            leftover.unlink()
        installed.rmdir()

    # --- PATH is enumerated fully, not by first match ------------------------
    note(len(discovery.path_candidates("tool-shadowed", environ(shadow, real))) == 2,
         "every PATH hit must be a candidate, not only the first")

    # --- the known tools declare a probe and are addressable by name ---------
    for name in ("codex", "claude", "1cedtcli"):
        note(name in discovery.TOOLS, f"{name} must be a known tool")
        note(bool(discovery.TOOLS[name].probe), f"{name} must declare how it is started")

    # --- skipped is not a failure -------------------------------------------
    import subprocess

    run = subprocess.run([sys.executable, str(SCRIPT), "tool-absent"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    note(run.returncode == 0, f"a skipped tool must not fail the run: exit {run.returncode}")
    note("skip" in run.stdout, f"the report must show the skip: {run.stdout!r}")
    run = subprocess.run([sys.executable, str(SCRIPT), "tool-absent", "--require"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    note(run.returncode == 1, "with --require a skipped tool is an error")

if not WINDOWS:
    skipped.append("зависимость от App Execution Alias проверяется только на Windows")

for message in skipped:
    print(f"SKIP: {message}")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} discovery check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("CLI discovery checks passed.")
