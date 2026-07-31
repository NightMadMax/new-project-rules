#!/usr/bin/env python3
"""The YAxUnit report, read rather than retold.

Until now the skill said "прогнать тесты и вернуть отчёт" and nothing could read
one, so the result of a run was whatever the agent wrote down about it. That is
the failure mode this exists to remove: a run whose outcome is a paraphrase.

Two distinctions carry the design, and both are refusals to blur.

`SKIP` means the component is not installed. It never means "the run produced
nothing": a configured YAxUnit that wrote no report is a failure — the tests did
not run, and calling that a skip turns a broken pipeline into a green one.

A test that errored is not a test that failed, and neither is a test that was
skipped inside the suite. They are reported apart because they need different
actions: a failure is a defect in the code, an error is usually a defect in the
harness, and a skipped test is coverage nobody has.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path

STATUSES = ("PASS", "FAIL", "SKIP")
# What a run writes. Not a guess: YAxUnit is asked for jUnit output, which is
# the one format both it and every CI on the planet already speak.
DEFAULT_REPORT = "build/yaxunit/junit.xml"


class ReportError(Exception):
    """The report cannot be read, which is not the same as tests failing."""


@dataclass
class Case:
    name: str
    outcome: str  # passed | failed | error | skipped
    detail: str = ""


@dataclass
class Result:
    status: str
    reason: str
    total: int = 0
    failed: int = 0
    errored: int = 0
    skipped: int = 0
    cases: list[Case] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return self.total - self.failed - self.errored - self.skipped


def parse(text: str) -> Result:
    """A jUnit document as counts and the cases that did not pass."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        raise ReportError(f"отчёт не разбирается как XML: {error}") from error

    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        raise ReportError("в отчёте нет ни одного testsuite")

    cases: list[Case] = []
    for suite in suites:
        for case in suite.iter("testcase"):
            name = f"{case.get('classname', '')}.{case.get('name', '')}".strip(".")
            failure = case.find("failure")
            error = case.find("error")
            skipped = case.find("skipped")
            if failure is not None:
                cases.append(Case(name, "failed", (failure.get("message") or failure.text or "").strip()[:200]))
            elif error is not None:
                cases.append(Case(name, "error", (error.get("message") or error.text or "").strip()[:200]))
            elif skipped is not None:
                cases.append(Case(name, "skipped", (skipped.get("message") or "").strip()[:200]))
            else:
                cases.append(Case(name, "passed"))

    if not cases:
        # A document with suites and no cases is a run that started and tested
        # nothing. Reporting "0 failures" about it would be true and useless.
        raise ReportError("отчёт не содержит ни одного теста: прогон ничего не проверил")

    failed = sum(1 for case in cases if case.outcome == "failed")
    errored = sum(1 for case in cases if case.outcome == "error")
    skipped = sum(1 for case in cases if case.outcome == "skipped")
    status = "PASS" if not failed and not errored else "FAIL"
    reason = ("все тесты прошли" if status == "PASS"
              else f"провалено {failed}, ошибок {errored}")
    return Result(status, reason, len(cases), failed, errored, skipped,
                  [case for case in cases if case.outcome != "passed"])


def read(root: Path, report: str = DEFAULT_REPORT, *, installed: bool = True) -> Result:
    """The result of a run, or the honest reason there is none.

    `installed` is what the component catalog says about YAxUnit. It is the only
    thing that may turn a missing report into `SKIP`: without it, a suite that
    silently failed to start would be indistinguishable from a machine that
    never had the component.
    """
    path = root / report
    if not path.is_file():
        if not installed:
            return Result("SKIP", "YAxUnit не установлен: модульные тесты недоступны, "
                                  "остаются syntax и smoke")
        return Result("FAIL", f"YAxUnit установлен, но отчёта нет ({report}): "
                              "прогон не состоялся, и это не пропуск")
    try:
        return parse(path.read_bytes().decode("utf-8", errors="replace"))
    except ReportError as error:
        return Result("FAIL", str(error))


def render(result: Result) -> str:
    lines = [f"[{result.status}] YAxUnit — {result.reason}"]
    if result.total:
        lines.append(f"        тестов: {result.total}, прошло: {result.passed}, "
                     f"провалено: {result.failed}, ошибок: {result.errored}, "
                     f"пропущено внутри набора: {result.skipped}")
    for case in result.cases:
        lines.append(f"        [{case.outcome}] {case.name}" + (f" — {case.detail}" if case.detail else ""))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--report", default=DEFAULT_REPORT, help="jUnit отчёт прогона")
    parser.add_argument("--not-installed", action="store_true",
                        help="YAxUnit отсутствует: отчёта нет и это SKIP, а не отказ")
    arguments = parser.parse_args(argv)
    result = read(Path(arguments.root).resolve(), arguments.report,
                  installed=not arguments.not_installed)
    print(render(result))
    # A failing suite is a failing command: this one is called from a workflow
    # that has to stop, unlike the diagnosis.
    return 1 if result.status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
