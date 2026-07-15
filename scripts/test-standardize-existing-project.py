#!/usr/bin/env python3
"""Regression tests for standardize_existing_project.py."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "standardize_existing_project.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("standardize_existing_project", MODULE_PATH)
assert SPEC and SPEC.loader
planner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = planner
SPEC.loader.exec_module(planner)


def make_symlink_or_skip(test: unittest.TestCase, link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        test.skipTest(f"symlinks are unavailable on this platform: {exc}")


def tree_digest(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(
        item for item in root.rglob("*")
        if item.is_file() and ".git" not in item.relative_to(root).parts
    ):
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class StandardizeExistingProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="standardize-existing-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.rows = planner.load_artifacts(ROOT)
        self.profiles = planner.profile_destinations(self.rows)

    def git_init(self, root: Path):
        subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Standardize Test"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "standardize@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "core.autocrlf", "false"], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "--allow-empty", "-m", "fixture"], check=True, capture_output=True)

    def git_commit_all(self, root: Path, message: str):
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-m", message], check=True, capture_output=True)

    def make_project(self, profile="minimal", git=True) -> Path:
        project = self.base / f"project-{profile}-{len(list(self.base.glob('project-*')))}"
        project.mkdir()
        for destination in self.profiles[profile]:
            if destination == ".project-standard.json":
                continue
            path = project / destination
            path.parent.mkdir(parents=True, exist_ok=True)
            if destination == "CLAUDE.md":
                path.write_text("@AGENTS.md\n", encoding="utf-8")
            elif path.suffix == ".md":
                path.write_text(f"# {path.stem}\n", encoding="utf-8")
            else:
                path.write_text("generated\n", encoding="utf-8")
        if git:
            self.git_init(project)
        return project

    def test_missing_adoption_journal_is_planned_and_created(self):
        project = self.make_project("minimal")
        (project / planner.ADOPTION_JOURNAL).unlink()
        self.git_commit_all(project, "drop adoption journal")
        report = planner.assess_project(project, ROOT, "auto", "auto")
        self.assertIn(planner.ADOPTION_JOURNAL, report.files_to_create)
        plan = planner.build_adopt_in_place_plan(project, ROOT, report)
        self.assertEqual(plan.status, "ready")
        planner.apply_plan(plan)
        journal = json.loads((project / planner.ADOPTION_JOURNAL).read_text(encoding="utf-8"))
        self.assertEqual(journal["schema_version"], 1)
        self.assertIsNone(journal["first_green_at"])
        self.assertEqual(journal["interventions"], [])

    def test_adoption_journal_starts_at_the_recorded_adoption_date(self):
        """A legacy project has no recoverable creation date, so the journal must start when the
        standard was adopted rather than inventing today's date."""
        project = self.make_project("minimal")
        (project / planner.ADOPTION_JOURNAL).unlink()
        (project / ".project-standard.json").write_text(json.dumps({
            "schema_version": 1, "profile": "minimal", "source": "NightMadMax/new-project-rules",
            "source_commit": "0" * 40, "created_at": None, "adopted_at": "2020-01-02",
            "applied_migrations": ["0001-adopt-project-standard"],
        }), encoding="utf-8")
        self.git_commit_all(project, "legacy metadata without journal")
        self.assertEqual(planner.adoption_date_for(project), "2020-01-02")
        report = planner.assess_project(project, ROOT, "auto", "auto")
        planner.apply_plan(planner.build_adopt_in_place_plan(project, ROOT, report))
        journal = json.loads((project / planner.ADOPTION_JOURNAL).read_text(encoding="utf-8"))
        self.assertEqual(journal["created_at"], "2020-01-02")

    def test_adoption_journal_falls_back_to_today_without_metadata(self):
        project = self.make_project("minimal")
        self.assertFalse((project / ".project-standard.json").exists())
        self.assertEqual(planner.adoption_date_for(project), date.today().isoformat())

    def test_adopt_is_recommended_for_clean_managed_project(self):
        project = self.make_project("software")
        before = tree_digest(project)
        report = planner.assess_project(project, ROOT, "auto", "auto")
        self.assertEqual(report.recommended_strategy, "adopt-in-place")
        self.assertEqual(report.candidate_profile, "software")
        self.assertTrue(report.safe_to_adopt_in_place)
        self.assertFalse(report.blocking_issues)
        self.assertEqual(before, tree_digest(project))

    def test_rules_repository_assessment_is_not_applicable_and_read_only(self):
        before = tree_digest(ROOT)
        report = planner.assess_project(ROOT, ROOT, "auto", "auto")
        self.assertEqual(report.target_kind, "rules-repository")
        self.assertEqual(report.status, "not_applicable")
        self.assertEqual(report.recommended_strategy, "not-applicable")
        self.assertIsNone(report.candidate_profile)
        self.assertFalse(report.safe_to_adopt_in_place)
        self.assertFalse(report.safe_to_rebootstrap)
        self.assertIn("not a consumer-project", "\n".join(report.blocking_issues))
        self.assertEqual(before, tree_digest(ROOT))

    def test_rules_repository_blocks_all_standardization_plans(self):
        report = planner.assess_project(ROOT, ROOT, "auto", "auto")
        adopt = planner.build_adopt_in_place_plan(ROOT, ROOT, report)
        rebuilt = planner.build_rebootstrap_plan(
            ROOT,
            ROOT,
            report,
            self.base / "should-not-exist",
            "Invalid Rules Copy",
        )
        self.assertEqual(adopt.status, "blocked")
        self.assertEqual(rebuilt.status, "blocked")
        self.assertEqual(adopt.profile, "unknown")
        self.assertEqual(rebuilt.profile, "unknown")
        self.assertIn("Rules repositories", "\n".join(adopt.blockers))
        self.assertIn("Rules repositories", "\n".join(rebuilt.blockers))

    def test_rules_repository_cli_json_reports_not_applicable(self):
        command = [sys.executable, str(MODULE_PATH), "--root", str(ROOT), "--json"]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["target_kind"], "rules-repository")
        self.assertEqual(payload["status"], "not_applicable")
        self.assertEqual(payload["recommended_strategy"], "not-applicable")

    def test_rules_repository_cli_plan_and_apply_are_blocked(self):
        commands = (
            ["--strategy", "adopt-in-place", "--plan-adopt"],
            [
                "--strategy", "re-bootstrap-from-existing",
                "--plan-rebootstrap",
                "--destination", str(self.base / "rebuilt-rules"),
                "--project-name", "Invalid Rules Copy",
            ],
            [
                "--strategy", "adopt-in-place",
                "--apply",
                "--fingerprint", "0" * 64,
                "--yes",
            ],
        )
        before = tree_digest(ROOT)
        for arguments in commands:
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--root", str(ROOT), *arguments],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1, (arguments, result.stdout, result.stderr))
            self.assertIn("Rules repositories", result.stdout)
        self.assertEqual(before, tree_digest(ROOT))

    def test_standard_version_alone_does_not_mark_consumer_as_rules_repository(self):
        project = self.make_project("minimal")
        (project / "STANDARD_VERSION").write_text("2\n", encoding="utf-8")
        self.git_commit_all(project, "add unrelated standard version file")
        report = planner.assess_project(project, ROOT, "auto", "auto")
        self.assertEqual(report.target_kind, "consumer-project")
        self.assertEqual(report.recommended_strategy, "adopt-in-place")

    def test_rebootstrap_is_recommended_for_non_repo_and_missing_core(self):
        project = self.base / "legacy-folder"
        project.mkdir()
        (project / "src").mkdir()
        (project / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
        report = planner.assess_project(project, ROOT, "auto", "auto")
        self.assertEqual(report.recommended_strategy, "re-bootstrap-from-existing")
        self.assertFalse(report.safe_to_adopt_in_place)
        self.assertIn("src", report.proposed_transfer_set)
        self.assertIn("Git repository root", "\n".join(report.blocking_issues))

    def test_conflicting_claude_and_nested_obsidian_block_in_place(self):
        project = self.make_project("minimal")
        (project / "CLAUDE.md").write_text("custom\n", encoding="utf-8")
        (project / ".obsidian").mkdir()
        report = planner.assess_project(project, ROOT, "adopt-in-place", "auto")
        self.assertEqual(report.status, "manual_review_required")
        self.assertFalse(report.safe_to_adopt_in_place)
        text = "\n".join(report.blocking_issues)
        self.assertIn("CLAUDE.md conflicts", text)
        self.assertIn("nested .obsidian", text)

    def test_cli_json_is_read_only(self):
        project = self.make_project("minimal")
        before = tree_digest(project)
        command = [sys.executable, str(MODULE_PATH), "--root", str(project), "--json"]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["recommended_strategy"], "adopt-in-place")
        self.assertEqual(before, tree_digest(project))

    def test_plan_and_apply_create_only_safe_files(self):
        project = self.make_project("software")
        (project / "CLAUDE.md").unlink()
        (project / "docs" / "README.md").unlink()
        self.git_commit_all(project, "remove managed files")
        before = tree_digest(project)
        plan_command = [
            sys.executable, str(MODULE_PATH),
            "--root", str(project),
            "--strategy", "adopt-in-place",
            "--profile", "software",
            "--plan-adopt",
        ]
        planned = subprocess.run(plan_command, capture_output=True, text=True)
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertIn("CLAUDE.md", planned.stdout)
        self.assertIn("docs/README.md", planned.stdout)
        fingerprint = next(
            line.split("=", 1)[1].strip()
            for line in planned.stdout.splitlines()
            if line.startswith("fingerprint=")
        )
        self.assertEqual(before, tree_digest(project))
        apply_command = plan_command[:-1] + ["--apply", "--fingerprint", fingerprint, "--yes"]
        applied = subprocess.run(apply_command, capture_output=True, text=True)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual((project / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")
        self.assertTrue((project / "docs" / "README.md").exists())
        index_text = (project / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("[[docs/README|docs/README.md]]", index_text)

    def test_apply_rejects_fingerprint_mismatch(self):
        project = self.make_project("software")
        (project / "CLAUDE.md").unlink()
        command = [
            sys.executable, str(MODULE_PATH),
            "--root", str(project),
            "--strategy", "adopt-in-place",
            "--apply",
            "--fingerprint", "0" * 64,
            "--yes",
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse((project / "CLAUDE.md").exists())

    def test_rebootstrap_plan_and_apply_copy_safe_transfer_set(self):
        project = self.base / "legacy-rebootstrap"
        project.mkdir()
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
        (project / "package.json").write_text('{"name":"legacy"}\n', encoding="utf-8")
        (project / "docs").mkdir()
        (project / "docs" / "README.md").write_text("# Legacy docs\n", encoding="utf-8")
        self.git_init(project)
        destination = self.base / "rebuilt"
        plan = subprocess.run([
            sys.executable, str(MODULE_PATH),
            "--root", str(project),
            "--strategy", "re-bootstrap-from-existing",
            "--plan-rebootstrap",
            "--destination", str(destination),
            "--project-name", "Rebuilt Project",
            "--profile", "software",
        ], capture_output=True, text=True)
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertIn("destination=", plan.stdout)
        fingerprint = next(
            line.split("=", 1)[1].strip()
            for line in plan.stdout.splitlines()
            if line.startswith("fingerprint=")
        )
        apply = subprocess.run([
            sys.executable, str(MODULE_PATH),
            "--root", str(project),
            "--strategy", "re-bootstrap-from-existing",
            "--apply",
            "--destination", str(destination),
            "--project-name", "Rebuilt Project",
            "--profile", "software",
            "--fingerprint", fingerprint,
            "--yes",
        ], capture_output=True, text=True)
        self.assertEqual(apply.returncode, 0, apply.stderr)
        self.assertTrue((destination / "src" / "main.py").exists())
        self.assertTrue((destination / "package.json").exists())
        self.assertFalse((destination / "docs" / "README.md").read_text(encoding="utf-8").startswith("# Legacy"))
        self.assertIn("NEXT METADATA PLAN:", apply.stdout)

    def test_adopt_plan_blocks_symlink_write_target(self):
        outside = self.base / "outside-target.md"
        outside.write_text("external\n", encoding="utf-8")
        project = self.make_project("software")
        (project / "INDEX.md").unlink()
        make_symlink_or_skip(self, project / "INDEX.md", outside)
        (project / "CLAUDE.md").unlink()
        self.git_commit_all(project, "symlink index")
        before_outside = outside.read_text(encoding="utf-8")
        report = planner.assess_project(project, ROOT, "adopt-in-place", "software")
        plan = planner.build_adopt_in_place_plan(project, ROOT, report)
        self.assertEqual(plan.status, "blocked")
        self.assertIn("symlink", "\n".join(plan.blockers))
        with self.assertRaises(planner.StandardizationApplyError):
            planner.apply_plan(plan)
        self.assertEqual(outside.read_text(encoding="utf-8"), before_outside)

    def test_rebootstrap_blocks_symlink_in_transfer_set(self):
        outside = self.base / "linked-secret.txt"
        outside.write_text("secret\n", encoding="utf-8")
        project = self.base / "legacy-symlink"
        project.mkdir()
        (project / "src").mkdir()
        (project / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
        make_symlink_or_skip(self, project / "src" / "linked-secret.txt", outside)
        self.git_init(project)
        destination = self.base / "rebuilt-from-symlink"
        report = planner.assess_project(project, ROOT, "re-bootstrap-from-existing", "software")
        plan = planner.build_rebootstrap_plan(project, ROOT, report, destination, "Rebuilt")
        self.assertEqual(plan.status, "blocked")
        self.assertIn("symlink", "\n".join(plan.blockers))
        with self.assertRaises(planner.StandardizationApplyError):
            planner.copy_transfer_item(project, destination, "src")
        self.assertFalse((destination / "src" / "linked-secret.txt").exists())

    def test_rebootstrap_fingerprint_covers_transfer_content(self):
        project = self.base / "legacy-fingerprint"
        project.mkdir()
        (project / "src").mkdir()
        (project / "src" / "app.txt").write_text("original\n", encoding="utf-8")
        self.git_init(project)
        destination = self.base / "rebuilt-fingerprint"

        def make_plan():
            report = planner.assess_project(project, ROOT, "re-bootstrap-from-existing", "software")
            return planner.build_rebootstrap_plan(project, ROOT, report, destination, "Rebuilt")

        first = make_plan()
        self.assertEqual(first.status, "ready")
        (project / "src" / "app.txt").write_text("tampered\n", encoding="utf-8")
        second = make_plan()
        self.assertEqual(second.status, "ready")
        self.assertNotEqual(first.fingerprint, second.fingerprint)

    def test_rebootstrap_blocks_destination_inside_source_root(self):
        project = self.base / "legacy-nested-destination"
        project.mkdir()
        (project / "src").mkdir()
        (project / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
        self.git_init(project)
        report = planner.assess_project(project, ROOT, "re-bootstrap-from-existing", "software")
        for destination in (project / "src" / "new-project", project / ".git" / "nested-project"):
            plan = planner.build_rebootstrap_plan(project, ROOT, report, destination, "Rebuilt")
            self.assertEqual(plan.status, "blocked", destination)
            self.assertIn("outside the legacy project root", "\n".join(plan.blockers))

    @unittest.skipIf(os.name == "nt", "POSIX wrapper is exercised on macOS/Linux only")
    def test_wrapper_reports_python_requirement_for_missing_runtime(self):
        env = os.environ.copy()
        env["PATH"] = str(self.base / "empty-path")
        (self.base / "empty-path").mkdir()
        command = ["/bin/sh", str(ROOT / "scripts" / "standardize-existing-project.sh"), "--root", str(self.base)]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Python 3.9+", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
