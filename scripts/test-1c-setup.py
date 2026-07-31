#!/usr/bin/env python3
"""Setup must ask the whole question, install only what was approved, and leave
the repository alone.

Each of these was a line in a skill before. A prompt written by hand is short
exactly where it matters — what breaks on refusal, whether it needs admin — and
"the command exited zero" was allowed to stand in for "the component is there".
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent


def module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


components = module("one_c_components")
setup = module("one_c_setup")

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def catalog_text(rows: list[str]) -> str:
    return "\t".join(components.COLUMNS) + "\n" + "\n".join(rows) + "\n"


def row(**overrides: str) -> str:
    values = {
        "component": "Тестовый компонент", "class": "conditional", "purpose": "зачем",
        "enables": "что включает", "consequence": "что сломается", "version": "1.0",
        "download": "https://example.invalid/download", "docs": "https://example.invalid/docs",
        "install": "manual", "command": "", "admin": "no", "restart": "no", "network": "yes",
        "credentials": "no", "license": "no", "platform": "any", "detect": "cli:example",
    }
    values.update(overrides)
    return "\t".join(values[column] for column in components.COLUMNS)


def catalog(root: Path, rows: list[str]) -> Path:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / components.CATALOG).write_bytes(catalog_text(rows).encode("utf-8"))
    return root


# --- the shipped catalog is the one that has to hold up ----------------------

shipped = components.load(ROOT)
note(len(shipped) >= 15, f"the shipped catalog looks short: {len(shipped)} components")
note({item.component_class for item in shipped} == set(components.CLASSES),
     "all three classes must be present: skipping one is what makes the class column matter")
for component in shipped:
    text = components.prompt(component)
    for field in components.PROMPT_FIELDS:
        note(f"{field}:" in text, f"{component.name}: the prompt drops the field '{field}'")
    note(len(components.options(component, found=False)) == 3,
         f"{component.name}: a missing component must offer three answers")
    note(len(components.options(component, found=True)) == 3,
         f"{component.name}: a found component must offer three answers")

# The plan's own table and the machine catalog must name the same components:
# two lists of components is two answers to what `required` means.
plan_text = (ROOT / "docs/architecture/one-c/ENVIRONMENT_SETUP_PLAN.md").read_bytes().decode("utf-8")
for component in shipped:
    key = component.name.split()[0].rstrip(":")
    note(key in plan_text, f"{component.name} is in the catalog and not in the subplan table")

# --- a row that would shorten the question is an error -----------------------

with tempfile.TemporaryDirectory() as raw:
    root = catalog(Path(raw), [row(consequence="")])
    try:
        components.load(root)
        failures.append("an empty field must be refused: the prompt would silently drop it")
    except components.CatalogError:
        pass

    catalog(root, [row(**{"class": "nice-to-have"})])
    try:
        components.load(root)
        failures.append("an unknown class must be refused")
    except components.CatalogError:
        pass

    catalog(root, [row(install="project-local", command="")])
    try:
        components.load(root)
        failures.append("an install that promises a command and names none must be refused")
    except components.CatalogError:
        pass

    catalog(root, [row(), row()])
    try:
        components.load(root)
        failures.append("a duplicated component must be refused")
    except components.CatalogError:
        pass

# --- the three classes carry different consequences --------------------------

with tempfile.TemporaryDirectory() as raw:
    root = catalog(Path(raw), [
        row(component="Обязательный", **{"class": "required"}, detect="cli:absent-required"),
        row(component="Условный", **{"class": "conditional"}, detect="cli:absent-conditional"),
        row(component="Необязательный", **{"class": "optional"}, detect="cli:absent-optional"),
    ])
    loaded = components.load(root)
    ready = components.outcome(loaded, skipped={"Необязательный"})
    note(ready["status"] == "ready", f"skipping an optional component must not change the status: {ready}")
    partial = components.outcome(loaded, skipped={"Условный"})
    note(partial["status"] == "ready" and partial["disabled_features"],
         f"skipping a conditional component must name the disabled features: {partial}")
    incomplete = components.outcome(loaded, skipped={"Обязательный"})
    note(incomplete["status"] == "incomplete", f"skipping a required component must be incomplete: {incomplete}")

# --- setup installs only what was approved, and checks the result ------------


class Detector:
    """A CLI that appears only after its install command has run."""

    def __init__(self, appears_after: str = ""):
        self.appears_after = appears_after
        self.installed = False

    def __call__(self, name: str):
        class Found:
            pass

        found = Found()
        found.status = "ok" if self.installed else "skipped"
        found.version = "1.0"
        found.path = "/tmp/example"
        found.diagnostics = ["не найден"]
        return found


class Runner:
    def __init__(self, code: int = 0, detector: Detector | None = None):
        self.code = code
        self.detector = detector
        self.commands: list[str] = []

    def __call__(self, command: str):
        self.commands.append(command)
        if self.code == 0 and self.detector is not None:
            self.detector.installed = True
        return self.code, "output"


def tree(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes()
            for path in sorted(root.rglob("*")) if path.is_file()}


with tempfile.TemporaryDirectory() as raw:
    standard = catalog(Path(raw) / "standard", [
        row(component="Автоматический", install="project-local", command="install-me",
            detect="cli:example"),
        row(component="Ручной", detect="cli:manual-example"),
        row(component="Обязательный", **{"class": "required"}, detect="cli:required-example"),
    ])
    project = Path(raw) / "project"
    (project / "docs").mkdir(parents=True)
    (project / "README.md").write_bytes(b"project\n")
    (project / ".dev.env").write_bytes(b"DEFAULT_PASSWORD=hunter2\n")
    before = tree(project)

    # A plan writes nothing and shows the prompt for every component.
    detector = Detector()
    rows = setup.plan(project, standard, discover=detector)
    note(len(rows) == 3, f"the plan must cover every catalog component: {rows}")
    note(all(item["prompt"] for item in rows), "every component must arrive with its prompt")
    note(tree(project) == before, "a plan must not write into the project")

    # The provider is asked through the discovery that refuses to start
    # containers, not through a second implementation living here.
    state = setup.provider_state(project)
    note(state["resolved"] is False and state["detail"],
         f"a project without an MCP catalog must say so, not report a provider: {state}")

    # Nothing runs without a recorded decision.
    runner = Runner(detector=detector)
    steps, summary = setup.apply(project, standard, {}, runner=runner, discover=detector)
    note(runner.commands == [], f"no decision means no command: {runner.commands}")
    note(all(step.result == "manual-pending" for step in steps), f"unanswered components: {steps}")
    note(summary["status"] == "incomplete",
         f"a required component nobody answered about leaves the environment incomplete: {summary}")

    # An approved automatic install runs the catalog's command — and only it.
    detector = Detector()
    runner = Runner(detector=detector)
    steps, summary = setup.apply(project, standard,
                                 {"Автоматический": components.MISSING_OPTIONS[0]},
                                 runner=runner, discover=detector)
    note(runner.commands == ["install-me"], f"only the declared command may run: {runner.commands}")
    installed = [step for step in steps if step.component == "Автоматический"]
    note(installed and installed[0].result == "installed", f"a successful install must be recorded: {steps}")
    note(tree(project) == before, "an install must not write into the project")

    # The command succeeding is not the evidence: if the component is still not
    # detectable, the step failed.
    detector = Detector()
    runner = Runner(detector=None)  # exits zero, installs nothing
    steps, _ = setup.apply(project, standard, {"Автоматический": components.MISSING_OPTIONS[0]},
                           runner=runner, discover=detector)
    lying = [step for step in steps if step.component == "Автоматический"]
    note(lying and lying[0].result == "failed",
         f"a command that exits zero without installing anything must not count: {steps}")

    # A failing install leaves the repository byte-for-byte where it was.
    detector = Detector()
    runner = Runner(code=1, detector=detector)
    steps, summary = setup.apply(project, standard, {"Автоматический": components.MISSING_OPTIONS[0]},
                                 runner=runner, discover=detector)
    note(tree(project) == before, "a failed install must not touch the finished repository")
    note(summary["status"] == "incomplete", f"a failure must be visible in the outcome: {summary}")

    # A decision that is not one of the offered answers is a refusal.
    try:
        setup.apply(project, standard, {"Автоматический": "поставь молча"},
                    runner=Runner(), discover=Detector())
        failures.append("an unknown decision must be refused, not treated as approval")
    except setup.SetupError:
        pass

    # A decision cannot smuggle in a command of its own: only the catalog's runs.
    runner = Runner(detector=Detector())
    try:
        setup.apply(project, standard,
                    {"Ручной": components.MISSING_OPTIONS[0]},
                    runner=runner, discover=Detector())
        failures.append("automatic install of a component with no command must be refused")
    except setup.SetupError:
        pass
    note(runner.commands == [], f"nothing may run for a component with no command: {runner.commands}")

    # A skip names what it costs.
    steps, summary = setup.apply(project, standard,
                                 {"Обязательный": components.MISSING_OPTIONS[2]},
                                 runner=Runner(), discover=Detector())
    skipped = [step for step in steps if step.component == "Обязательный"]
    note(skipped and skipped[0].result == "skipped" and skipped[0].detail,
         f"a skip must carry its consequence: {steps}")
    note("Обязательный" in summary["skipped_required"], f"a skipped required must be named: {summary}")

    # An unreadable decision file is a refusal, not an empty set of decisions.
    broken = Path(raw) / "decisions.json"
    broken.write_bytes(b"[]")
    try:
        setup.read_decisions(broken)
        failures.append("decisions must be a mapping of component to answer")
    except setup.SetupError:
        pass
    good = Path(raw) / "good.json"
    good.write_bytes(json.dumps({"Автоматический": components.MISSING_OPTIONS[2]}).encode("utf-8"))
    note(setup.read_decisions(good) == {"Автоматический": components.MISSING_OPTIONS[2]},
         "a recorded decision must survive the round trip")

    # A decision about something the catalog does not have is a mistake worth
    # stopping for: it usually means the catalog moved under the answers.
    try:
        setup.apply(project, standard, {"Придуманный": components.MISSING_OPTIONS[2]},
                    runner=Runner(), discover=Detector())
        failures.append("a decision about an unknown component must be refused")
    except setup.SetupError:
        pass

    # The environment file is read for keys, never for values.
    settings = setup.environment(project)
    note(settings.get("DEFAULT_PASSWORD") == "hunter2" and "hunter2" not in setup.render(
        *setup.apply(project, standard, {}, runner=Runner(), discover=Detector())),
        "a value must never reach the setup report")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} setup check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("Setup and component catalog checks passed.")
