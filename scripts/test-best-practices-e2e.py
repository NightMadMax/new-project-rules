#!/usr/bin/env python3
"""Cross-repository E2E tests for the NPR/BP consumer manifest contract."""

from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConsumerManifestE2E(unittest.TestCase):
    bp_root: Path

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(cls.bp_root / "scripts"))
        cls.writer = load_module("npr_consumer_writer", ROOT / "scripts" / "best_practices_manifest.py")
        cls.report = load_module("bp_practice_report", cls.bp_root / "scripts" / "practice_report.py")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(cls.bp_root / "scripts"))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "consumer"
        self.project.mkdir()
        self.manifest = self.project / ".best-practices.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_npr_global_optout_is_enforced_by_bp(self):
        self.writer.update_preference(
            self.project, global_value="optout", section=None, section_value=None,
        )
        manifest = self.report.load_manifest(self.manifest)
        practices = self.report.load_practices(self.bp_root, {"common"})
        self.assertEqual([], self.report.apply_preferences(practices, manifest))

    def test_npr_section_optout_is_enforced_by_bp(self):
        self.writer.update_preference(
            self.project, global_value=None, section="common", section_value="optout",
        )
        manifest = self.report.load_manifest(self.manifest)
        practices = self.report.load_practices(self.bp_root, {"common"})
        self.assertTrue(practices)
        self.assertEqual([], self.report.apply_preferences(practices, manifest))

    def test_bp_outcome_survives_npr_preference_update(self):
        self.writer.update_preference(
            self.project, global_value="ask", section=None, section_value=None,
        )
        practice = self.report.load_practices(self.bp_root, {"common"})[0]
        source_commit = self.report.current_commit(self.bp_root)
        self.report.record_outcome(
            self.manifest, practice, "applied", source_commit, "cross-repo fixture",
        )
        self.writer.update_preference(
            self.project, global_value=None, section="tools", section_value="optout",
        )
        manifest = self.report.load_manifest(self.manifest)
        self.assertEqual("applied", manifest["practices"][practice["id"]]["outcome"])
        self.assertEqual(source_commit, manifest["practices"][practice["id"]]["source_commit"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--best-practices-root", required=True, type=Path)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.best_practices_root.resolve()
    if not (root / "scripts" / "practice_report.py").is_file():
        print(f"Best Practices checkout is incomplete: {root}", file=sys.stderr)
        return 2
    ConsumerManifestE2E.bp_root = root
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ConsumerManifestE2E)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
