#!/usr/bin/env python3
"""Regression tests for read-only global policy sync inspection."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "sync_global_agents.py"
SPEC = importlib.util.spec_from_file_location("sync_global_agents", MODULE_PATH)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync
SPEC.loader.exec_module(sync)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AgentSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="agent-sync-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.portable = self.root / "GLOBAL_AGENT_INSTRUCTIONS.md"
        self.active = self.root / "home" / ".codex" / "AGENTS.md"
        self.portable.write_text("# Global rules\n\n- Shared rule.\n", encoding="utf-8")
        self.schema = 1

    def inspect(self):
        return sync.inspect_sync_state(self.portable, self.active, self.schema)

    def write_active(self, text: str, newline=None):
        self.active.parent.mkdir(parents=True, exist_ok=True)
        with self.active.open("w", encoding="utf-8", newline=newline) as handle:
            handle.write(text)

    def test_missing(self):
        state = self.inspect()
        self.assertEqual(state.status, "missing")
        self.assertIn("create managed block", sync.secret_safe_diff(state))

    def test_legacy_exact(self):
        self.write_active(self.portable.read_text(encoding="utf-8"), newline="\r\n")
        state = self.inspect()
        self.assertEqual(state.status, "legacy_exact")
        self.assertIn("wrap", sync.secret_safe_diff(state))

    def test_unmanaged_conflict_redacts_content(self):
        secret = "github_pat_SUPER_SECRET_VALUE_123456789"
        self.write_active(f"# Local\n{secret}\n")
        state = self.inspect()
        report = sync.secret_safe_diff(state)
        self.assertEqual(state.status, "unmanaged_conflict")
        self.assertNotIn(secret, report)
        self.assertIn("sha256=", report)

    def test_unmanaged_conflict_desired_text_appends_below_existing(self):
        existing = "# Local rules\n\n- Keep me.\n"
        self.write_active(existing)
        state = self.inspect()
        self.assertEqual(state.status, "unmanaged_conflict")
        desired = sync.desired_text(state)
        assert desired is not None
        self.assertTrue(desired.startswith(sync.normalize(existing)))
        self.assertIn(sync.managed_block(self.portable.read_text(encoding="utf-8"), self.schema), desired)
        self.write_active(desired)
        self.assertEqual(self.inspect().status, "managed_match")

    def test_managed_match_preserves_outside_text(self):
        prefix = "# Local prefix\r\n\r\n"
        suffix = "\r\n# Local suffix\r\n"
        block = sync.managed_block(self.portable.read_text(encoding="utf-8"), self.schema)
        self.write_active(prefix + block + suffix, newline="")
        state = self.inspect()
        self.assertEqual(state.status, "managed_match")
        desired = sync.desired_text(state)
        assert desired is not None
        self.assertTrue(desired.startswith(prefix))
        self.assertTrue(desired.endswith(suffix))

    def test_managed_drift_diff_is_secret_safe(self):
        secret = "gh" + "p_" + "X" * 30
        begin = sync.BEGIN_TEMPLATE.format(schema=self.schema)
        self.write_active(f"{begin}\n# Changed\n{secret}\n{sync.END_MARKER}\n")
        state = self.inspect()
        report = sync.secret_safe_diff(state)
        self.assertEqual(state.status, "managed_drift")
        self.assertNotIn(secret, report)
        self.assertIn("Changed ranges (content redacted)", report)

    def test_older_managed_schema_is_upgradeable_and_secret_safe(self):
        secret = "gh" + "p_" + "X" * 30
        block = sync.managed_block(f"# Old\n{secret}\n", self.schema)
        self.write_active(block)
        state = sync.inspect_state(self.portable.read_text(encoding="utf-8"), self.active, self.schema + 1)
        self.assertEqual(state.status, "managed_upgrade")
        self.assertEqual(state.managed_schema, self.schema)
        report = sync.secret_safe_diff(state)
        self.assertNotIn(secret, report)
        desired = sync.desired_text(state)
        assert desired is not None
        self.assertIn(f"schema={self.schema + 1}", desired)

    def test_malformed_and_unsupported_markers(self):
        self.write_active(f"{sync.END_MARKER}\n{sync.BEGIN_TEMPLATE.format(schema=1)}\n")
        self.assertEqual(self.inspect().status, "malformed")
        self.write_active(f"{sync.BEGIN_TEMPLATE.format(schema=2)}\ntext\n{sync.END_MARKER}\n")
        self.assertEqual(self.inspect().status, "unsupported_schema")

    def test_extract_managed_region(self):
        block = sync.managed_block("- A rule.\n", 1)
        text = "# Head\n\n## Local\n- local\n\n" + block
        self.assertEqual(sync.extract_managed_region(text), sync.normalize("- A rule.\n"))
        self.assertIsNone(sync.extract_managed_region("# No markers here\n"))

    def test_inspect_state_text_match_and_drift(self):
        baseline = "- A rule.\n"
        prefix = "## Local\n- local rule\n\n"
        self.write_active(prefix + sync.managed_block(baseline, 1))
        self.assertEqual(sync.inspect_state(baseline, self.active, 1).status, "managed_match")
        self.write_active(prefix + sync.managed_block("- Changed rule.\n", 1))
        self.assertEqual(sync.inspect_state(baseline, self.active, 1).status, "managed_drift")
        self.write_active(prefix + "- unmarked baseline\n")
        self.assertEqual(sync.inspect_state(baseline, self.active, 1).status, "unmanaged_conflict")

    def test_cli_exit_codes_and_no_mutation(self):
        contract = self.root / "contract"
        contract.mkdir()
        (contract / "STANDARD_VERSION").write_text("1\n", encoding="utf-8")
        (contract / "GLOBAL_AGENT_INSTRUCTIONS.md").write_text(self.portable.read_text(encoding="utf-8"), encoding="utf-8")
        home = self.root / "home"
        before = file_hash(self.active) if self.active.exists() else None
        base = [sys.executable, str(MODULE_PATH), "--contract-root", str(contract), "--home", str(home)]
        self.assertEqual(subprocess.run(base + ["--check"], capture_output=True).returncode, 1)
        self.assertEqual(subprocess.run(base + ["--diff", "--report-only"], capture_output=True).returncode, 0)
        after = file_hash(self.active) if self.active.exists() else None
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
