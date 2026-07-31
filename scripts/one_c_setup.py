#!/usr/bin/env python3
"""The setup step: propose components, change the machine only after approval.

Two boundaries make this safe to run on a finished project, and both are code
rather than intention.

The repository is not part of the transaction. Setup changes the machine — a
package, a plugin, a token — and a failure there must not reach the project that
was just created and validated. So this executor never writes inside the project
root: everything it produces is a report.

Approval is per component and explicit. A decision arrives as a recorded answer
to the prompt of `one_c_components`, and only the answer "установить
автоматически" may run anything — and only the command the catalog declares. An
unknown answer is a refusal, not a default.

After every install the state is checked again by the same detector that found
it missing. "The command exited zero" is not evidence that a component is there.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import cli_discovery  # noqa: E402
from one_c_components import (  # noqa: E402
    CatalogError, Component, FOUND_OPTIONS, MISSING_OPTIONS, load, outcome, prompt,
)

APPROVED, MANUAL, SKIPPED = MISSING_OPTIONS
USE, REINSTALL, DROP = FOUND_OPTIONS
DECISIONS = (*MISSING_OPTIONS, *FOUND_OPTIONS)
INSTALL_TIMEOUT_SECONDS = 600


class SetupError(Exception):
    """Setup refuses to proceed, and this says why."""


@dataclass
class State:
    component: str
    found: bool
    detail: str


@dataclass
class Step:
    component: str
    decision: str
    result: str  # installed | failed | manual-pending | skipped | already
    detail: str = ""
    commands: list[str] = field(default_factory=list)


def environment(root: Path, relative: str = ".dev.env") -> dict[str, str]:
    """Local settings as keys and whether they are set — values stay out.

    Setup reads this file to learn that a token or a plugin has been recorded,
    which is a yes/no question. Carrying the value into a report would repeat
    the incident the diagnostics allowlist exists for.
    """
    path = root / relative
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_bytes().decode("utf-8", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if separator:
            values[name.strip()] = value.strip()
    return values


def module_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def detect(component: Component, root: Path, *, settings: dict[str, str] | None = None,
           discover=cli_discovery.discover, provider=None) -> State:
    """Whether the component is actually there — never whether it should be."""
    settings = environment(root) if settings is None else settings
    scheme, target = component.scheme, component.target
    if scheme == "cli":
        found = discover(target)
        if found.status == "ok":
            return State(component.name, True, f"{found.version or 'версия не сообщается'} — {found.path}")
        return State(component.name, False, "; ".join(found.diagnostics)[:200])
    if scheme == "runtime" and target == "python":
        # The interpreter running this code is the answer. Asking PATH for
        # `python3` on Windows finds the zero-byte App Execution Alias and
        # reports "missing" about the very Python that is executing the check —
        # defect 61 inverted.
        version = ".".join(str(part) for part in sys.version_info[:3])
        return State(component.name, sys.version_info >= (3, 9),
                     f"{version} — {sys.executable}")
    if scheme == "python":
        return State(component.name, module_present(target),
                     f"модуль {target}" + ("" if module_present(target) else " не импортируется"))
    if scheme == "node":
        # A project-local package is a directory in the skill it belongs to, and
        # its absence is what the install command fixes.
        installed = (root / ".agents/skills/md-to-docx/node_modules" / target).is_dir()
        return State(component.name, installed, f"node_modules/{target}")
    if scheme == "env":
        value = settings.get(target, "")
        return State(component.name, bool(value),
                     f"{target}: задан" if value else f"{target} не записан в .dev.env")
    if scheme == "provider":
        if provider is None:
            return State(component.name, False, "provider manifest не проверялся")
        return State(component.name, bool(provider.get("resolved")),
                     provider.get("detail", ""))
    # `manual`: there is no honest machine check, and inventing one would report
    # a state nobody measured.
    return State(component.name, False, "проверяется человеком: машинной проверки нет")


def provider_state(root: Path) -> dict[str, object]:
    """What the external MCP provider answers, asked the read-only way.

    Delegated rather than re-implemented: the discovery that refuses to start a
    container lives in one place, and a second implementation here would be the
    one that forgets the refusal.
    """
    catalog = root / "config/1c-mcp-catalog.json"
    if not catalog.is_file():
        return {"resolved": False, "detail": "каталог ролей MCP отсутствует в проекте"}
    try:
        import one_c_provider
        from one_c_clients import ClientError, read_catalog

        rows = one_c_provider.discover(root, read_catalog(root))
    except (ImportError, ValueError) as error:
        return {"resolved": False, "detail": f"каталог не читается: {error}"}
    except ClientError as error:
        return {"resolved": False, "detail": str(error)}
    except one_c_provider.ProviderError as error:
        return {"resolved": False, "detail": str(error)}
    verified = [row for row in rows if row.status == "OK"]
    if not verified:
        first = rows[0].detail if rows else "каталог ролей пуст"
        return {"resolved": False, "detail": first}
    return {"resolved": True, "detail": f"ролей подтверждено: {len(verified)} из {len(rows)}"}


def applicable(component: Component) -> bool:
    return component.platform == "any" or (component.platform == "windows" and os.name == "nt")


def plan(root: Path, standard_root: Path, *, discover=cli_discovery.discover,
         provider=None) -> list[dict[str, object]]:
    """The report of what is there, what is missing, and what will be asked.

    Writes nothing anywhere: this is the step a user is expected to run on a
    machine they have not decided anything about yet.
    """
    settings = environment(root)
    # Asked once: one discovery answers about every role, and asking per
    # component would probe the same deployment again and again.
    provider = provider_state(root) if provider is None else provider
    rows: list[dict[str, object]] = []
    for component in load(standard_root):
        if not applicable(component):
            rows.append({
                "component": component.name, "class": component.component_class,
                "state": "n/a", "detail": f"нужен только на {component.platform}",
                "prompt": "",
            })
            continue
        state = detect(component, root, settings=settings, discover=discover, provider=provider)
        rows.append({
            "component": component.name,
            "class": component.component_class,
            "state": "found" if state.found else "missing",
            "detail": state.detail,
            "prompt": prompt(component, found=state.found, detail=state.detail if state.found else ""),
        })
    return rows


def read_decisions(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise SetupError(f"decisions are unreadable: {error}") from error
    if not isinstance(data, dict) or not all(isinstance(value, str) for value in data.values()):
        raise SetupError("decisions must map a component name to one recorded answer")
    return data


def run(command: str, runner) -> tuple[bool, str]:
    try:
        result = runner(command)
    except OSError as error:
        return False, f"не запускается: {error.strerror or error}"
    code, output = result
    return code == 0, (output or "").strip()[:200]


def default_runner(command: str) -> tuple[int, str]:
    completed = subprocess.run(command, shell=True, capture_output=True,
                               timeout=INSTALL_TIMEOUT_SECONDS, check=False)
    output = (completed.stdout or b"") + (completed.stderr or b"")
    return completed.returncode, output.decode("utf-8", errors="replace")


def apply(root: Path, standard_root: Path, decisions: dict[str, str], *,
          runner=default_runner, discover=cli_discovery.discover,
          provider=None) -> tuple[list[Step], dict[str, object]]:
    """Carry out only what was approved, then check the result for real."""
    components = load(standard_root)
    known = {component.name: component for component in components}
    unknown = sorted(set(decisions) - set(known))
    if unknown:
        raise SetupError(f"decisions name components the catalog does not have: {', '.join(unknown)}")

    steps: list[Step] = []
    skipped: set[str] = set()
    settings = environment(root)
    # Asked once: one discovery answers about every role, and asking per
    # component would probe the same deployment again and again.
    provider = provider_state(root) if provider is None else provider
    for component in components:
        if not applicable(component):
            continue
        state = detect(component, root, settings=settings, discover=discover, provider=provider)
        decision = decisions.get(component.name, "").strip()
        if decision and not any(decision.startswith(option) for option in DECISIONS):
            raise SetupError(f"{component.name}: unknown decision '{decision}'")
        if state.found:
            # Nothing to install. Reinstalling goes through the vendor installer,
            # which is the user's step, not ours.
            if decision.startswith(DROP):
                steps.append(Step(component.name, decision, "skipped", component.consequence))
                skipped.add(component.name)
            elif decision.startswith(REINSTALL):
                steps.append(Step(component.name, decision, "manual-pending",
                                  f"переустановка идёт штатным установщиком: {component.download}"))
            else:
                steps.append(Step(component.name, decision or USE, "already", state.detail))
            continue
        if not decision:
            # No answer is not consent: an unanswered component stays untouched
            # and is reported as still missing.
            steps.append(Step(component.name, "", "manual-pending", "решение не записано"))
            skipped.add(component.name)
            continue
        if decision.startswith(SKIPPED):
            steps.append(Step(component.name, decision, "skipped", component.consequence))
            skipped.add(component.name)
            continue
        if decision.startswith(MANUAL):
            steps.append(Step(component.name, decision, "manual-pending",
                              f"источник: {component.download}"))
            skipped.add(component.name)
            continue
        # Approved automatic install: the catalog's command, nothing else. A
        # decision cannot smuggle in a command of its own.
        command = component.command.strip()
        if not command:
            raise SetupError(f"{component.name}: automatic install approved, but the catalog names no command")
        succeeded, detail = run(command, runner)
        # The install is not the evidence. The detector that reported it missing
        # reports it again, and its answer is what the step records.
        after = detect(component, root, settings=environment(root), discover=discover, provider=provider)
        if succeeded and after.found:
            steps.append(Step(component.name, decision, "installed", after.detail, [command]))
        else:
            reason = detail if not succeeded else "команда завершилась успешно, но компонент не обнаружен"
            steps.append(Step(component.name, decision, "failed", reason, [command]))
            skipped.add(component.name)
    return steps, outcome(components, skipped)


def render(steps: list[Step], summary: dict[str, object]) -> str:
    lines = [f"[{step.result:14}] {step.component} — {step.detail}" for step in steps]
    lines.append(f"Итог: {summary['status']}")
    if summary["skipped_required"]:
        lines.append("Пропущены обязательные: " + ", ".join(summary["skipped_required"]))
    for disabled in summary["disabled_features"]:
        lines.append(f"Отключено: {disabled}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--standard-root", default=str(SCRIPTS.parent),
                        help="checkout of new-project-rules holding the catalog")
    parser.add_argument("--apply", metavar="DECISIONS",
                        help="JSON файл с записанными ответами; без него — только отчёт")
    arguments = parser.parse_args(argv)

    root = Path(arguments.root).resolve()
    standard_root = Path(arguments.standard_root).resolve()
    try:
        if not arguments.apply:
            for row in plan(root, standard_root):
                print(f"[{row['state']:7}] {row['component']} — {row['detail']}")
                if row["prompt"]:
                    print(row["prompt"])
                    print()
            return 0
        steps, summary = apply(root, standard_root, read_decisions(Path(arguments.apply)))
    except (CatalogError, SetupError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 2
    print(render(steps, summary))
    # A failed install is a reported state, not a broken run: the repository is
    # untouched either way, and an exit code that cries failure hides the report.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
