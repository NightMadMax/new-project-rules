#!/usr/bin/env python3
"""Read-only diagnostics of the 1C environment.

Two rules carry the weight here, and both exist because of what went wrong
before: the report reads only what it declared it would read, and it masks
values before they can reach the output rather than cleaning the output
afterwards. A broad walk of a user profile once carried a historical credential
out of a session file — that is a reproduced incident, not a hypothesis.

A missing tool is `SKIP`, never `FAIL`. Not every task needs every component,
and a diagnosis that cries failure about an absent optional tool teaches people
to ignore it. Every row says what it means and what to do next: a status with no
consequence is a number nobody acts on.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import cli_discovery  # noqa: E402

# Exactly what may be opened. Anything else is refused, so widening the diagnosis
# is a review of this list rather than an accident — and state, backups, sessions
# and logs are outside it by construction rather than by a second list that could
# fall out of step. A broad walk of those once carried a historical credential
# out of a session file.
ALLOWLIST = (
    ".dev.env",
    ".v8-project.json",
    "config/1c-projects.tsv",
    "config/1c-mcp-catalog.json",
    ".claude/settings.json",
    ".mcp.json",
    ".codex/config.toml",
)
ALLOWED_GLOBS = ("configurations/launch/*.launch",)
SECRET_MARKERS = ("password", "passwd", "token", "secret", "key", "srvr=", "ref=")
MASK = "задан"


@dataclass(frozen=True)
class Row:
    component: str
    status: str  # OK | SKIP | FAIL
    detail: str
    action: str


def allowed(relative: str) -> bool:
    """Whether the diagnosis may open this path at all."""
    if relative.startswith("/") or "\\" in relative or ".." in relative.split("/"):
        return False
    if relative in ALLOWLIST:
        return True
    return any(Path(relative).match(pattern) for pattern in ALLOWED_GLOBS)


def read(root: Path, relative: str) -> str:
    if not allowed(relative):
        raise PermissionError(f"{relative} is outside the diagnostics allowlist")
    path = root / relative
    if not path.is_file():
        return ""
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""


def mask(line: str) -> str:
    """A key and whether it is set — never the value.

    Masking happens on the way in. Cleaning a finished report means the value
    existed in memory next to the code that prints it, and one forgotten branch
    is enough.
    """
    lowered = line.lower()
    if not any(marker in lowered for marker in SECRET_MARKERS):
        return line
    name, separator, value = line.partition("=")
    if not separator:
        name, separator, value = line.partition(":")
    if not separator or not value.strip():
        return f"{name.strip()}: не задан"
    return f"{name.strip()}: {MASK}"


def settings(root: Path, relative: str = ".dev.env") -> list[str]:
    """The environment file as key/state pairs, values never included."""
    return [mask(line) for line in read(root, relative).splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def tools(names: tuple[str, ...] = ("1cedtcli", "docker", "codex", "claude")) -> list[Row]:
    rows: list[Row] = []
    for name in names:
        found = cli_discovery.discover(name)
        if found.status == "ok":
            rows.append(Row(name, "OK", f"{found.version or 'версия не сообщается'} — {found.path}",
                            "ничего не требуется"))
        else:
            rows.append(Row(
                name, "SKIP", "; ".join(found.diagnostics)[:200],
                cli_discovery.TOOLS[name].note if name in cli_discovery.TOOLS else
                "инструмент не найден; часть задач будет недоступна",
            ))
    return rows


def report(root: Path, names: tuple[str, ...] = ("1cedtcli", "docker", "codex", "claude")) -> list[Row]:
    rows = list(tools(names))
    registry = read(root, "config/1c-projects.tsv")
    if registry.strip():
        bases = max(0, len(registry.strip().splitlines()) - 1)
        rows.append(Row("реестр баз", "OK", f"строк: {bases}", "ничего не требуется"))
    else:
        rows.append(Row("реестр баз", "SKIP", "реестр пуст или отсутствует",
                        "добавить базу через add-1c-base"))
    environment = settings(root)
    rows.append(Row(".dev.env", "OK" if environment else "SKIP",
                    f"ключей: {len(environment)}" if environment else "файл отсутствует",
                    "значения не читаются — только имя ключа и признак «задан»"))
    return rows


def render(rows: list[Row]) -> str:
    width = max((len(row.component) for row in rows), default=0)
    return "\n".join(f"[{row.status:4}] {row.component.ljust(width)}  {row.detail} — {row.action}"
                     for row in rows)


def main(argv: list[str] | None = None) -> int:
    import argparse

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="project root")
    arguments = parser.parse_args(argv)
    rows = report(Path(arguments.root).resolve())
    print(render(rows))
    # A diagnosis never fails a run: it reports. A missing optional tool is not
    # a broken project, and an exit code that says otherwise gets ignored.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
