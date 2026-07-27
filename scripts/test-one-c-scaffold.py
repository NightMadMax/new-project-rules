#!/usr/bin/env python3
"""The 1C project scaffold: what a created project gets and what it must reject.

The scaffold is checked through a real bootstrap rather than by listing files in
the manifest: what matters is the project a person ends up with.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location("validate_project", SCRIPTS / "validate-project.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules["validate_project"] = validator
spec.loader.exec_module(validator)

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com",
}
MANAGED = (
    "configurations/AGENTS.md",
    "configurations/CLAUDE.md",
    "config/1c-mcp-catalog.json",
    ".dev.env.example",
    "configurations/launch/toolkit.launch",
    "configurations/launch/ordinary-http-debug.launch",
    "docs/operations/EDT_SETUP.md",
)
SKILLS = (
    "doctor-1c", "setup-1c-environment", "select-1c-project", "query-1c-infobase",
    "measure-1c-performance", "work-with-1c-edt", "add-1c-base", "activate-1c-client",
    "export-1c-source", "deploy-1c-source", "deploy-and-test-1c",
)
SEED = (
    "docs/operations/TOOLCHAIN.md",
    "docs/quality/TEST_MODEL.md",
    "docs/integrations/ONE_C_INTEGRATIONS.md",
    "ONE_C_WORKSPACE.md",
    "docs/operations/ENVIRONMENT_REGISTRY.md",
    "config/1c-projects.tsv",
    "USER-RULES.md",
    "memory.md",
    "LLM-RULES.md",
)
failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def bootstrap(destination: Path) -> subprocess.CompletedProcess | None:
    if not shutil.which("sh"):
        return None
    return subprocess.run(
        ["sh", (SCRIPTS / "bootstrap-new-project.sh").as_posix(),
         destination.as_posix(), "demo", "minimal", "--preset", "1c"],
        capture_output=True, text=True, env={**os.environ, **GIT_IDENTITY},
    )


def registry_rows(*rows: str) -> str:
    header = "\t".join(validator.ONE_C_REGISTRY_FIELDS)
    return "\n".join([header, *rows]) + "\n"


def base_row(**overrides: str) -> str:
    values = {
        "project_id": "erp", "environment_id": "dev", "folder": "configurations/erp",
        "configuration": "ERP 2", "platform_version": "8.3.27.2025", "compatibility_mode": "8.3.27",
        "application_kind": "managed", "support_mode": "on-support", "source_format": "edt",
        "edt_workspace": "erp-workspace", "edt_profile": "-", "server_port": "6003",
        "is_production": "false", "mcp_enabled": "true", "owner": "team",
    }
    values.update(overrides)
    return "\t".join(values[field] for field in validator.ONE_C_REGISTRY_FIELDS)


# --- what a created project gets -------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    project = Path(raw) / "project"
    result = bootstrap(project)
    if result is None:
        print("SKIP: sh is not available on this machine")
    elif result.returncode != 0:
        failures.append(f"bootstrap failed: {result.stderr.strip()[:300]}")
    else:
        for relative in MANAGED + SEED:
            note((project / relative).is_file(), f"scaffold is missing {relative}")

        # Placeholders belong to seeds, which bootstrap renders; a managed file
        # must not carry them, or it could never be updated.
        for relative in MANAGED:
            body = (project / relative).read_text(encoding="utf-8")
            note("<PROJECT_NAME>" not in body, f"{relative} still carries a placeholder")
        for relative in ("ONE_C_WORKSPACE.md", "USER-RULES.md", "memory.md"):
            body = (project / relative).read_text(encoding="utf-8")
            note("<PROJECT_NAME>" not in body, f"{relative} was not rendered")
            note("demo" in body, f"{relative} does not name the project")

        # A skill that is not delivered is a rule nobody can follow.
        for skill in SKILLS:
            for tail in ("SKILL.md", "agents/openai.yaml"):
                note((project / f".agents/skills/{skill}/{tail}").is_file(),
                     f"scaffold is missing the {skill} {tail}")

        scoped = (project / "configurations/AGENTS.md").read_text(encoding="utf-8")
        # The rules that must reach a working session, in the words the file uses.
        for expected in ("EDT", "расширением", "не команды", "фактической базы", "резервной копии"):
            note(expected.lower() in scoped.lower(), f"scoped rules do not state '{expected}'")
        note((project / "configurations/CLAUDE.md").read_text(encoding="utf-8").strip() == "@AGENTS.md",
             "the Claude entry point must only import AGENTS.md")

        registry = (project / "config/1c-projects.tsv").read_text(encoding="utf-8")
        note(registry.splitlines()[0].split("\t") == list(validator.ONE_C_REGISTRY_FIELDS),
             "the registry header does not match the contract")
        note(len(registry.splitlines()) == 1, "a fresh registry must have no rows")

        report = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate-project.py"), "--root", str(project), "--report-only"],
            capture_output=True, text=True,
        )
        note("0 error(s)" in report.stdout, f"a fresh 1C project must validate: {report.stdout[-300:]}")

        # The registry must be checked by the validator itself, not only by a
        # function a test can call directly.
        (project / "config/1c-projects.tsv").write_bytes(
            registry_rows(base_row(server_port="9000")).encode("utf-8"))
        report = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate-project.py"), "--root", str(project), "--report-only"],
            capture_output=True, text=True,
        )
        note("registry.port" in report.stdout, f"the validator must check the registry: {report.stdout[-300:]}")

        # What git must not track and must not normalise. The template promises
        # .dev.env is ignored, and a normalised EPF is a corrupted EPF.
        ignored = (project / ".gitignore").read_text(encoding="utf-8")
        for line in (".dev.env", ".v8-project.json"):
            note(line in ignored.splitlines(), f".gitignore must hold {line}")
        attributes = (project / ".gitattributes").read_text(encoding="utf-8").splitlines()
        for line in ("*.epf binary", "*.cf binary", "*.bsl text eol=lf"):
            note(line in attributes, f".gitattributes must hold '{line}'")

        # The companion files are only rules if something loads them.
        root_rules = (project / "AGENTS.md").read_text(encoding="utf-8")
        for companion in ("USER-RULES.md", "LLM-RULES.md", "memory.md"):
            note(f"@{companion}" in root_rules, f"the root rules must load {companion}")

        # Every section of the docs index must appear once: a repeated heading
        # splits the index and a reader trusts whichever half they saw first.
        headings = [line for line in (project / "docs/README.md").read_text(encoding="utf-8").splitlines()
                    if line.startswith("## ")]
        note(len(headings) == len(set(headings)), f"the docs index repeats a section: {headings}")

        # The instruction chain has a hard budget: past 32 KiB an agent stops
        # loading files and the rules that did not fit simply do not apply.
        chain = sum((project / relative).stat().st_size for relative in
                    ("AGENTS.md", "configurations/AGENTS.md", "USER-RULES.md", "LLM-RULES.md", "memory.md"))
        note(chain < 32 * 1024, f"the instruction chain is {chain} bytes, over the 32 KiB budget")


# --- what the registry must reject -----------------------------------------

def registry_case(name: str, content: str, expect: str | None) -> None:
    with tempfile.TemporaryDirectory() as raw:
        project = Path(raw)
        (project / "config").mkdir()
        (project / "config/1c-projects.tsv").write_bytes(content.encode("utf-8"))
        codes = {finding.code for finding in validator.check_one_c_registry(project)}
        if expect is None:
            note(not codes, f"{name}: expected no findings, got {codes}")
        else:
            note(expect in codes, f"{name}: expected '{expect}', got {codes}")


registry_case("healthy registry", registry_rows(base_row()), None)
registry_case("empty registry", registry_rows(), None)
registry_case("wrong header", "project_id\tenvironment_id\n", "registry.header")
registry_case(
    "duplicate identity",
    registry_rows(base_row(), base_row(server_port="6004")),
    "registry.duplicate",
)
registry_case("unknown application kind", registry_rows(base_row(application_kind="both")), "registry.value")
registry_case("unknown support mode", registry_rows(base_row(support_mode="maybe")), "registry.value")
registry_case("unknown source format", registry_rows(base_row(source_format="xml")), "registry.value")
registry_case("production flag is not a boolean", registry_rows(base_row(is_production="yes")), "registry.value")
registry_case("port outside the range", registry_rows(base_row(server_port="9000")), "registry.port")
registry_case("exposed base without a port", registry_rows(base_row(server_port="")), "registry.port")
registry_case(
    "port on a base that does not expose MCP",
    registry_rows(base_row(mcp_enabled="false")),
    "registry.port",
)
registry_case(
    "two bases on one port",
    registry_rows(base_row(), base_row(project_id="zup")),
    "registry.port",
)
# A path check that depends on the host would let each platform through the
# other's mistake: the repository is prepared on macOS and used on Windows.
for case, value in (
    ("posix machine path", "/Users/someone/workspace"),
    ("windows machine path", "C:\\Users\\someone\\workspace"),
    ("windows share", "\\\\server\\share\\workspace"),
    ("home path", "~/workspace"),
    ("path out of the project", "../../elsewhere"),
):
    registry_case(case, registry_rows(base_row(edt_workspace=value)), "registry.path")
registry_case("machine path in a profile", registry_rows(base_row(edt_profile="C:/profiles/dev")), "registry.path")

registry_case("byte order mark", "\ufeff" + registry_rows(base_row()), None)
# The header is a prefix: the standard adds columns over time and the project
# owns this file, so an upgrade must not turn every existing row into an error.
registry_case(
    "extra project column",
    registry_rows(base_row()).replace("owner\n", "owner\tbsp_version\n", 1).replace("\tteam\n", "\tteam\t3.1\n", 1),
    None,
)
registry_case("empty identity", registry_rows(base_row(project_id="", environment_id="")), "registry.value")
registry_case("identifier with a separator", registry_rows(base_row(project_id="erp/main")), "registry.value")
registry_case("port with a leading zero collides", registry_rows(base_row(), base_row(project_id="zup", server_port="06003")), "registry.port")
registry_case("row that does not match the header", registry_rows("erp\tdev"), "registry.row")

# A base that does not expose MCP is legitimate and needs no port.
registry_case("registered but not exposed", registry_rows(base_row(mcp_enabled="false", server_port="")), None)

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} scaffold check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All 1C scaffold checks passed.")
