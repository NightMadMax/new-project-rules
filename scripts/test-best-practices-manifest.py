#!/usr/bin/env python3
"""Regression tests for the schema-2 Best Practices consumer writer."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "best_practices_manifest.py"
SPEC = importlib.util.spec_from_file_location("best_practices_manifest", MODULE_PATH)
manifest_writer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(manifest_writer)


class BestPracticesManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "consumer"
        self.project.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    @property
    def path(self):
        return self.project / ".best-practices.json"

    def read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_new_decline_writes_schema2_global_optout(self):
        manifest_writer.update_preference(self.project, global_value="optout", section=None, section_value=None)
        self.assertEqual({
            "schema_version": 2,
            "preferences": {"global": "optout", "sections": {}},
            "practices": {},
        }, self.read())

    def test_section_preference_preserves_practice_outcomes(self):
        decision = {"outcome": "applied", "source_commit": "a" * 40}
        self.path.write_text(json.dumps({
            "schema_version": 2,
            "preferences": {"global": "ask", "sections": {}},
            "practices": {"PC-2026-001": decision},
        }), encoding="utf-8")
        manifest_writer.update_preference(
            self.project, global_value=None, section="web", section_value="optout",
        )
        self.assertEqual("optout", self.read()["preferences"]["sections"]["web"])
        self.assertEqual(decision, self.read()["practices"]["PC-2026-001"])

    def test_schema1_requires_explicit_migration(self):
        before = b'{"schema_version": 1, "optout": true}\n'
        self.path.write_bytes(before)
        with self.assertRaisesRegex(ValueError, "migrate it first"):
            manifest_writer.update_preference(self.project, global_value="ask", section=None, section_value=None)
        self.assertEqual(before, self.path.read_bytes())

    def test_symlink_is_blocked(self):
        outside = Path(self.temp.name) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        try:
            self.path.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, "symlink"):
            manifest_writer.update_preference(self.project, global_value="ask", section=None, section_value=None)
        self.assertEqual("{}\n", outside.read_text(encoding="utf-8"))

    def test_cli_rejects_invalid_section_preference_without_write(self):
        result = subprocess.run([
            sys.executable, str(MODULE_PATH), "--project", str(self.project),
            "--set-section", "python", "invalid",
        ], capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertFalse(self.path.exists())

    def test_writer_rejects_well_formed_but_unknown_section(self):
        with self.assertRaisesRegex(ValueError, "unsupported Best Practices section"):
            manifest_writer.update_preference(
                self.project, global_value=None, section="unknown", section_value="ask",
            )
        self.assertFalse(self.path.exists())

    def test_cli_stack_records_selected_stacks(self):
        result = subprocess.run([
            sys.executable, str(MODULE_PATH), "--project", str(self.project),
            "--stack", "web", "--stack", "backend",
        ], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            {"web": "ask", "backend": "ask"},
            self.read()["preferences"]["sections"],
        )

    def test_cli_stack_rejects_unknown_stack_without_write(self):
        result = subprocess.run([
            sys.executable, str(MODULE_PATH), "--project", str(self.project),
            "--stack", "nope",
        ], capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertFalse(self.path.exists())

    def test_cli_requires_an_action(self):
        result = subprocess.run([
            sys.executable, str(MODULE_PATH), "--project", str(self.project),
        ], capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
