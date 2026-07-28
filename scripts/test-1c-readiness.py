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
from urllib.error import HTTPError
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

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def section(text: str, heading: str, where: str) -> str:
    """The block under a heading, or a message naming the heading that moved."""
    if heading not in text:
        failures.append(f"{where}: no section '{heading}'")
        return ""
    block = text[text.index(heading):]
    tail = block.index("\n## ", len(heading)) if "\n## " in block[len(heading):] else len(block)
    return block[:tail]


def plan_criteria() -> list[str]:
    block = section(read(PLAN), "## Критерии готовности", "the plan")
    criteria, current = [], []
    for line in block.splitlines()[1:]:
        stripped = line.strip()
        if line.startswith("- "):
            if current:
                criteria.append(" ".join(current))
            current = [line[2:].strip()]
        elif stripped.startswith("- ") and line.startswith(" "):
            # A nested bullet is a criterion the matrix would never see: the
            # count would still match while a requirement quietly disappeared.
            failures.append(f"the plan holds a nested criterion, which the matrix cannot mirror: {stripped[:60]}")
        elif current and line.startswith("  "):
            current.append(stripped)
    if current:
        criteria.append(" ".join(current))
    return criteria


def matrix_rows() -> list[dict[str, str]]:
    rows = []
    for raw in read(MATRIX).splitlines():
        # A wikilink alias is written as [[note\|name]]; the matrix legend uses
        # one, so the style of the document invites it into a cell too.
        line = raw.replace("\\|", "\x00")
        match = re.match(r"^\|\s*(\d+)\s*\|(.+?)\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", line)
        if match:
            rows.append({
                "number": int(match.group(1)),
                "criterion": match.group(2).replace("\x00", "|").strip(),
                "status": match.group(3).replace("\x00", "|").strip(),
                "evidence": match.group(4).replace("\x00", "|").strip(),
            })
    return rows


def open_defects() -> set[str]:
    """Only the open ones: a criterion cannot lean on a defect already closed."""
    return set(re.findall(r"^\|\s*(\d+)\s*\|", section(read(DEFECTS), "## Open", "DEFECTS.md"), re.M))


# Words that flip the meaning of a sentence without changing many others.
POLARITY = {"не", "нет", "только", "без", "невозможно", "запрещено", "обязателен", "обязательно"}


def words(text: str) -> set[str]:
    """Comparable form: the words, without markup and case.

    A hyphen stays inside a word: "не-Windows" is one word, and splitting it
    would hand the polarity check a "не" that means nothing.
    """
    return set(re.sub(r"[^\w\s-]", " ", text.lower()).split())


def same_subject(planned: str, stated: str) -> tuple[bool, str]:
    """Is the row still about this criterion?

    Overlap alone cannot see an inversion: adding "не" to a sentence increases
    the shared words. So polarity words have to agree, and the rest is judged by
    the share of the union rather than by a count that stop words can reach.
    """
    left, right = words(planned), words(stated)
    # The row is a shortened criterion, so it may drop words the plan has. What
    # it may never do is introduce one that flips the meaning: "не работают"
    # against "работают" shares more words, not fewer.
    introduced = (right & POLARITY) - (left & POLARITY)
    if introduced:
        return False, f"the row adds a word that flips the meaning: {', '.join(sorted(introduced))}"
    union = left | right
    if not union:
        return False, "empty criterion"
    overlap = len(left & right) / len(right or union)
    return overlap >= 0.5, f"only {overlap:.0%} of the row's words are in the plan's wording"


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
        for name in evidence:
            check_test(where, name)
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
    elif row["status"] == "Windows":
        note("веха" in row["evidence"].lower(),
             f"{where}: a Windows criterion must point at the milestone, not '{row['evidence']}'")

    # The row must still be about the criterion it claims to be about: a
    # reformulation in the plan has to reach the matrix, not sit unnoticed.
    if row["number"] <= len(criteria):
        matches, reason = same_subject(criteria[row["number"] - 1], row["criterion"])
        note(matches, f"{where}: {reason}: '{row['criterion']}'")

# The count in the summary is the one number a reader takes away, so it is
# derived from the table rather than typed beside it.
summary = section(read(MATRIX), "## Итог", "the matrix")
counts = {name: sum(1 for row in rows if row["status"] == name) for name in STATUSES}
stated = re.search(
    r"Из (\d+) критери\w+: `тест` — (\d+), `частично` — (\d+), `Windows` — (\d+), `не выполнено` — (\d+)",
    summary)
if stated is None:
    failures.append("the summary must state the counts in one parsable line")
else:
    total, by_status = int(stated.group(1)), [int(stated.group(index)) for index in (2, 3, 4, 5)]
    note(total == len(rows), f"the summary says {total} criteria against {len(rows)} rows")
    note(by_status == [counts[name] for name in STATUSES],
         f"the summary says {by_status} against {[counts[name] for name in STATUSES]}")

# A defect may be open or fixed, never both: the section a row lives in is its
# status, so two rows mean two contradictory statuses.
defects = read(DEFECTS)
open_block = section(defects, "## Open", "DEFECTS.md")
fixed_block = defects[defects.index("## Fixed"):] if "## Fixed" in defects else ""
both = set(re.findall(r"^\|\s*(\d+)\s*\|", open_block, re.M)) & set(re.findall(r"^\|\s*(\d+)\s*\|", fixed_block, re.M))
note(not both, f"defects listed as both open and fixed: {sorted(both)}")

# --- what the criteria demand of the documentation ---------------------------

components = section(read(TOOLS), "## Условные компоненты 1С", "TOOLS.md")
for component in CONDITIONAL:
    note(component in components, f"the conditional components section must name {component}")

# In the section that states the boundaries, not anywhere in the guides: the
# same words appear in unrelated documents and would prove nothing.
boundaries = section(read(ROOT / "docs/guides/USE_THIS_PROJECT.md"),
                     "## Проекты 1С: чего в первой версии нет", "the user guide")
for refusal in OUT_OF_SCOPE:
    note(refusal in boundaries, f"the section on v1 boundaries must name '{refusal}'")

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
    """A page that is gone arrives as an exception, which is how urlopen works."""

    def __init__(self, code: int = 404):
        self.code = code
        self.calls = 0

    def __call__(self, request, *arguments, **keywords):
        self.calls += 1
        raise HTTPError(request.full_url, self.code, "Not Found", {}, None)


class RefusesHead:
    """A vendor portal that answers HEAD with 405 and GET with 200."""

    def __init__(self):
        self.methods = []

    def __call__(self, request, *arguments, **keywords):
        self.methods.append(request.get_method())
        if request.get_method() == "HEAD":
            raise HTTPError(request.full_url, 405, "Method Not Allowed", {}, None)
        return Response()


class Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *arguments):
        return False


report = links.report(ROOT, opener=Unreachable())
note(all(status == "UNREACHABLE" for _, status, _ in report), "an unreachable source must be a status")
note(len(report) == len(found), "every link must appear in the report")

report = links.report(ROOT, opener=Moved())
note(all(status == "MOVED" for _, status, _ in report),
     "a moved source must be a status, not a network failure")

# A portal that refuses HEAD is not a portal that moved.
refuses = RefusesHead()
report = links.report(ROOT, opener=refuses)
note(all(status == "OK" for _, status, _ in report), "a refused HEAD must be retried with GET")
note("GET" in refuses.methods, "the retry must actually use GET")

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
