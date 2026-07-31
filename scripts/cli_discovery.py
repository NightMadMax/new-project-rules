#!/usr/bin/env python3
"""Discovery of a CLI by launchability, not by the presence of a name.

A name on PATH is not a tool. On Windows an App Execution Alias is a zero-byte
reparse point that resolves like an executable and then refuses to run — defect
61 was exactly this: `codex` resolved into WindowsApps and PowerShell answered
"Отказано в доступе", while a working binary sat in the user profile all along.
The inverse happens just as often: the working binary is installed but not on
PATH, so a name check reports "missing" about a tool that starts fine.

So a candidate is accepted only after it has actually started and answered. A
tool that answers nowhere is `skipped` with the list of what was tried and why
each candidate was rejected — never a bare "not found", because the diagnosis is
the whole value: the user has to learn whether to install the tool or to fix the
PATH.

`skipped` is not a failure. Not every task needs every tool, and the caller
decides what a missing one costs.
"""

from __future__ import annotations

import argparse
import json
import locale
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

VERSION_RE = re.compile(r"\d+\.\d+[\w.+-]*")
DEFAULT_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class Tool:
    """What to start and where to look for it when PATH does not have it.

    `fallbacks` are globs against the home directory or an absolute root: an
    installer that does not touch PATH still puts the binary in a predictable
    place, and naming that place is cheaper than telling the user to hunt.
    """

    name: str
    probe: tuple[str, ...] = ("--version",)
    fallbacks: tuple[str, ...] = ()
    timeout: int = DEFAULT_TIMEOUT_SECONDS
    note: str = ""
    # Only where the install path really carries the version. Applied to every
    # tool it would report the version of whatever runtime happens to sit in the
    # path — "python3.12" in a directory name is not the tool's version.
    version_in_path: bool = False


TOOLS: dict[str, Tool] = {
    "codex": Tool(
        name="codex",
        fallbacks=(
            "~/.codex/plugins/.plugin-appserver/codex.exe",
            "~/.codex/bin/codex*",
            "~/.local/bin/codex*",
            "~/AppData/Roaming/npm/codex*",
            "~/.npm-global/bin/codex",
        ),
        note="агент Codex",
    ),
    "claude": Tool(
        name="claude",
        fallbacks=(
            "~/.local/bin/claude*",
            "~/.claude/local/claude*",
            "~/AppData/Roaming/npm/claude*",
            "~/.npm-global/bin/claude",
        ),
        note="агент Claude Code",
    ),
    "1cedtcli": Tool(
        name="1cedtcli",
        # `-command version` boots the JVM and a workspace; usage output answers
        # the only question discovery asks — does this binary start at all.
        probe=("-help",),
        fallbacks=(
            "C:/Program Files/1C/1CE/components/1c-edt-*/1cedtcli.exe",
            "C:/Program Files (x86)/1C/1CE/components/1c-edt-*/1cedtcli.exe",
            "~/AppData/Local/Programs/1C/1CE/components/1c-edt-*/1cedtcli.exe",
            "/opt/1C/1CE/components/1c-edt-*/1cedtcli",
            "~/.local/share/1C/1CE/components/1c-edt-*/1cedtcli",
        ),
        timeout=90,
        note="CLI 1C:EDT для конвертации формата исходников",
        # `-help` prints usage without a version; the component directory is
        # named after the EDT release it belongs to.
        version_in_path=True,
    ),
    "docker": Tool(name="docker", note="внешний MCP provider"),
    "git": Tool(name="git", note="версионирование"),
    "gh": Tool(name="gh", note="GitHub CLI"),
}


@dataclass
class Result:
    tool: str
    status: str  # "ok" | "skipped"
    path: str = ""
    version: str = ""
    detail: str = ""
    diagnostics: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "tool": self.tool,
            "status": self.status,
            "path": self.path,
            "version": self.version,
            "detail": self.detail,
            "diagnostics": list(self.diagnostics),
        }


def path_candidates(name: str, environ: dict[str, str] | None = None) -> list[Path]:
    """Every PATH hit, not the first one.

    `which` answers with the first match, and on Windows the first match is
    routinely the alias stub that cannot run. Stopping there would hide the real
    binary two entries further down the same PATH.
    """
    environ = os.environ if environ is None else environ
    directories = [part for part in environ.get("PATH", "").split(os.pathsep) if part]
    suffixes = [""]
    if os.name == "nt":
        suffixes = [""] + [
            suffix.lower()
            for suffix in environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(os.pathsep)
            if suffix
        ]
    found: list[Path] = []
    for directory in directories:
        for suffix in suffixes:
            candidate = Path(directory) / f"{name}{suffix}"
            if candidate.is_file():
                found.append(candidate)
    return found


def fallback_candidates(tool: Tool) -> list[Path]:
    found: list[Path] = []
    for pattern in tool.fallbacks:
        if pattern.startswith("~"):
            root, glob = Path.home(), pattern[2:]
        else:
            anchor = Path(pattern).anchor
            root, glob = Path(anchor), pattern[len(anchor):]
        try:
            matches = sorted(root.glob(glob))
        except (OSError, ValueError):
            continue
        found.extend(match for match in matches if match.is_file())
    return found


def candidates(tool: Tool, environ: dict[str, str] | None = None) -> list[Path]:
    ordered: list[Path] = []
    seen: set[str] = set()
    for candidate in path_candidates(tool.name, environ) + fallback_candidates(tool):
        key = str(candidate).lower() if os.name == "nt" else str(candidate)
        if key not in seen:
            seen.add(key)
            ordered.append(candidate)
    return ordered


def rejected_before_start(candidate: Path) -> str:
    """Why not even to try. Empty string means: go ahead and start it.

    A zero-byte executable is the App Execution Alias stub. Starting it opens
    the Microsoft Store instead of answering, so the one thing discovery must not
    do with it is start it.
    """
    try:
        size = candidate.stat().st_size
    except OSError as error:
        return f"недоступен: {error.strerror or error}"
    if size == 0:
        return "нулевой размер — это заглушка App Execution Alias, а не программа"
    if os.name != "nt" and not os.access(candidate, os.X_OK):
        return "нет права на исполнение"
    return ""


def decode_output(raw: bytes) -> str:
    """What the tool said, in whatever encoding it chose to say it.

    Console tools on Windows do not agree on one: 1cedtcli answers `-help` in
    UTF-16LE, and decoding that as UTF-8 yields NUL-laced garbage in the report —
    garbage that can also contain digits and a dot, which would be reported as a
    version.
    """
    if not raw:
        return ""
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in raw[:64]:
        encoding = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-16-le"
        return raw.decode(encoding, errors="replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode(locale.getpreferredencoding(False), errors="replace")


def start(candidate: Path, tool: Tool) -> tuple[bool, str]:
    """(started, detail). Every failure is a detail, never an exception."""
    try:
        result = subprocess.run(
            [str(candidate), *tool.probe],
            capture_output=True, timeout=tool.timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"не ответил за {tool.timeout} с"
    except OSError as error:
        # This is the shape of defect 61: the file exists, resolves, and the
        # operating system still refuses to run it.
        return False, f"не запускается: {error.strerror or error}"
    output = " ".join(decode_output(result.stdout).split()) or " ".join(decode_output(result.stderr).split())
    if result.returncode != 0:
        return False, f"код возврата {result.returncode}: {output[:120]}" if output else \
            f"код возврата {result.returncode}"
    return True, output[:200]


def discover(tool: Tool | str, environ: dict[str, str] | None = None) -> Result:
    tool = TOOLS.get(tool, Tool(name=tool)) if isinstance(tool, str) else tool
    result = Result(tool=tool.name, status="skipped")
    for candidate in candidates(tool, environ):
        reason = rejected_before_start(candidate)
        if reason:
            result.diagnostics.append(f"{candidate}: {reason}")
            continue
        started, detail = start(candidate, tool)
        if not started:
            result.diagnostics.append(f"{candidate}: {detail}")
            continue
        # A tool that does not print a version may still carry one: EDT names
        # the component directory after its release. Only where declared —
        # elsewhere the path would supply somebody else's version number.
        version = VERSION_RE.search(detail)
        if version is None and tool.version_in_path:
            version = VERSION_RE.search(candidate.parent.name)
        return Result(tool=tool.name, status="ok", path=str(candidate),
                      version=version.group(0) if version else "",
                      detail=detail, diagnostics=result.diagnostics)
    if not result.diagnostics:
        result.diagnostics.append("не найден ни в PATH, ни в известных местах установки")
    return result


def report(names: list[str], environ: dict[str, str] | None = None) -> list[Result]:
    return [discover(name, environ) for name in names]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tools", nargs="*", default=[], help=f"известные: {', '.join(TOOLS)}")
    parser.add_argument("--json", action="store_true", help="машиночитаемый отчёт")
    parser.add_argument("--porcelain", action="store_true",
                        help="строка на инструмент: имя, статус, путь — для shell без парсера JSON")
    parser.add_argument("--require", action="store_true",
                        help="считать `skipped` ошибкой; по умолчанию это не отказ")
    arguments = parser.parse_args()

    names = arguments.tools or ["git", "gh", "codex", "claude"]
    results = report(names)

    if arguments.porcelain:
        # Tab-separated so a shell can read it with `cut`; JSON in POSIX sh means
        # a hand-rolled parser, and a hand-rolled parser is where it breaks.
        for result in results:
            print(f"{result.tool}	{result.status}	{result.path}")
    elif arguments.json:
        print(json.dumps([result.as_dict() for result in results], ensure_ascii=False, indent=2))
    else:
        for result in results:
            if result.status == "ok":
                print(f"[ ok   ] {result.tool} {result.version} — {result.path}")
            else:
                print(f"[ skip ] {result.tool} — недоступен")
                for line in result.diagnostics:
                    print(f"         {line}")

    skipped = [result.tool for result in results if result.status != "ok"]
    if skipped and arguments.require:
        print(f"Недоступны: {', '.join(skipped)}.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
