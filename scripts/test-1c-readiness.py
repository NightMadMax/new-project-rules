#!/usr/bin/env python3
"""The readiness matrix must describe the delivery, not last month's delivery.

A table of "what is checked and by what" rots the moment a criterion is added or
a test is renamed, and a rotten table is worse than none: it reads as evidence.
So the matrix is compared against the plan it summarises, and every claim in it
has to point at something that exists — a test file or a recorded defect.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PLAN = ROOT / "docs/architecture/ONE_C_CAPABILITY_PLAN.md"
MATRIX = ROOT / "docs/quality/READINESS_1C.md"
DEFECTS = ROOT / "docs/quality/DEFECTS.md"
TOOLS = ROOT / "TOOLS.md"
STATUSES = ("тест", "частично", "Windows", "не выполнено")
TESTING = ROOT / "docs/quality/TESTING.md"
CI = ROOT / ".github/workflows/ci.yml"
CONDITIONAL = ("Node.js", "Pillow", "OpenSpec", "v8unpack", "YAxUnit", "BSL Language Server")
OUT_OF_SCOPE = ("CI/CD", "хранилищ", "SonarQube", "АПК", "cfu")

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def plan_criteria() -> list[str]:
    text = read(PLAN)
    block = text[text.index("## Критерии готовности"):]
    block = block[: block.index("\n## ", 10)] if "\n## " in block[10:] else block
    criteria, current = [], []
    for line in block.splitlines()[1:]:
        if line.startswith("- "):
            if current:
                criteria.append(" ".join(current))
            current = [line[2:].strip()]
        elif current and line.startswith("  "):
            current.append(line.strip())
    if current:
        criteria.append(" ".join(current))
    return criteria


def matrix_rows() -> list[dict[str, str]]:
    rows = []
    for line in read(MATRIX).splitlines():
        match = re.match(r"^\|\s*(\d+)\s*\|(.+?)\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", line)
        if match:
            rows.append({
                "number": int(match.group(1)),
                "criterion": match.group(2).strip(),
                "status": match.group(3).strip(),
                "evidence": match.group(4).strip(),
            })
    return rows


def open_defects() -> set[str]:
    """Only the open ones: a criterion cannot lean on a defect already closed."""
    defects = read(DEFECTS)
    return set(re.findall(r"^\|\s*(\d+)\s*\|", defects[defects.index("## Open"): defects.index("## Fixed")], re.M))


def words(text: str) -> list[str]:
    """Comparable form: the words, without markup and case."""
    return re.sub(r"[^\w\s]", " ", text.lower()).split()


def check_test(where: str, name: str) -> None:
    name = name.strip().strip("`")
    if not (ROOT / name).is_file():
        failures.append(f"{where}: names a test that does not exist: {name}")
        return
    # A proof that nobody runs is not a proof: the named test must be in the
    # documented set and in the pipeline.
    base = Path(name).name
    if base not in read(TESTING):
        failures.append(f"{where}: {base} is not in TESTING.md")
    if base not in read(CI):
        failures.append(f"{where}: {base} does not run in ci.yml")


# --- the matrix against the plan ---------------------------------------------

criteria = plan_criteria()
rows = matrix_rows()
note(len(criteria) >= 30, f"the plan should hold the readiness criteria, found {len(criteria)}")
note(len(rows) == len(criteria),
     f"the matrix covers {len(rows)} criteria against {len(criteria)} in the plan")
note([row["number"] for row in rows] == list(range(1, len(rows) + 1)),
     "the matrix must be numbered as the plan is, without gaps")

for row in rows:
    where = f"criterion {row['number']}"
    note(row["status"] in STATUSES, f"{where}: unknown status '{row['status']}'")
    evidence = [part.strip() for part in row["evidence"].split(",")]
    if row["status"] == "тест":
        check_test(where, evidence[0])
    elif row["status"] == "частично":
        # Partly checked means two claims, and both have to be backed.
        note(len(evidence) == 2, f"{where}: 'частично' needs a test and a defect, got '{row['evidence']}'")
        if len(evidence) == 2:
            check_test(where, evidence[0])
            note(evidence[1].lstrip("№") in open_defects(),
                 f"{where}: names defect {evidence[1]}, which is not open in DEFECTS.md")
    elif row["status"] == "не выполнено":
        note(evidence[0].lstrip("№") in open_defects(),
             f"{where}: names defect {evidence[0]}, which is not open in DEFECTS.md")
    else:
        note("веха" in row["evidence"].lower(),
             f"{where}: a Windows criterion must point at the milestone, not '{row['evidence']}'")

    # The row must still be about the criterion it claims to be about: a
    # reformulation in the plan has to reach the matrix, not sit unnoticed.
    if row["number"] <= len(criteria):
        planned, stated = set(words(criteria[row["number"] - 1])), set(words(row["criterion"]))
        shared = len(planned & stated)
        note(shared >= 3 or shared >= len(stated) // 2,
             f"{where}: the row no longer matches the plan's wording: '{row['criterion']}'")

# The count in the summary is the one number a reader takes away, so it is
# derived from the table rather than typed beside it.
summary = read(MATRIX)
summary = summary[summary.index("## Итог"):]
counts = {name: sum(1 for row in rows if row["status"] == name) for name in STATUSES}
for name, expected in counts.items():
    note(re.search(rf"{re.escape(name)}`?\D{{0,4}}{expected}\b", summary) is not None,
         f"the summary must say {expected} for '{name}': {counts}")

# A defect may be open or fixed, never both: the section a row lives in is its
# status, so two rows mean two contradictory statuses.
defects = read(DEFECTS)
open_block = defects[defects.index("## Open"): defects.index("## Fixed")]
fixed_block = defects[defects.index("## Fixed"):]
both = set(re.findall(r"^\|\s*(\d+)\s*\|", open_block, re.M)) & set(re.findall(r"^\|\s*(\d+)\s*\|", fixed_block, re.M))
note(not both, f"defects listed as both open and fixed: {sorted(both)}")

# --- what the criteria demand of the documentation ---------------------------

tools = read(TOOLS)
if "## Условные компоненты 1С" not in tools:
    failures.append("TOOLS.md must hold the section on conditional components")
else:
    section = tools[tools.index("## Условные компоненты 1С"):]
    section = section[: section.index("\n## ", 10)]
    for component in CONDITIONAL:
        note(component in section, f"the conditional components section must name {component}")

# In the section that states the boundaries, not anywhere in the guides: the
# same words appear in unrelated documents and would prove nothing.
guide = read(ROOT / "docs/guides/USE_THIS_PROJECT.md")
if "## Проекты 1С: чего в первой версии нет" not in guide:
    failures.append("the user guide must hold the section on what v1 does not do")
else:
    section = guide[guide.index("## Проекты 1С: чего в первой версии нет"):]
    section = section[: section.index("\n## ", 10)]
    for refusal in OUT_OF_SCOPE:
        note(refusal in section, f"the section on v1 boundaries must name '{refusal}'")

# --- the link checker reports and does not fail ------------------------------

spec = importlib.util.spec_from_file_location("links", SCRIPTS / "check-1c-component-links.py")
assert spec and spec.loader
links = importlib.util.module_from_spec(spec)
spec.loader.exec_module(links)

found = links.links(ROOT)
note(bool(found), "the component catalog should hold external links to check")


class Unreachable:
    def __call__(self, *arguments, **keywords):
        raise OSError("no network here")


class Moved:
    def __enter__(self):
        return self

    def __exit__(self, *arguments):
        return False

    status = 404

    def __call__(self, *arguments, **keywords):
        return self


report = links.report(ROOT, opener=Unreachable())
note(all(status == "UNREACHABLE" for _, status, _ in report), "an unreachable source must be a status")
note(len(report) == len(found), "every link must appear in the report")

report = links.report(ROOT, opener=Moved())
note(all(status == "MOVED" for _, status, _ in report), "a moved source must be a status")

offline = links.report(ROOT, network=False)
note(all(status == "SKIP" for _, status, _ in offline), "without --network every link is a SKIP")

# The whole point: a source that moved must not fail a build.
import subprocess  # noqa: E402

result = subprocess.run(
    [sys.executable, str(SCRIPTS / "check-1c-component-links.py"), "--root", str(ROOT)],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
)
note(result.returncode == 0, f"the link check must be report-only: exit {result.returncode}")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} readiness check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print(f"Readiness matrix covers all {len(rows)} criteria.")
