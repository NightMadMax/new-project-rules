#!/usr/bin/env python3
"""Provider discovery must reuse an existing deployment, prove what answers, and
never start a container.

The reuse rule is the one that fails silently: a second set of containers on the
same ports answers, looks healthy, and serves a different workspace. So the
refusal is checked as a property of the code, not as a habit of whoever calls it.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


provider = module("one_c_provider")
clients = module("one_c_clients")

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


CATALOG = [
    {"role": "syntax", "provider_id": "1c-syntax-checker-mcp", "scope": "provider-shared",
     "endpoint": "from-provider-manifest"},
    {"role": "help", "provider_id": "1C-docs-mcp", "scope": "provider-shared",
     "endpoint": "from-provider-manifest"},
    {"role": "toolkit", "provider_id": "onec-toolkit", "scope": "per-base", "endpoint": "local-port"},
]


class Healthy:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *arguments):
        return False


class Opener:
    def __init__(self, failing: set[str] | None = None):
        self.failing = failing or set()
        self.urls: list[str] = []

    def __call__(self, request, *arguments, **keywords):
        self.urls.append(request.full_url)
        if request.full_url in self.failing:
            raise OSError("connection refused")
        return Healthy()


class Docker:
    """A docker that records what it was asked to do."""

    def __init__(self, names: list[str] | None = None):
        self.names = names or []
        self.calls: list[list[str]] = []

    def __call__(self, arguments: list[str]) -> str:
        self.calls.append(list(arguments))
        return "\n".join(self.names) + "\n"


def manifest(root: Path, servers: list[dict]) -> Path:
    path = root / "provider-manifest.json"
    path.write_bytes(json.dumps({"servers": servers}, ensure_ascii=False).encode("utf-8"))
    return path


# --- nothing may start a container -------------------------------------------

for refused in (["run", "-d", "image"], ["compose", "up"], ["start", "syntax"], ["up"], []):
    try:
        provider.docker(refused, runner=Docker())
        failures.append(f"docker {' '.join(refused)} must be refused: it would create a second deployment")
    except provider.ProviderError:
        pass

recorder = Docker(names=["1c-syntax-checker-mcp-1"])
provider.docker(["ps", "--format", "{{.Names}}"], runner=recorder)
note(recorder.calls == [["ps", "--format", "{{.Names}}"]], f"read-only calls must pass: {recorder.calls}")

# --- an absent manifest is a SKIP, never a guessed endpoint -------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    rows = provider.discover(root, CATALOG, environ={})
    note(all(row.status == "SKIP" for row in rows), f"without a manifest every role is SKIP: {rows}")
    note(all(not row.url for row in rows), "a missing manifest must not produce a URL")
    note(provider.resolved(rows) == {}, "nothing may be registered from a manifest that is not there")

    # The manifest is found where it was declared, and nowhere else.
    path = manifest(root, [
        {"id": "1c-syntax-checker-mcp", "url": "http://127.0.0.1:8801/mcp", "tools": ["check"]},
        {"id": "1C-docs-mcp", "url": "http://127.0.0.1:8802/mcp", "tools": ["docsearch", "docinfo"]},
    ])
    (root / ".dev.env").write_bytes(f"{provider.MANIFEST_KEY}={path}\n".encode("utf-8"))
    note(provider.manifest_path(root, environ={}) == path, "the manifest declared in .dev.env must be found")
    note(provider.manifest_path(root, environ={provider.MANIFEST_ENV: str(path)}) == path,
         "the environment must be able to name the manifest")

    opener = Opener()
    docker = Docker(names=["mcp-1c-syntax-checker-mcp-1", "unrelated"])
    rows = provider.discover(root, CATALOG, opener=opener, runner=docker, environ={})
    verified = {row.role: row for row in rows}
    note(verified["syntax"].status == "OK", f"a described, healthy role must verify: {verified['syntax']}")
    note(verified["help"].status == "OK", f"a described, healthy role must verify: {verified['help']}")
    note(verified["toolkit"].status == "SKIP",
         "the toolkit runs on a local port and must not be asked of the provider")
    note("переиспользуется" in verified["syntax"].detail,
         f"an already running container must be reported as reused: {verified['syntax'].detail}")
    note(all(call[0] in provider.READ_ONLY_DOCKER for call in docker.calls),
         f"discovery may only read from docker: {docker.calls}")
    note(provider.resolved(rows) == {
        "1c-syntax-checker-mcp": "http://127.0.0.1:8801/mcp",
        "1C-docs-mcp": "http://127.0.0.1:8802/mcp",
    }, f"only verified endpoints may be registered: {provider.resolved(rows)}")

    # Health has to be proved, not assumed.
    opener = Opener(failing={"http://127.0.0.1:8801/mcp"})
    rows = provider.check(CATALOG, provider.read_manifest(path), opener=opener)
    unhealthy = {row.role: row for row in rows}["syntax"]
    note(unhealthy.status == "FAIL", f"a role that does not answer must not verify: {unhealthy}")
    note(provider.resolved(rows) == {"1C-docs-mcp": "http://127.0.0.1:8802/mcp"},
         "an endpoint that failed its health check must not be registered")

    # A server that declares no tools is not a server we can register.
    silent = manifest(root, [{"id": "1c-syntax-checker-mcp", "url": "http://127.0.0.1:8801/mcp",
                              "tools": []}])
    rows = provider.check(CATALOG, provider.read_manifest(silent), opener=Opener())
    note({row.role: row for row in rows}["syntax"].status == "FAIL",
         "a server without declared tools must not be registered")

    # An identity the catalog does not know stays out: the port says nothing
    # about who is behind it.
    stranger = manifest(root, [{"id": "somebody-elses-mcp", "url": "http://127.0.0.1:8801/mcp",
                                "tools": ["check"]}])
    rows = provider.check(CATALOG, provider.read_manifest(stranger), opener=Opener())
    note(all(row.status == "SKIP" for row in rows if row.role != "toolkit"),
         f"an unknown identity must not resolve a catalog role: {rows}")

    # A manifest that cannot be trusted is an error, not an empty result.
    for broken in (b"{}", b'{"servers": []}', b'{"servers": [{"id": "x"}]}', b"not json"):
        (root / "broken.json").write_bytes(broken)
        try:
            provider.read_manifest(root / "broken.json")
            failures.append(f"a broken manifest must be refused: {broken!r}")
        except provider.ProviderError:
            pass

# --- what the renderer does with the resolved endpoints ----------------------

registry: list[dict[str, str]] = []
without = clients.projected_servers(CATALOG, registry)
note(all(entry["unresolved"] for entry in without if entry["role"] != "toolkit"),
     "without a provider the endpoints stay unresolved")
with_provider = clients.projected_servers(CATALOG, registry, {
    "1c-syntax-checker-mcp": "http://127.0.0.1:8801/mcp"})
syntax = [entry for entry in with_provider if entry["role"] == "syntax"][0]
note(syntax["url"] == "http://127.0.0.1:8801/mcp" and not syntax["unresolved"],
     f"a verified endpoint must reach the projection: {syntax}")
still = [entry for entry in with_provider if entry["role"] == "help"][0]
note(still["unresolved"], "a role the provider did not describe must stay unresolved")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} provider check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("Provider discovery checks passed.")
