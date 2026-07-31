#!/usr/bin/env python3
"""Discovery of the external MCP provider: find it, verify it, never start it.

The provider is somebody else's deployment. Its containers, ports, mounts and
lifecycle belong to the provider project (decision S.4.5), and our whole contract
is: find the existing deployment, prove that what answers is what the catalog
expects, and hand the resolved endpoints to the client renderer.

Two refusals carry the design.

Nothing here starts a container. Only `ps` and `inspect` may be issued, and the
check is a refusal in code rather than a rule in a document — a second set of
containers on the same ports is the failure the reuse requirement exists to
prevent, and it is invisible until something answers on the wrong port.

Nothing here guesses an endpoint. A role that the manifest does not describe is
`SKIP`, exactly as it is in the renderer: a plausible URL looks installed and
fails at the first call. Identity, health and tools are verified before an
endpoint is offered for registration, because the port says nothing about who
sits behind it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

MANIFEST_ENV = "ONEC_MCP_PROVIDER_MANIFEST"
MANIFEST_KEY = "MCP_PROVIDER_MANIFEST"
DEV_ENV = ".dev.env"
# Read-only by construction. `run`, `compose`, `start` and `up` are exactly the
# verbs that would create the second deployment this module exists to avoid.
READ_ONLY_DOCKER = ("ps", "inspect", "version")
TIMEOUT_SECONDS = 10


class ProviderError(Exception):
    """The provider cannot be used as described, and this says why."""


@dataclass(frozen=True)
class Row:
    role: str
    provider_id: str
    status: str  # OK | SKIP | FAIL
    detail: str
    url: str = ""


def read_dev_env(root: Path) -> dict[str, str]:
    path = root / DEV_ENV
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_bytes().decode("utf-8", errors="replace").splitlines():
        name, separator, value = line.partition("=")
        if separator and not name.lstrip().startswith("#"):
            values[name.strip()] = value.strip()
    return values


def manifest_path(root: Path, explicit: str = "", environ: dict[str, str] | None = None) -> Path | None:
    """Where the provider describes itself, or nothing.

    An explicit path wins, then the environment, then the local settings file.
    There is no well-known default: a guessed path would either miss or, worse,
    pick up a stale manifest from an unrelated install.
    """
    environ = os.environ if environ is None else environ
    for candidate in (explicit, environ.get(MANIFEST_ENV, ""), read_dev_env(root).get(MANIFEST_KEY, "")):
        if candidate:
            path = Path(candidate)
            return path if path.is_absolute() else (root / path)
    return None


def read_manifest(path: Path) -> dict[str, dict]:
    """The provider's servers by id: `{id: {url, tools, health}}`.

    This is our consumer contract, not the provider's internal state: everything
    beyond identity, endpoint and tool names is ignored on purpose.
    """
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise ProviderError(f"provider manifest is unreadable: {error}") from error
    servers = data.get("servers") if isinstance(data, dict) else None
    if not isinstance(servers, list) or not servers:
        raise ProviderError("provider manifest declares no servers")
    described: dict[str, dict] = {}
    for entry in servers:
        if not isinstance(entry, dict):
            raise ProviderError("provider manifest holds a server that is not an object")
        identity = entry.get("id") or entry.get("provider_id")
        url = entry.get("url", "")
        if not identity or not url:
            raise ProviderError("provider manifest holds a server without an id or a url")
        tools = entry.get("tools", [])
        if not isinstance(tools, list):
            raise ProviderError(f"provider manifest: tools of '{identity}' must be a list")
        described[identity] = {"url": url, "tools": [name for name in tools if isinstance(name, str)],
                               "health": entry.get("health", url)}
    return described


def docker(arguments: list[str], runner=None) -> str:
    """A read-only docker call, or a refusal.

    The allowlist is here rather than in review because "do not start a second
    deployment" is a property the code must have, not advice it may follow.
    """
    if not arguments or arguments[0] not in READ_ONLY_DOCKER:
        raise ProviderError(
            f"docker {' '.join(arguments) or '<none>'} is refused: discovery may only "
            f"read ({', '.join(READ_ONLY_DOCKER)}); the provider owns container lifecycle"
        )
    if runner is not None:
        return runner(arguments)
    try:
        completed = subprocess.run(["docker", *arguments], capture_output=True,
                                   timeout=TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ProviderError(f"docker is unavailable: {error}") from error
    if completed.returncode != 0:
        raise ProviderError(f"docker {arguments[0]} exited {completed.returncode}")
    return (completed.stdout or b"").decode("utf-8", errors="replace")


def deployment(runner=None) -> list[str]:
    """Names of the containers already running, so nothing is started twice."""
    try:
        output = docker(["ps", "--format", "{{.Names}}"], runner=runner)
    except ProviderError:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def probe(url: str, opener=urlopen) -> tuple[bool, str]:
    """(healthy, detail). Every failure is a detail, never an exception."""
    try:
        with opener(Request(url, method="GET", headers={"User-Agent": "new-project-rules"}),
                    timeout=TIMEOUT_SECONDS) as response:
            code = getattr(response, "status", 0) or 0
            return code < 400, str(code)
    except HTTPError as error:
        return False, f"{error.code} {error.reason}"[:80]
    except URLError as error:
        return False, str(error.reason)[:80]
    except Exception as error:  # noqa: BLE001 - a report must survive anything
        return False, f"{type(error).__name__}: {error}"[:80]


def check(catalog: list[dict], described: dict[str, dict], *, opener=urlopen,
          running: list[str] | None = None) -> list[Row]:
    """One row per catalog role: what was found, and what was proved about it."""
    rows: list[Row] = []
    for server in catalog:
        role, identity = server.get("role", ""), server.get("provider_id", "")
        if server.get("endpoint") != "from-provider-manifest":
            # Toolkit runs on a local port of its own; the provider does not
            # describe it and must not be asked about it.
            rows.append(Row(role, identity, "SKIP", "endpoint не из provider manifest"))
            continue
        entry = described.get(identity)
        if entry is None:
            rows.append(Row(role, identity, "SKIP",
                            f"provider manifest не описывает '{identity}'"))
            continue
        if not entry["tools"]:
            # A server that declares no tools cannot be narrowed to tools, and a
            # registration would hand the client an endpoint with nothing behind
            # it. The catalog's fallback class stays in force either way.
            rows.append(Row(role, identity, "FAIL", "сервер не объявил ни одного инструмента",
                            entry["url"]))
            continue
        healthy, detail = probe(entry["health"], opener=opener)
        if not healthy:
            rows.append(Row(role, identity, "FAIL", f"health-check не прошёл: {detail}", entry["url"]))
            continue
        reused = ""
        if running:
            matched = [name for name in running if identity in name]
            reused = f"; переиспользуется контейнер {matched[0]}" if matched else ""
        rows.append(Row(role, identity, "OK",
                        f"инструментов: {len(entry['tools'])}; health {detail}{reused}", entry["url"]))
    return rows


def resolved(rows: list[Row]) -> dict[str, str]:
    """Endpoints safe to register: identity matched, health proved, tools present."""
    return {row.provider_id: row.url for row in rows if row.status == "OK" and row.url}


def discover(root: Path, catalog: list[dict], *, explicit: str = "", opener=urlopen,
             runner=None, environ: dict[str, str] | None = None) -> list[Row]:
    path = manifest_path(root, explicit, environ)
    if path is None or not path.is_file():
        where = str(path) if path is not None else f"{MANIFEST_ENV} или {MANIFEST_KEY} в {DEV_ENV}"
        return [Row(server.get("role", ""), server.get("provider_id", ""), "SKIP",
                    f"provider manifest не найден: {where}")
                for server in catalog]
    return check(catalog, read_manifest(path), opener=opener, running=deployment(runner))


def render(rows: list[Row]) -> str:
    width = max((len(row.role) for row in rows), default=0)
    return "\n".join(f"[{row.status:4}] {row.role.ljust(width)}  {row.detail}" for row in rows)


def main(argv: list[str] | None = None) -> int:
    import argparse

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    from one_c_clients import ClientError, read_catalog

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--manifest", default="", help="path to the provider manifest")
    arguments = parser.parse_args(argv)
    root = Path(arguments.root).resolve()
    catalog = root / "config/1c-mcp-catalog.json"
    if not catalog.is_file():
        # "declares no servers" about a file that is not there sends the reader
        # to edit a catalog they do not have.
        print(f"[ERROR] {catalog} отсутствует: это не проект с capability 1c", file=sys.stderr)
        return 2
    try:
        rows = discover(root, read_catalog(root), explicit=arguments.manifest)
    except (ClientError, ProviderError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 2
    print(render(rows))
    # A provider that is not deployed yet is not a broken project.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
