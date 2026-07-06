#!/usr/bin/env python3
"""Regression tests for the read-only migration planner."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "plan_migration.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("plan_migration", MODULE_PATH)
assert SPEC and SPEC.loader
planner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = planner
SPEC.loader.exec_module(planner)


def digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file() and ".git" not in item.parts):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class MigrationPlannerTests(unittest.TestCase):
    def setUp(self):
        if not shutil.which("git"):
            self.skipTest("git is required")
        self.temp = tempfile.TemporaryDirectory(prefix="migration-planner-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.contract = self.base / "contract"
        (self.contract / "config").mkdir(parents=True)
        for name in ("profiles.tsv", "migrations.tsv", "standard-source.txt"):
            shutil.copy2(ROOT / "config" / name, self.contract / "config" / name)
        shutil.copy2(ROOT / "STANDARD_VERSION", self.contract / "STANDARD_VERSION")
        shutil.copy2(ROOT / "GLOBAL_AGENT_INSTRUCTIONS.md", self.contract / "GLOBAL_AGENT_INSTRUCTIONS.md")
        self.git_init(self.contract)
        self.version = planner.read_standard_version(self.contract)
        self.migrations = planner.read_migrations(self.contract, self.version)
        self.profiles = planner.read_profile_destinations(self.contract)

    def git_init(self, root: Path):
        subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Migration Test"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "migration@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "core.autocrlf", "false"], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "--allow-empty", "-m", "fixture"], check=True, capture_output=True)

    def make_project(self, profile="minimal", commit=True) -> Path:
        project = self.base / f"project-{profile}-{len(list(self.base.glob('project-*')))}"
        project.mkdir()
        for destination in self.profiles[profile]:
            path = project / destination
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"fixture {destination}\n", encoding="utf-8")
        self.git_init(project)
        if not commit:
            (project / "README.md").write_text("dirty\n", encoding="utf-8")
        return project

    def test_manifest_contract(self):
        self.assertEqual({row.migration_id for row in self.migrations}, {
            "0001-adopt-project-standard", "0002-adopt-global-managed-block"
        })
        path = self.contract / "config" / "migrations.tsv"
        path.write_text(path.read_text(encoding="utf-8") + path.read_text(encoding="utf-8").splitlines()[1] + "\n", encoding="utf-8")
        with self.assertRaises(planner.MigrationConfigError):
            planner.read_migrations(self.contract, self.version)

    def test_project_plan_is_reviewable_and_read_only(self):
        project = self.make_project("software")
        before = digest_tree(project)
        plan = planner.project_plan(project, self.contract, "auto", self.migrations, self.version)
        self.assertEqual(plan.status, "ready")
        self.assertEqual(plan.migration_id, "0001-adopt-project-standard")
        self.assertRegex(plan.fingerprint, r"^[0-9a-f]{64}$")
        metadata = json.loads(plan.preview)
        self.assertEqual(metadata["profile"], "software")
        self.assertIsNone(metadata["created_at"])
        self.assertRegex(metadata["source_commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(planner.format_plan(plan), planner.format_plan(
            planner.project_plan(project, self.contract, "auto", self.migrations, self.version)
        ))
        self.assertEqual(before, digest_tree(project))
        self.assertFalse((project / ".project-standard.json").exists())

    def test_project_apply_is_atomic_reviewable_and_idempotent(self):
        project = self.make_project("minimal")
        plan = planner.project_plan(project, self.contract, "auto", self.migrations, self.version)
        result = planner.apply_plan(plan)
        metadata_path = project / ".project-standard.json"
        self.assertTrue(result.changed)
        self.assertTrue(metadata_path.is_file())
        status = subprocess.run(["git", "-C", str(project), "status", "--porcelain"], capture_output=True, text=True)
        self.assertIn(".project-standard.json", status.stdout)
        repeated = planner.project_plan(project, self.contract, "auto", self.migrations, self.version)
        self.assertEqual(repeated.status, "up_to_date")
        self.assertFalse(planner.apply_plan(repeated).changed)

    def test_project_plan_blocks_ambiguous_and_dirty_state(self):
        ambiguous = self.base / "ambiguous"
        ambiguous.mkdir()
        self.git_init(ambiguous)
        plan = planner.project_plan(ambiguous, self.contract, "auto", self.migrations, self.version)
        self.assertEqual(plan.status, "blocked")
        self.assertIn("Cannot infer", "\n".join(plan.blockers))
        dirty = self.make_project("minimal", commit=False)
        plan = planner.project_plan(dirty, self.contract, "auto", self.migrations, self.version)
        self.assertEqual(plan.status, "blocked")
        self.assertIn("not clean", "\n".join(plan.blockers))

    def test_project_metadata_symlink_is_blocked(self):
        project = self.make_project("minimal")
        with mock.patch.object(planner.Path, "is_symlink", return_value=True):
            plan = planner.project_plan(project, self.contract, "auto", self.migrations, self.version)
        self.assertEqual(plan.status, "blocked")
        self.assertIn("symlink", "\n".join(plan.blockers))

    def test_current_metadata_is_up_to_date(self):
        project = self.make_project("minimal")
        commit = planner.inspect_git(self.contract).commit
        assert commit is not None
        metadata = planner.project_metadata.build_legacy_metadata(
            1, "minimal", "NightMadMax/new-project-rules", commit, "0001-adopt-project-standard"
        )
        (project / ".project-standard.json").write_text(json.dumps(metadata), encoding="utf-8")
        plan = planner.project_plan(project, self.contract, "auto", self.migrations, self.version)
        self.assertEqual(plan.status, "up_to_date")

    def test_incomplete_current_metadata_is_blocked(self):
        project = self.make_project("minimal")
        (project / ".project-standard.json").write_text('{"schema_version": 1, "profile": "minimal"}\n', encoding="utf-8")
        plan = planner.project_plan(project, self.contract, "auto", self.migrations, self.version)
        self.assertEqual(plan.status, "blocked")
        self.assertIn("source", "\n".join(plan.blockers))

    def test_global_legacy_plan_is_secret_safe_and_read_only(self):
        home = self.base / "home"
        active = home / ".codex" / "AGENTS.md"
        active.parent.mkdir(parents=True)
        shutil.copy2(self.contract / "GLOBAL_AGENT_INSTRUCTIONS.md", active)
        before = active.read_bytes()
        plan = planner.global_plan(home, self.contract, self.migrations, self.version)
        report = planner.format_plan(plan)
        self.assertEqual(plan.status, "ready")
        self.assertIn("timestamped backup", report)
        self.assertIn("sha256=", report)
        self.assertEqual(before, active.read_bytes())

    def test_global_apply_creates_exact_backup_and_is_idempotent(self):
        home = self.base / "apply-home"
        active = home / ".codex" / "AGENTS.md"
        active.parent.mkdir(parents=True)
        shutil.copy2(self.contract / "GLOBAL_AGENT_INSTRUCTIONS.md", active)
        before = active.read_bytes()
        plan = planner.global_plan(home, self.contract, self.migrations, self.version)
        result = planner.apply_plan(plan)
        self.assertTrue(result.changed)
        self.assertIsNotNone(result.backup)
        assert result.backup is not None
        self.assertEqual(result.backup.read_bytes(), before)
        state = planner.agent_sync.inspect_sync_state(
            self.contract / "GLOBAL_AGENT_INSTRUCTIONS.md", active, self.version
        )
        self.assertEqual(state.status, "managed_match")
        repeated = planner.global_plan(home, self.contract, self.migrations, self.version)
        self.assertEqual(repeated.status, "up_to_date")
        self.assertFalse(planner.apply_plan(repeated).changed)

    def test_apply_rejects_stale_preimage_and_cleans_interrupted_temp(self):
        project = self.make_project("minimal")
        plan = planner.project_plan(project, self.contract, "auto", self.migrations, self.version)
        assert plan.destination is not None
        readme = project / "README.md"
        original_readme = readme.read_text(encoding="utf-8")
        readme.write_text("concurrent project change\n", encoding="utf-8")
        with self.assertRaises(planner.MigrationApplyError):
            planner.apply_plan(plan)
        readme.write_text(original_readme, encoding="utf-8")
        plan.destination.write_text("concurrent\n", encoding="utf-8")
        with self.assertRaises(planner.MigrationApplyError):
            planner.apply_plan(plan)
        plan.destination.unlink()
        fresh = planner.project_plan(project, self.contract, "auto", self.migrations, self.version)
        with mock.patch.object(planner.os, "replace", side_effect=OSError("interrupted")):
            with self.assertRaises(planner.MigrationApplyError):
                planner.apply_plan(fresh)
        self.assertFalse(plan.destination.exists())
        self.assertEqual(list(project.glob("..project-standard.json.tmp.*")), [])

    def test_global_conflict_plan_appends_and_redacts_active_content(self):
        home = self.base / "conflict-home"
        active = home / ".codex" / "AGENTS.md"
        active.parent.mkdir(parents=True)
        secret = "github_pat_" + "S" * 30
        active.write_text(secret + "\n", encoding="utf-8")
        before = active.read_bytes()
        plan = planner.global_plan(home, self.contract, self.migrations, self.version)
        report = planner.format_plan(plan)
        self.assertEqual(plan.status, "ready")
        self.assertTrue(plan.backup_required)
        self.assertIn("append", report)
        self.assertNotIn(secret, report)
        self.assertEqual(before, active.read_bytes())

    def test_global_conflict_apply_preserves_existing_content_and_backs_up(self):
        home = self.base / "conflict-apply-home"
        active = home / ".codex" / "AGENTS.md"
        active.parent.mkdir(parents=True)
        personal = "# My personal global rules\n\n- Keep this untouched.\n"
        active.write_text(personal, encoding="utf-8")
        before = active.read_bytes()
        plan = planner.global_plan(home, self.contract, self.migrations, self.version)
        result = planner.apply_plan(plan)
        self.assertTrue(result.changed)
        self.assertIsNotNone(result.backup)
        assert result.backup is not None
        self.assertEqual(result.backup.read_bytes(), before)
        updated = active.read_text(encoding="utf-8")
        self.assertTrue(updated.startswith(personal))
        state = planner.agent_sync.inspect_sync_state(
            self.contract / "GLOBAL_AGENT_INSTRUCTIONS.md", active, self.version
        )
        self.assertEqual(state.status, "managed_match")
        repeated = planner.global_plan(home, self.contract, self.migrations, self.version)
        self.assertEqual(repeated.status, "up_to_date")
        self.assertFalse(planner.apply_plan(repeated).changed)

    def test_global_symlink_destination_is_blocked(self):
        home = self.base / "symlink-home"
        active = home / ".codex" / "AGENTS.md"
        active.parent.mkdir(parents=True)
        shutil.copy2(self.contract / "GLOBAL_AGENT_INSTRUCTIONS.md", active)
        with mock.patch.object(planner.Path, "is_symlink", return_value=True):
            plan = planner.global_plan(home, self.contract, self.migrations, self.version)
        self.assertEqual(plan.status, "blocked")
        self.assertIn("symlink", "\n".join(plan.blockers))

    def test_cli_exit_codes_and_no_mutation(self):
        project = self.make_project("minimal")
        before = digest_tree(project)
        base = [sys.executable, str(MODULE_PATH), "--plan", "--target", "project", "--root", str(project), "--contract-root", str(self.contract)]
        result = subprocess.run(base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No files were changed.", result.stdout)
        self.assertEqual(before, digest_tree(project))
        plan = planner.project_plan(project, self.contract, "auto", self.migrations, self.version)
        apply_base = [
            sys.executable, str(MODULE_PATH), "--apply", "--target", "project",
            "--root", str(project), "--contract-root", str(self.contract),
            "--fingerprint", plan.fingerprint,
        ]
        self.assertEqual(subprocess.run(apply_base, capture_output=True).returncode, 2)
        applied = subprocess.run(apply_base + ["--yes"], capture_output=True, text=True)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertTrue((project / ".project-standard.json").is_file())
        self.assertEqual(subprocess.run(apply_base + ["--yes"], capture_output=True).returncode, 0)

    def test_cli_rejects_fingerprint_mismatch(self):
        project = self.make_project("minimal")
        command = [
            sys.executable, str(MODULE_PATH), "--apply", "--target", "project",
            "--root", str(project), "--contract-root", str(self.contract),
            "--fingerprint", "0" * 64, "--yes",
        ]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        self.assertFalse((project / ".project-standard.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
