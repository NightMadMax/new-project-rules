#!/usr/bin/env python3
"""Level-1 project compression: dry-run report plus reversible archiving.

Deterministic, safe housekeeping for a standardized project. Reports by
default; ``--apply`` performs only reversible operations:
  * move aged ``Fixed`` defects into ``DEFECTS_ARCHIVE.md`` (text and running
    numbering preserved);
  * split an oversized ``CHANGELOG.md`` into ``CHANGELOG_ARCHIVE.md`` at
    version boundaries, keeping ``Unreleased`` plus the most recent releases;
  * remove regenerable cruft (``__pycache__``, ``.DS_Store``, empty ``.trash``).

Provenance is never deleted, only moved. Content judgement (merging research,
pruning promotion candidates, agent memory) belongs to the ``compress-project``
skill, not to this script.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence


MIN_PYTHON = (3, 9)
KB = 1024
IGNORED_PARTS = {".git"}

# Standard artifact locations, relative to the project root.
CHANGELOG = Path("CHANGELOG.md")
CHANGELOG_ARCHIVE = Path("CHANGELOG_ARCHIVE.md")
DEFECTS = Path("docs/quality/DEFECTS.md")
DEFECTS_ARCHIVE = Path("docs/quality/DEFECTS_ARCHIVE.md")

CHANGELOG_ARCHIVE_HEADER = (
    "# Архив журнала изменений\n"
    "\n"
    "Старые релизы, перенесённые из [[CHANGELOG]] при компрессии. Содержимое\n"
    "записей не менялось; порядок — от новых к старым.\n"
    "\n"
)

# Back-reference kept in CHANGELOG.md so the archive is not orphaned.
CHANGELOG_ARCHIVE_POINTER = "Старые релизы перенесены в [[CHANGELOG_ARCHIVE|архив журнала изменений]].\n"

FIXED_DATE_COLUMN = 3  # `| # | Title | Discovered | Fixed | Commit | Root Cause |`


@dataclass(frozen=True)
class Config:
    root: Path
    today: datetime.date
    changelog_max_bytes: int
    changelog_target_bytes: int
    changelog_keep: int
    fixed_max_age_days: int
    stale_days: int


@dataclass(frozen=True)
class Action:
    """A pending reversible change, shown in the report and run on --apply."""

    code: str
    summary: str


@dataclass(frozen=True)
class Notice:
    """A report-only observation; never mutated by this script."""

    severity: str  # WARN or INFO
    code: str
    message: str
    path: str = ""


@dataclass
class Plan:
    actions: list[Action] = field(default_factory=list)
    notices: list[Notice] = field(default_factory=list)
    writes: dict[Path, str] = field(default_factory=dict)
    deletes: list[Path] = field(default_factory=list)


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def parse_date(value: str) -> Optional[datetime.date]:
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        return None


# --- CHANGELOG splitting -----------------------------------------------------


def split_h2_blocks(text: str) -> tuple[str, list[str]]:
    """Split Markdown text into (preamble, [block, ...]) at level-2 headers.

    Each block starts at a ``## `` line and includes everything up to the next
    one, so concatenating preamble and blocks reproduces the input byte for
    byte.
    """
    preamble: list[str] = []
    blocks: list[str] = []
    current: Optional[list[str]] = None
    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            if current is not None:
                blocks.append("".join(current))
            current = [line]
        elif current is None:
            preamble.append(line)
        else:
            current.append(line)
    if current is not None:
        blocks.append("".join(current))
    return "".join(preamble), blocks


def split_changelog(
    text: str,
    archive_text: Optional[str],
    max_bytes: int,
    target_bytes: int,
    keep: int,
) -> Optional[tuple[str, str, int]]:
    """Return (new_changelog, new_archive, moved_count) or None if no split.

    A split happens only when the changelog exceeds ``max_bytes``. The oldest
    version blocks move to the archive until the changelog is at or below
    ``target_bytes`` or only ``keep`` releases remain, whichever comes first.
    ``Unreleased`` is always retained locally.
    """
    if len(text.encode("utf-8")) <= max_bytes:
        return None
    preamble, blocks = split_h2_blocks(text)
    unreleased = [b for b in blocks if b.startswith("## Unreleased")]
    versions = [b for b in blocks if not b.startswith("## Unreleased")]
    if len(versions) <= keep:
        return None

    def changelog_bytes(kept_versions: Sequence[str]) -> int:
        body = preamble + "".join(unreleased) + "".join(kept_versions)
        return len(body.encode("utf-8"))

    kept_n = len(versions)
    while kept_n > keep and changelog_bytes(versions[:kept_n]) > target_bytes:
        kept_n -= 1
    kept_versions = versions[:kept_n]
    moved_versions = versions[kept_n:]
    if not moved_versions:
        return None

    if "CHANGELOG_ARCHIVE" not in preamble:
        preamble = preamble.rstrip("\n") + "\n\n" + CHANGELOG_ARCHIVE_POINTER + "\n"
    new_changelog = preamble + "".join(unreleased) + "".join(kept_versions)

    if archive_text is None:
        arc_preamble, arc_versions = CHANGELOG_ARCHIVE_HEADER, []
    else:
        arc_preamble, arc_blocks = split_h2_blocks(archive_text)
        arc_versions = arc_blocks
    # Moved blocks are newer than anything already archived, so they lead.
    new_archive = arc_preamble + "".join(moved_versions) + "".join(arc_versions)
    return new_changelog, new_archive, len(moved_versions)


# --- DEFECTS archiving -------------------------------------------------------


def find_table(lines: Sequence[str], lo: int, hi: int) -> Optional[tuple[int, int]]:
    """Locate a Markdown table between lines[lo:hi].

    Returns (data_start, data_end): the half-open range of data rows below the
    ``| # |`` header and its separator, or None if no such table is present.
    """
    header = -1
    for i in range(lo, hi):
        if lines[i].lstrip().startswith("| # |"):
            header = i
            break
    if header == -1:
        return None
    data_start = header + 2  # skip header row and separator row
    data_end = data_start
    while data_end < hi and lines[data_end].lstrip().startswith("|"):
        data_end += 1
    return data_start, data_end


def section_end(lines: Sequence[str], start: int) -> int:
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            return j
    return len(lines)


def row_date(line: str, column: int) -> Optional[datetime.date]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if column >= len(cells):
        return None
    return parse_date(cells[column])


def archive_fixed_defects(
    defects_text: str,
    archive_text: Optional[str],
    today: datetime.date,
    max_age_days: int,
) -> Optional[tuple[str, str, int]]:
    """Move ``Fixed`` rows older than ``max_age_days`` into the archive table.

    Rows whose ``Fixed`` date cannot be parsed are left in place. Returns
    (new_defects, new_archive, moved_count) or None when nothing qualifies.
    """
    lines = defects_text.splitlines(keepends=True)
    fixed = next((i for i, ln in enumerate(lines) if ln.startswith("## Fixed")), -1)
    if fixed == -1:
        return None
    table = find_table(lines, fixed, section_end(lines, fixed))
    if table is None:
        return None
    data_start, data_end = table

    keep_rows: list[str] = []
    moved_rows: list[str] = []
    for line in lines[data_start:data_end]:
        fixed_date = row_date(line, FIXED_DATE_COLUMN)
        if fixed_date is not None and (today - fixed_date).days > max_age_days:
            moved_rows.append(line)
        else:
            keep_rows.append(line)
    if not moved_rows:
        return None

    new_defects = "".join(lines[:data_start] + keep_rows + lines[data_end:])

    if archive_text is None:
        return None  # a project without an archive table is not auto-created here
    arc_lines = archive_text.splitlines(keepends=True)
    arc_fixed = next((i for i, ln in enumerate(arc_lines) if ln.startswith("## Fixed")), -1)
    if arc_fixed == -1:
        return None
    arc_table = find_table(arc_lines, arc_fixed, section_end(arc_lines, arc_fixed))
    if arc_table is None:
        return None
    _, arc_data_end = arc_table
    new_archive = "".join(arc_lines[:arc_data_end] + moved_rows + arc_lines[arc_data_end:])
    return new_defects, new_archive, len(moved_rows)


# --- Cruft and staleness -----------------------------------------------------


def is_ignored(path: Path, root: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.relative_to(root).parts)


def find_cruft(root: Path) -> list[Path]:
    """Return regenerable throwaway paths: __pycache__, .DS_Store, empty .trash."""
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if is_ignored(path, root):
            continue
        if path.is_dir() and path.name == "__pycache__":
            found.append(path)
        elif path.is_file() and path.name == ".DS_Store":
            found.append(path)
    trash = root / ".trash"
    if trash.is_dir() and not any(trash.iterdir()):
        found.append(trash)
    return found


def frontmatter_field(text: str, key: str) -> Optional[str]:
    if not text.startswith("---\n"):
        return None
    lines = text.splitlines()
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    for line in lines[1:end]:
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            return stripped[len(key) + 1:].strip().strip('"\'')
    return None


def stale_frontmatter(root: Path, today: datetime.date, stale_days: int) -> list[Notice]:
    notices: list[Notice] = []
    for path in sorted(root.rglob("*.md")):
        if is_ignored(path, root):
            continue
        rel = relative(path, root)
        if rel.startswith("templates/"):
            continue
        text = read_text(path)
        if text is None:
            continue
        raw = frontmatter_field(text, "last_verified")
        if not raw:
            continue
        verified = parse_date(raw)
        if verified is None:  # placeholder such as <YYYY-MM-DD> or empty
            continue
        age = (today - verified).days
        if age > stale_days:
            notices.append(Notice(
                "WARN", "stale.last_verified",
                f"last_verified is {age} days old (> {stale_days}); review and refresh.",
                rel,
            ))
    return notices


# --- Planning and application ------------------------------------------------


def plan_compression(cfg: Config) -> Plan:
    plan = Plan()
    root = cfg.root

    cruft = find_cruft(root)
    for path in cruft:
        plan.deletes.append(path)
    if cruft:
        plan.actions.append(Action(
            "cruft.remove",
            f"Remove {len(cruft)} regenerable item(s): "
            + ", ".join(relative(p, root) for p in cruft),
        ))

    changelog = read_text(root / CHANGELOG)
    if changelog is not None:
        archive = read_text(root / CHANGELOG_ARCHIVE)
        result = split_changelog(
            changelog, archive,
            cfg.changelog_max_bytes, cfg.changelog_target_bytes, cfg.changelog_keep,
        )
        if result is not None:
            new_changelog, new_archive, moved = result
            plan.writes[root / CHANGELOG] = new_changelog
            plan.writes[root / CHANGELOG_ARCHIVE] = new_archive
            plan.actions.append(Action(
                "changelog.split",
                f"Move {moved} older release(s) from {CHANGELOG.as_posix()} to "
                f"{CHANGELOG_ARCHIVE.as_posix()}.",
            ))
        else:
            size_kb = len(changelog.encode("utf-8")) / KB
            plan.notices.append(Notice(
                "INFO", "changelog.size",
                f"CHANGELOG.md is {size_kb:.0f} KB "
                f"(limit {cfg.changelog_max_bytes // KB} KB); no split needed.",
            ))

    defects = read_text(root / DEFECTS)
    if defects is not None:
        archive = read_text(root / DEFECTS_ARCHIVE)
        result = archive_fixed_defects(defects, archive, cfg.today, cfg.fixed_max_age_days)
        if result is not None:
            new_defects, new_archive, moved = result
            plan.writes[root / DEFECTS] = new_defects
            plan.writes[root / DEFECTS_ARCHIVE] = new_archive
            plan.actions.append(Action(
                "defects.archive",
                f"Move {moved} Fixed defect(s) older than {cfg.fixed_max_age_days} "
                f"days to {DEFECTS_ARCHIVE.as_posix()}.",
            ))

    plan.notices.extend(stale_frontmatter(root, cfg.today, cfg.stale_days))
    return plan


def apply_plan(plan: Plan) -> None:
    for path in plan.deletes:
        if path.is_dir():
            for child in sorted(path.rglob("*"), reverse=True):
                child.unlink() if child.is_file() else child.rmdir()
            path.rmdir()
        elif path.exists():
            path.unlink()
    for path, content in plan.writes.items():
        path.write_text(content, encoding="utf-8")


def print_report(cfg: Config, plan: Plan, applied: bool) -> None:
    verb = "Applied" if applied else "Planned"
    print(f"Compression: {cfg.root.resolve()} (today={cfg.today.isoformat()})")
    if plan.actions:
        print(f"{verb} actions:")
        for action in plan.actions:
            print(f"  [{action.code}] {action.summary}")
    else:
        print("No reversible actions pending.")
    order = {"WARN": 0, "INFO": 1}
    notices = sorted(plan.notices, key=lambda n: (order[n.severity], n.code, n.path))
    for notice in notices:
        location = f" {notice.path}:" if notice.path else ":"
        print(f"[{notice.severity}] {notice.code}{location} {notice.message}")
    warn = sum(1 for n in plan.notices if n.severity == "WARN")
    print(f"Summary: {len(plan.actions)} action(s), {warn} warning(s).")


def build_config(args: argparse.Namespace) -> Config:
    today = parse_date(args.today) if args.today else datetime.date.today()
    if today is None:
        raise ValueError(f"--today must be YYYY-MM-DD: {args.today!r}")
    return Config(
        root=Path(args.root),
        today=today,
        changelog_max_bytes=args.changelog_max_kb * KB,
        changelog_target_bytes=args.changelog_target_kb * KB,
        changelog_keep=args.changelog_keep,
        fixed_max_age_days=args.fixed_max_age_days,
        stale_days=args.stale_days,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Level-1 project compression (report by default).")
    parser.add_argument("--root", default=".", help="Project root to compress.")
    parser.add_argument("--apply", action="store_true", help="Perform the reversible actions.")
    parser.add_argument("--today", default="", help="Override today's date (YYYY-MM-DD) for aging.")
    parser.add_argument("--changelog-max-kb", type=int, default=32, help="Split CHANGELOG.md above this size.")
    parser.add_argument("--changelog-target-kb", type=int, default=24, help="Target CHANGELOG.md size after a split.")
    parser.add_argument("--changelog-keep", type=int, default=5, help="Releases always kept in CHANGELOG.md.")
    parser.add_argument("--fixed-max-age-days", type=int, default=90, help="Archive Fixed defects older than this.")
    parser.add_argument("--stale-days", type=int, default=60, help="Warn when last_verified is older than this.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if sys.version_info < MIN_PYTHON:
        print(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required.", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    try:
        cfg = build_config(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    if not cfg.root.is_dir():
        print(f"Error: root is not a directory: {cfg.root}", file=sys.stderr)
        return 2
    plan = plan_compression(cfg)
    if args.apply:
        apply_plan(plan)
    print_report(cfg, plan, applied=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
