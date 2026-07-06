#!/usr/bin/env python3
"""Regression tests for promotion candidate storage and ID generation."""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import promotion_candidates as candidates


ROOT = Path(__file__).resolve().parents[1]


class PromotionCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="promotion-candidates-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs" / "quality" / "promotion-candidates").mkdir(parents=True)

    def args(self, slug="safe-storage"):
        return argparse.Namespace(
            slug=slug, title="Safe storage", source="source/project", observation="Observed",
            generalized_lesson="Generalized", scope="Repositories", evidence="defect #1",
            artifact_type="validator", proposed_target="scripts/validate-project.py",
            year=2026, created="2026-07-06",
        )

    def test_repository_candidates_are_valid(self):
        self.assertEqual(candidates.validate_candidates(ROOT), [])

    def test_generator_uses_collision_resistant_id(self):
        with mock.patch("promotion_candidates.secrets.token_hex", return_value="abcdef123456"):
            path = candidates.create_candidate(self.root, self.args())
        self.assertEqual(path.name, "PC-2026-abcdef123456-safe-storage.md")
        self.assertEqual(candidates.validate_candidates(self.root), [])

    def test_generator_retries_local_collision(self):
        values = iter(("abcdef123456", "fedcba654321"))
        with mock.patch("promotion_candidates.secrets.token_hex", side_effect=lambda _: next(values)):
            candidates.create_candidate(self.root, self.args("first"))
            second = candidates.create_candidate(self.root, self.args("second"))
        self.assertTrue(second.name.startswith("PC-2026-fedcba654321-"))

    def test_validator_rejects_duplicate_id(self):
        with mock.patch("promotion_candidates.secrets.token_hex", return_value="abcdef123456"):
            first = candidates.create_candidate(self.root, self.args("first"))
        second = first.with_name("PC-2026-abcdef123456-second.md")
        second.write_text(first.read_text(encoding="utf-8"), encoding="utf-8")
        issues = candidates.validate_candidates(self.root)
        self.assertTrue(any("duplicate candidate id" in message for _, message in issues), issues)

    def test_legacy_sequential_id_remains_valid(self):
        path = self.root / "docs" / "quality" / "promotion-candidates" / "PC-2026-001-legacy.md"
        path.write_text('''---
type: promotion-candidate
id: PC-2026-001
status: implemented
source: "legacy"
observation: "Observed"
generalized_lesson: "Lesson"
scope: "Scope"
evidence: "Evidence"
artifact_type: test
proposed_target: "scripts/test.py"
created: 2026-06-30
last_verified: 2026-07-06
implemented_commit: abc1234
---
''', encoding="utf-8")
        self.assertEqual(candidates.validate_candidates(self.root), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
