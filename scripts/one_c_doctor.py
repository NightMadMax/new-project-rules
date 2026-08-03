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

import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import cli_discovery  # noqa: E402
import one_c_release_guard as release_guard  # noqa: E402

# Exactly what may be opened. Anything else is refused, so widening the diagnosis
# is a review of this list rather than an accident — and state, backups, sessions
# and logs are outside it by construction rather than by a second list that could
# fall out of step. A broad walk of those once carried a historical credential
# out of a session file.
#
# Two reads sit outside these paths and are named here because an undeclared
# exception is how a list like this stops meaning anything: the external
# provider manifest, opened by the path the project declared in `.dev.env` and
# never printed, and the output of `docker ps`. Neither reaches the network —
# the provider is asked with `network=False` — and the same rule as everywhere
# holds: the report carries the key name, not its value.
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
# What an `ordinary` launch profile must carry (decision 1.16).
CLIENT_TYPE_ATTRIBUTE = "ATTR_CLIENT_TYPE"
# What makes a profile start the Toolkit instead of only the client.
STARTUP_OPTION_ATTRIBUTE = "ATTR_STARTUP_OPTION"
# Matched against the key name, not the whole line. Deciding by line content
# meant a key named DB_PWD or BASE_LOGIN carried no marker and was printed
# whole, while an ordinary setting whose value happened to contain "key" was
# masked for no reason.
SECRET_NAME_MARKERS = (
    "password", "passwd", "pwd", "pass", "secret", "token", "key", "credential",
    "login", "user", "auth",
)
# Matched against the value: a connection string carries the server and the
# base regardless of what the key is called.
SECRET_VALUE_MARKERS = ("srvr=", "ref=")
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
        # `utf-8-sig`, like every other reader of these files: the registry is
        # edited in a spreadsheet, which writes a BOM. Decoding without it left
        # the mark on the first header cell, so `project_id` was a key nobody
        # looked up and every base in the report lost its name while the
        # registry itself was pronounced fine.
        return path.read_bytes().decode("utf-8-sig", errors="replace")
    except OSError:
        return ""


def mask(line: str) -> str:
    """A key and whether it is set — never the value.

    Masking happens on the way in. Cleaning a finished report means the value
    existed in memory next to the code that prints it, and one forgotten branch
    is enough.
    """
    name, separator, value = line.partition("=")
    if not separator:
        name, separator, value = line.partition(":")
    if not separator:
        # No key, no value: nothing to mask and nothing to disclose.
        return line
    # Every value, not just the ones a marker list recognised. The report says
    # values are not read, and the previous rule made that true only of keys
    # named like credentials: an EDT workspace and the provider manifest went
    # out as full machine paths — the same paths the rest of the diagnosis takes
    # care to hide. A marker list can only ever be behind the names a project
    # invents.
    if not value.strip():
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


def registry_rows(root: Path) -> list[dict[str, str]]:
    """The base registry as rows. An unreadable registry is no rows, not a guess."""
    text = read(root, "config/1c-projects.tsv")
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return []
    header = lines[0].split("\t")
    rows = []
    for number, line in enumerate(lines[1:], start=2):
        values = line.split("\t")
        if len(values) == len(header):
            rows.append(dict(zip(header, values)))
        else:
            # A dropped row used to disappear from the diagnosis in silence,
            # which reads as "this base is fine" rather than "this base was not
            # looked at". The row is still not guessed at — it is named.
            rows.append({"project_id": f"<строка {number}>", "environment_id": "?",
                         "status": "unreadable",
                         "notes": f"в строке {len(values)} колонок вместо {len(header)}"})
    return rows


def setting(root: Path, key: str) -> str:
    """Whether a local setting is recorded. The value itself never leaves here."""
    for line in read(root, ".dev.env").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == key and not name.lstrip().startswith("#"):
            return value.strip()
    return ""


STANDARD_ROOT = SCRIPTS.parent


def catalog_key(component: str, fallback: str) -> str:
    """Which `.dev.env` key holds this component's state, per the catalog.

    The same fact was declared twice — in the catalog and here — so renaming a
    key in the catalog left the diagnosis reading the old one and reporting
    `SKIP` for a reason nobody could see. The catalog is the source; the
    fallback only keeps the diagnosis working when it cannot be read at all.
    """
    try:
        import one_c_components

        for item in one_c_components.load(STANDARD_ROOT):
            if item.name == component and item.scheme == "env":
                return item.target
    except Exception:  # noqa: BLE001 - a diagnosis never fails on its own catalog
        pass
    return fallback


def edt_rows(root: Path, discover=None) -> list[Row]:
    """Versions of EDT and EDT-MCP, and the state of the conditional patches.

    EDT answers about itself: its CLI carries the release it was installed from.
    EDT-MCP and the two patches do not — they are plugins inside an installation
    the diagnosis may not walk, so the only honest source is what the project
    recorded about them. Nothing recorded is a `SKIP` that names the key to
    fill, never a guess about a version nobody measured.
    """
    discover = cli_discovery.discover if discover is None else discover
    found = discover("1cedtcli")
    rows = [Row("1C:EDT", "OK", f"версия {found.version or 'не определена'} — {found.path}",
                "ничего не требуется")
            if found.status == "ok" else
            Row("1C:EDT", "SKIP", "; ".join(found.diagnostics)[:200],
                "без EDT недоступны разработка и конвертация формата исходников")]
    for component, catalog_name, fallback, consequence in (
        ("EDT-MCP", "EDT-MCP", "EDT_MCP_VERSION", "AI-клиент не управляет EDT"),
        ("патч Run without update", "Патч Run without update", "EDT_RUN_WITHOUT_UPDATE",
         "запуск без обновления конфигурации недоступен"),
    ):
        key = catalog_key(catalog_name, fallback)
        value = setting(root, key)
        rows.append(Row(component, "OK" if value else "SKIP",
                        f"версия {value}" if value else f"{key} не записан в .dev.env",
                        "ничего не требуется" if value else consequence))
    return rows


def started_processor(body: str) -> Optional[str]:
    """The project-relative processor a launch profile starts, if it names one.

    The profile is XML, the value is escaped, and the path inside it is quoted:
    `/Execute &quot;<path>&quot;`. Only a path that stays inside the project can
    be checked here, and one that does not is exactly what should not be
    reported as ready — an absolute path belongs to one machine (№241), and a
    placeholder belongs to nobody until somebody edits it (№252).
    """
    match = re.search(rf'{STARTUP_OPTION_ATTRIBUTE}"\s+value="([^"]*)"', body)
    if not match:
        return None
    value = html.unescape(match.group(1))
    quoted = re.search(r'/Execute\s+"([^"]+)"', value) or re.search(r"/Execute\s+(\S+)", value)
    if not quoted:
        return None
    path = quoted.group(1).strip().replace("\\", "/")
    if not path or path.startswith("/") or ".." in path.split("/") or re.match(r"^[A-Za-z]:", path):
        return None
    return path


def ordinary_rows(root: Path, rows: list[dict[str, str]]) -> list[Row]:
    """The plugin and the launch profiles — a requirement of `ordinary` only.

    A managed base has no Toolkit build of ours: its write barrier is the switch
    in the Toolkit UI, confirmed by a call rather than by a file. Reporting a
    missing profile there would teach people that a correct environment has open
    items.
    """
    ordinary = [row for row in rows if row.get("application_kind") == "ordinary"]
    if not ordinary:
        return [Row("плагин обычного приложения", "OK",
                    "в реестре нет баз application_kind=ordinary",
                    "не требуется: для managed плагин и server-vs-client guard не применяются")]
    key = catalog_key("Плагин обычного приложения", "EDT_ORDINARY_PLUGIN")
    plugin = setting(root, key)
    result = [Row("плагин обычного приложения", "OK" if plugin else "SKIP",
                  f"версия {plugin}" if plugin else f"{key} не записан в .dev.env",
                  "ничего не требуется" if plugin else
                  f"обычные приложения не запускаются из EDT; баз ordinary: {len(ordinary)}")]
    for row in ordinary:
        profile = row.get("edt_profile", "").strip()
        relative = f"configurations/launch/{profile}.launch"
        identity = f"{row.get('project_id', '?')}/{row.get('environment_id', '?')}"
        if not profile:
            result.append(Row(f"профиль запуска {identity}", "SKIP", "edt_profile не заполнен в реестре",
                              "запуск обычного приложения настраивается вручную"))
        elif allowed(relative) and (root / relative).is_file():
            # Decision 1.16: the attribute is checked for `ordinary` and only
            # there. A profile without it starts the base as the wrong client,
            # and the file being present says nothing about that.
            body = read(root, relative)
            if CLIENT_TYPE_ATTRIBUTE in body:
                # A Toolkit profile also has to start the build; the HTTP-debug
                # profile deliberately has no `/Execute` and is not judged by it.
                started = STARTUP_OPTION_ATTRIBUTE in body and "/Execute" in body
                target = started_processor(body)
                if not started:
                    result.append(Row(f"профиль запуска {identity}", "OK",
                                      f"{relative}, {CLIENT_TYPE_ATTRIBUTE} задан, "
                                      "без автозапуска обработки",
                                      "клиент стартует, Toolkit открывается вручную"))
                elif target is None or not (root / target).is_file():
                    # Naming a processor is not starting one. The path used to
                    # be taken on trust, so a profile pointing at a placeholder
                    # no one substitutes was reported as needing nothing (№253).
                    named = target or "путь не разобран"
                    result.append(Row(f"профиль запуска {identity}", "SKIP",
                                      f"{relative} запускает '{named}', которого нет в проекте",
                                      "профиль не стартует обработку; поправить путь в "
                                      f"{STARTUP_OPTION_ATTRIBUTE}"))
                else:
                    result.append(Row(f"профиль запуска {identity}", "OK",
                                      f"{relative}, {CLIENT_TYPE_ATTRIBUTE} задан, "
                                      f"автозапуск: {target}",
                                      "ничего не требуется"))
            else:
                result.append(Row(f"профиль запуска {identity}", "SKIP",
                                  f"{relative} без {CLIENT_TYPE_ATTRIBUTE}",
                                  "обычное приложение запустится не тем клиентом"))
        else:
            result.append(Row(f"профиль запуска {identity}", "SKIP", f"{relative} отсутствует",
                              "профиль запуска для ordinary не поставлен"))
    return result


def port_rows(rows: list[dict[str, str]], probe=None) -> list[Row]:
    """Whether the port a base was assigned is free on this machine.

    The runtime smoke of milestone W found `6003` — the port the allocation rule
    hands to the first base — already listened on by the platform itself. The
    rule does not change and the diagnosis never reassigns anything: a shared
    topology is not rewritten because one machine is busy. It says which port is
    taken, and the choice is the user's.
    """
    probe = occupied if probe is None else probe
    result: list[Row] = []
    for row in rows:
        if row.get("mcp_enabled") != "true":
            continue
        port = row.get("server_port", "").strip()
        identity = f"{row.get('project_id', '?')}/{row.get('environment_id', '?')}"
        if not port.isdigit():
            continue
        if probe(int(port)):
            result.append(Row(f"порт {port} ({identity})", "FAIL", "порт уже занят на этой машине",
                              "освободить порт или изменить topology явно — "
                              "диагностика не переназначает порты"))
        else:
            result.append(Row(f"порт {port} ({identity})", "OK", "свободен", "ничего не требуется"))
    return result


def occupied(port: int) -> bool:
    """Local occupancy only: bind, do not connect.

    Connecting would answer about whoever is listening, including a service on
    another machine; binding answers the only question that matters — whether
    this base can start its server here.
    """
    import socket
    import sys

    # Every interface, then loopback. A server that matters here binds
    # 0.0.0.0 — the 1C platform on 6003 does — and probing only 127.0.0.1
    # reported such a port free, which is exactly the case the check exists for.
    # The reverse also happens: a loopback-only listener leaves 0.0.0.0
    # bindable on some stacks, so both are asked and either one answers "taken".
    for address in ("", "127.0.0.1"):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if sys.platform == "win32":
                # SO_REUSEADDR on Windows lets a bind succeed over a socket that
                # is actively bound — the probe would report free while the
                # platform listens. SO_EXCLUSIVEADDRUSE is the option that
                # refuses instead.
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind((address, port))
            except OSError:
                return True
    return False


def provider_rows(root: Path, discover=None) -> list[Row]:
    """The external MCP provider: found and verified, or honestly absent."""
    import one_c_provider

    try:
        catalog = json.loads(read(root, "config/1c-mcp-catalog.json") or "{}")
    except ValueError:
        return [Row("MCP provider", "FAIL", "config/1c-mcp-catalog.json не читается как JSON",
                    "исправить каталог ролей")]
    servers = catalog.get("servers", []) if isinstance(catalog, dict) else []
    if not servers:
        return [Row("MCP provider", "SKIP", "каталог ролей пуст",
                    "капабилити не поставила каталог MCP")]
    try:
        # No network and no machine path in the output: the diagnosis reports
        # what is on this machine, and a manifest that cannot be read is a row
        # of that report — a traceback here would break the tool exactly in the
        # situation it exists to diagnose.
        rows = (one_c_provider.discover(root, servers, network=False) if discover is None
                else discover(root, servers))
    except one_c_provider.ProviderError as error:
        return [Row("MCP provider", "FAIL", str(error)[:200],
                    "исправить manifest провайдера или убрать ссылку на него")]
    unresolved = [row for row in rows if row.status != "OK"]
    if not unresolved:
        return [Row("MCP provider", "OK", f"ролей подтверждено: {len(rows)}",
                    "переиспользуется существующий deployment, вторые контейнеры не разворачиваются")]
    return [Row("MCP provider", "SKIP",
                f"подтверждено {len(rows) - len(unresolved)} из {len(rows)}: "
                + "; ".join(f"{row.role} — {row.detail}" for row in unresolved[:3]),
                "часть MCP-зависимой разработки недоступна")]


def release_rows(root: Path) -> list[Row]:
    """Whether this checkout is the release the project installed.

    A diagnosis never fails a run, so unlike the session lock and the client
    renderer this does not refuse — it reports. But it has to report: the
    scripts that decide what may be written to a live infobase are run out of
    this checkout, and being a different release than the project installed is
    the kind of thing a diagnosis exists to notice.
    """
    try:
        agreed = release_guard.require_matching_release(root, SCRIPTS.parent)
    except release_guard.ReleaseMismatch as error:
        return [Row("release capability 1c", "FAIL", str(error),
                    "привести чекаут стандарта и проект к одному release")]
    if agreed is None:
        return [Row("release capability 1c", "SKIP", "capability не установлена в проекте",
                    "ничего не требуется")]
    return [Row("release capability 1c", "OK", f"чекаут и проект на {agreed[:12]}",
                "ничего не требуется")]


def report(root: Path, names: tuple[str, ...] = ("docker", "codex", "claude"),
           discover=None, provider=None) -> list[Row]:
    rows = list(tools(names))
    rows.extend(release_rows(root))
    registry = registry_rows(root)
    if registry:
        rows.append(Row("реестр баз", "OK", f"строк: {len(registry)}", "ничего не требуется"))
    else:
        rows.append(Row("реестр баз", "SKIP", "реестр пуст или отсутствует",
                        "добавить базу через add-1c-base"))
    rows.extend(edt_rows(root, discover))
    rows.extend(ordinary_rows(root, registry))
    rows.extend(port_rows(registry))
    rows.extend(provider_rows(root, provider))
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
