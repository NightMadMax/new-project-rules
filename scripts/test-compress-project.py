#!/usr/bin/env python3
"""Regression tests for the Level-1 project compression script."""

from __future__ import annotations

import datetime
import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = ROOT / "scripts" / "compress-project.py"
SPEC = importlib.util.spec_from_file_location("compress_project", SCRIPT_PATH)
assert SPEC and SPEC.loader
compress = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = compress
SPEC.loader.exec_module(compress)

TODAY = datetime.date(2026, 7, 6)


def tree_digest(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


CHANGELOG = (
    "# Журнал изменений\n\n"
    "## Unreleased\n\n- wip\n\n"
    "## v1.3.0 — 2026-03-03\n\n- третий релиз\n\n"
    "## v1.2.0 — 2026-02-02\n\n- второй релиз\n\n"
    "## v1.1.0 — 2026-01-01\n\n- первый релиз\n"
)

DEFECTS = (
    "# Дефекты\n\n"
    "## Open\n\n"
    "| # | Title | Discovered | Component | Description |\n"
    "|---|---|---|---|---|\n\n"
    "## Fixed\n\n"
    "Пояснение к разделу.\n\n"
    "| # | Title | Discovered | Fixed | Commit | Root Cause |\n"
    "|---|---|---|---|---|---|\n"
    "| 10 | Старый | 2025-01-01 | 2025-01-02 | `aaa` | old rc |\n"
    "| 11 | Свежий | 2026-06-01 | 2026-06-02 | `bbb` | recent rc |\n"
    "| 12 | Без даты | 2026-01-01 | pending | `ccc` | rc |\n\n"
    "## Won't Fix\n\n"
    "| # | Title | Discovered | Reason |\n"
    "|---|---|---|---|\n"
)

DEFECTS_ARCHIVE = (
    "# Архив дефектов\n\n"
    "## Fixed (архив)\n\n"
    "| # | Title | Discovered | Fixed | Commit | Root Cause |\n"
    "|---|---|---|---|---|---|\n"
    "| 1 | Первый | 2024-01-01 | 2024-01-02 | `zzz` | rc |\n"
)


class ChangelogTests(unittest.TestCase):
    def test_splits_oldest_versions(self):
        result = compress.split_changelog(CHANGELOG, None, max_bytes=150, target_bytes=120, keep=1)
        self.assertIsNotNone(result)
        new_cl, new_arc, moved = result
        self.assertEqual(moved, 2)
        self.assertIn("## Unreleased", new_cl)
        self.assertIn("## v1.3.0", new_cl)
        self.assertNotIn("## v1.2.0", new_cl)
        self.assertNotIn("## v1.1.0", new_cl)
        # Archive keeps newest-first order.
        self.assertLess(new_arc.index("v1.2.0"), new_arc.index("v1.1.0"))
        self.assertTrue(new_arc.startswith(compress.CHANGELOG_ARCHIVE_HEADER))

    def test_no_split_when_small(self):
        self.assertIsNone(
            compress.split_changelog(CHANGELOG, None, max_bytes=100_000, target_bytes=80_000, keep=1)
        )

    def test_no_split_when_keep_covers_all(self):
        self.assertIsNone(
            compress.split_changelog(CHANGELOG, None, max_bytes=10, target_bytes=5, keep=9)
        )

    def test_merges_into_existing_archive_newest_first(self):
        existing = compress.CHANGELOG_ARCHIVE_HEADER + "## v1.0.0 — 2025-12-31\n\n- старьё\n"
        new_cl, new_arc, _ = compress.split_changelog(
            CHANGELOG, existing, max_bytes=150, target_bytes=120, keep=1
        )
        self.assertLess(new_arc.index("v1.1.0"), new_arc.index("v1.0.0"))

    def test_split_reproduces_content(self):
        new_cl, new_arc, _ = compress.split_changelog(
            CHANGELOG, None, max_bytes=150, target_bytes=120, keep=1
        )
        combined = new_cl + "".join(
            b for b in compress.split_h2_blocks(new_arc)[1]
        )
        for marker in ("wip", "первый релиз", "второй релиз", "третий релиз"):
            self.assertIn(marker, new_cl + new_arc)


class DefectsTests(unittest.TestCase):
    def test_archives_only_aged_rows(self):
        result = compress.archive_fixed_defects(DEFECTS, DEFECTS_ARCHIVE, TODAY, max_age_days=90)
        self.assertIsNotNone(result)
        new_defects, new_archive, moved = result
        self.assertEqual(moved, 1)
        self.assertNotIn("Старый", new_defects)
        self.assertIn("Свежий", new_defects)
        self.assertIn("Без даты", new_defects)  # unparseable date is left in place
        self.assertIn("Старый", new_archive)
        self.assertLess(new_archive.index("Первый"), new_archive.index("Старый"))
        # Explanatory paragraph and Won't Fix section survive.
        self.assertIn("Пояснение к разделу.", new_defects)
        self.assertIn("## Won't Fix", new_defects)

    def test_no_archive_target_is_not_created(self):
        self.assertIsNone(compress.archive_fixed_defects(DEFECTS, None, TODAY, max_age_days=90))

    def test_nothing_to_archive(self):
        self.assertIsNone(
            compress.archive_fixed_defects(DEFECTS, DEFECTS_ARCHIVE, TODAY, max_age_days=10_000)
        )


class CruftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="compress-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_finds_and_removes_cruft(self):
        (self.root / "pkg" / "__pycache__").mkdir(parents=True)
        (self.root / "pkg" / "__pycache__" / "m.pyc").write_text("x", encoding="utf-8")
        (self.root / ".DS_Store").write_text("x", encoding="utf-8")
        (self.root / ".trash").mkdir()
        (self.root / "keep.md").write_text("keep", encoding="utf-8")
        (self.root / ".git" / "__pycache__").mkdir(parents=True)  # must be ignored

        found = compress.find_cruft(self.root)
        names = {p.relative_to(self.root).as_posix() for p in found}
        self.assertEqual(names, {"pkg/__pycache__", ".DS_Store", ".trash"})

        plan = compress.Plan(deletes=found)
        compress.apply_plan(plan)
        self.assertFalse((self.root / "pkg" / "__pycache__").exists())
        self.assertFalse((self.root / ".DS_Store").exists())
        self.assertFalse((self.root / ".trash").exists())
        self.assertTrue((self.root / "keep.md").exists())

    def test_nonempty_trash_is_kept(self):
        (self.root / ".trash").mkdir()
        (self.root / ".trash" / "note").write_text("x", encoding="utf-8")
        self.assertEqual(compress.find_cruft(self.root), [])


class StaleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="compress-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _write(self, rel: str, verified: str):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\ntype: doc\nlast_verified: {verified}\n---\n\n# X\n", encoding="utf-8")

    def test_flags_only_real_old_dates(self):
        self._write("old.md", "2020-01-01")
        self._write("fresh.md", "2026-07-01")
        self._write("placeholder.md", "<YYYY-MM-DD>")
        self._write("templates/new-project/t.md", "2020-01-01")

        notices = compress.stale_frontmatter(self.root, TODAY, stale_days=60)
        flagged = {n.path for n in notices}
        self.assertEqual(flagged, {"old.md"})


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="compress-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
        defects_dir = self.root / "docs" / "quality"
        defects_dir.mkdir(parents=True)
        (defects_dir / "DEFECTS.md").write_text(DEFECTS, encoding="utf-8")
        (defects_dir / "DEFECTS_ARCHIVE.md").write_text(DEFECTS_ARCHIVE, encoding="utf-8")
        (self.root / ".DS_Store").write_text("x", encoding="utf-8")

    def _config(self):
        return compress.Config(
            root=self.root, today=TODAY,
            changelog_max_bytes=150, changelog_target_bytes=120, changelog_keep=1,
            fixed_max_age_days=90, stale_days=60,
        )

    def test_planning_is_read_only(self):
        before = tree_digest(self.root)
        plan = compress.plan_compression(self._config())
        self.assertTrue(plan.actions)
        self.assertEqual(before, tree_digest(self.root))

    def test_apply_then_idempotent(self):
        plan = compress.plan_compression(self._config())
        compress.apply_plan(plan)
        # A second pass finds nothing left to do.
        again = compress.plan_compression(self._config())
        self.assertEqual(again.actions, [])
        self.assertEqual(again.writes, {})
        self.assertEqual(again.deletes, [])

    def test_main_report_exits_zero(self):
        rc = compress.main(["--root", str(self.root), "--today", "2026-07-06"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
