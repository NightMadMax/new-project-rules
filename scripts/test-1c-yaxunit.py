#!/usr/bin/env python3
"""A test run reports what the report says, and `SKIP` keeps its meaning.

The criterion asks for the report of a run. The failure mode it guards against
is the one that looks like success: a suite that never started, summarised as
"пропущено", and a pipeline that stays green because nothing ran.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("one_c_yaxunit", SCRIPTS / "one_c_yaxunit.py")
assert spec and spec.loader
yaxunit = importlib.util.module_from_spec(spec)
sys.modules["one_c_yaxunit"] = yaxunit
spec.loader.exec_module(yaxunit)

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


GREEN = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="ОбщийМодуль.ТестыРасчёта" tests="2">
    <testcase classname="ТестыРасчёта" name="СуммаБезНДС"/>
    <testcase classname="ТестыРасчёта" name="СуммаСНДС"/>
  </testsuite>
</testsuites>
"""

MIXED = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="ТестыДокумента" tests="4">
    <testcase classname="ТестыДокумента" name="Проведение"/>
    <testcase classname="ТестыДокумента" name="Отмена">
      <failure message="Ожидали 0, получили 15">Стек</failure>
    </testcase>
    <testcase classname="ТестыДокумента" name="Печать">
      <error message="Объект не найден"/>
    </testcase>
    <testcase classname="ТестыДокумента" name="Обмен">
      <skipped message="нет тестового контура"/>
    </testcase>
  </testsuite>
</testsuites>
"""

# --- the report is read, not retold ------------------------------------------

green = yaxunit.parse(GREEN)
note(green.status == "PASS" and green.total == 2 and green.passed == 2,
     f"a green run must be reported as passed: {green}")
note(not green.cases, "a green run needs no case list")

mixed = yaxunit.parse(MIXED)
note(mixed.status == "FAIL", f"a run with a failure is not a pass: {mixed}")
note((mixed.total, mixed.failed, mixed.errored, mixed.skipped) == (4, 1, 1, 1),
     f"failures, errors and skips must be counted apart: {mixed}")
note(mixed.passed == 1, f"passed is what is left, not what the suite claims: {mixed}")
rendered = yaxunit.render(mixed)
for expected in ("Отмена", "Ожидали 0, получили 15", "Печать", "Объект не найден", "Обмен"):
    note(expected in rendered, f"the report must name '{expected}': {rendered}")

# An error is not a failure: one is a defect in the code, the other usually in
# the harness, and they call for different work.
outcomes = {case.name.split(".")[-1]: case.outcome for case in mixed.cases}
note(outcomes.get("Отмена") == "failed" and outcomes.get("Печать") == "error"
     and outcomes.get("Обмен") == "skipped",
     f"each outcome must keep its own name: {outcomes}")

# --- what cannot be read is not a green run ----------------------------------

for broken, why in (("не xml", "a report that is not XML"),
                    ("<testsuites></testsuites>", "a report with no suites"),
                    ('<testsuite name="пусто" tests="0"></testsuite>', "a suite with no cases")):
    try:
        yaxunit.parse(broken)
        failures.append(f"{why} must not be read as a result")
    except yaxunit.ReportError:
        pass

# --- SKIP means the component is missing, and nothing else -------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    absent = yaxunit.read(root, installed=False)
    note(absent.status == "SKIP" and "не установлен" in absent.reason,
         f"without the component the run is a SKIP with its reason: {absent}")

    # The case the criterion is really about: the component is there, the run
    # produced nothing. Calling that a skip is how a broken pipeline stays green.
    silent = yaxunit.read(root, installed=True)
    note(silent.status == "FAIL" and "не состоялся" in silent.reason,
         f"an installed component with no report is a failure, not a skip: {silent}")

    (root / "build/yaxunit").mkdir(parents=True)
    (root / yaxunit.DEFAULT_REPORT).write_bytes(GREEN.encode("utf-8"))
    note(yaxunit.read(root).status == "PASS", "a written report must be read from its default place")

    (root / yaxunit.DEFAULT_REPORT).write_bytes(MIXED.encode("utf-8"))
    failing = yaxunit.read(root)
    note(failing.status == "FAIL" and failing.failed == 1,
         f"a report with failures must fail the step: {failing}")

    # And the exit code follows the result: this is called from a workflow that
    # has to stop, unlike the diagnosis, which reports and returns zero.
    note(yaxunit.main(["--root", str(root)]) == 1, "a failing suite must exit non-zero")
    (root / yaxunit.DEFAULT_REPORT).write_bytes(GREEN.encode("utf-8"))
    note(yaxunit.main(["--root", str(root)]) == 0, "a passing suite must exit zero")
    (root / yaxunit.DEFAULT_REPORT).unlink()
    note(yaxunit.main(["--root", str(root), "--not-installed"]) == 0,
         "an absent component must not fail the run")

# --- the skill says what the executor does -----------------------------------

skill = (SCRIPTS.parent / "templates/new-project/capabilities/1c/.agents/skills"
         / "deploy-and-test-1c/SKILL.md").read_bytes().decode("utf-8")
note("one_c_yaxunit.py" in skill, "the skill must name the executor that reads the report")
note("SKIP" in skill and "не установлен" in skill,
     "the skill must keep the distinction between a skip and a run that produced nothing")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} yaxunit check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("YAxUnit report checks passed.")
