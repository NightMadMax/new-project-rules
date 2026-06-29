#!/usr/bin/env python3
"""Regression tests for the read-only project validator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_PATH = ROOT / "scripts" / "validate-project.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("project_validator", VALIDATOR_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


def finding_codes(findings):
    return {finding.code for finding in findings}


def tree_digest(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="validator-test-")
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)
        self.rows = validator.load_artifacts(ROOT)

    def make_project(self, profile="minimal") -> Path:
        project = self.temp_path / f"project-{profile}"
        selected = validator.artifacts_for_profile(self.rows, profile)
        for artifact in selected:
            path = project / artifact.destination
            path.parent.mkdir(parents=True, exist_ok=True)
            if artifact.destination == "CLAUDE.md":
                path.write_text("@AGENTS.md\n", encoding="utf-8")
            elif artifact.destination == "INDEX.md":
                links = [f"- [[{item.destination.removesuffix('.md')}]]" for item in selected if item.root_purpose != "-"]
                path.write_text("# Index\n\n" + "\n".join(links) + "\n", encoding="utf-8")
            elif artifact.destination == "docs/README.md":
                links = [f"- [[{item.destination.removesuffix('.md')}]]" for item in selected if item.docs_section != "-"]
                path.write_text("# Documentation\n\n" + "\n".join(links) + "\n", encoding="utf-8")
            elif path.suffix == ".md":
                path.write_text(f"# {path.stem}\n", encoding="utf-8")
            else:
                path.write_text("generated\n", encoding="utf-8")
        return project

    def validate_project(self, project: Path, profile="auto", doctor=False):
        return validator.validate(project, ROOT, "project", profile, doctor)

    def test_rules_repository_is_valid(self):
        _, _, findings = validator.validate(ROOT, ROOT, "rules", "auto")
        self.assertFalse([item for item in findings if item.severity == "ERROR"], findings)

    def test_valid_legacy_project_infers_profile_without_mutation(self):
        project = self.make_project("software")
        before = tree_digest(project)
        kind, profile, findings = self.validate_project(project)
        self.assertEqual((kind, profile), ("project", "software"))
        self.assertIn("metadata.missing", finding_codes(findings))
        self.assertFalse([item for item in findings if item.severity == "ERROR"], findings)
        self.assertEqual(before, tree_digest(project))

    def test_real_bootstrap_output_passes_validator(self):
        project = self.temp_path / "bootstrap-operated"
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_NAME": "Validator Test",
            "GIT_AUTHOR_EMAIL": "validator@example.invalid",
            "GIT_COMMITTER_NAME": "Validator Test",
            "GIT_COMMITTER_EMAIL": "validator@example.invalid",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        })
        if os.name == "nt":
            command = [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(ROOT / "scripts" / "bootstrap-new-project.ps1"),
                "-Destination", str(project), "-ProjectName", "Validator Integration", "-Profile", "operated",
            ]
        else:
            command = [
                "sh", str(ROOT / "scripts" / "bootstrap-new-project.sh"),
                str(project), "Validator Integration", "operated",
            ]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        _, profile, findings = self.validate_project(project)
        self.assertEqual(profile, "operated")
        self.assertFalse([item for item in findings if item.severity == "ERROR"], findings)

    def test_explicit_profile_reports_missing_required_file(self):
        project = self.make_project("minimal")
        (project / "README.md").unlink()
        _, _, findings = self.validate_project(project, "minimal")
        self.assertIn("profile.missing", finding_codes(findings))

    def test_ambiguous_profile_requires_explicit_choice(self):
        project = self.make_project("minimal")
        (project / "docs" / "architecture").mkdir(parents=True)
        (project / "docs" / "architecture" / "ARCHITECTURE.md").write_text("# Partial\n", encoding="utf-8")
        _, profile, findings = self.validate_project(project)
        self.assertIsNone(profile)
        self.assertIn("profile.ambiguous", finding_codes(findings))

    def test_content_safety_findings(self):
        project = self.make_project("minimal")
        readme = project / "README.md"
        readme.write_text(
            "# Unsafe\n<PROJECT_NAME>\n[[MISSING_NOTE]]\n"
            r"C:\Users\alice\private\file.txt" + "\n" + "gh" + "p_" + "A" * 24 + "\n",
            encoding="utf-8",
        )
        (project / ".codex" / "memories").mkdir(parents=True)
        _, _, findings = self.validate_project(project, "minimal")
        codes = finding_codes(findings)
        for expected in (
            "placeholder.remaining", "wikilink.missing", "path.machine_specific",
            "secret.detected", "memory.raw",
        ):
            self.assertIn(expected, codes)

    def test_nested_obsidian_is_an_error(self):
        project = self.make_project("minimal")
        (project / ".obsidian").mkdir()
        _, _, findings = self.validate_project(project, "minimal")
        self.assertIn("obsidian.nested_vault", finding_codes(findings))

    def test_metadata_selects_profile_and_rejects_future_schema(self):
        project = self.make_project("minimal")
        metadata = {"schema_version": validator.load_standard_version(ROOT) + 1, "profile": "minimal"}
        (project / ".project-standard.json").write_text(json.dumps(metadata), encoding="utf-8")
        _, profile, findings = self.validate_project(project)
        self.assertEqual(profile, "minimal")
        self.assertIn("metadata.future_schema", finding_codes(findings))

    def test_global_rule_drift_is_reported_without_exposing_content(self):
        home = self.temp_path / "home"
        active = home / ".codex" / "AGENTS.md"
        active.parent.mkdir(parents=True)
        active.write_text("local divergent rule\n", encoding="utf-8")
        findings = validator.check_global_rules(ROOT, home)
        self.assertIn("doctor.global_unmanaged_conflict", finding_codes(findings))
        self.assertNotIn("local divergent rule", "\n".join(item.message for item in findings))

    def test_cli_exit_codes_and_report_only(self):
        valid = self.make_project("minimal")
        invalid = self.make_project("software")
        (invalid / "README.md").unlink()
        base = [sys.executable, str(VALIDATOR_PATH), "--contract-root", str(ROOT), "--kind", "project"]
        self.assertEqual(subprocess.run(base + ["--root", str(valid)], capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(base + ["--root", str(invalid), "--profile", "software"], capture_output=True).returncode, 1)
        self.assertEqual(
            subprocess.run(base + ["--root", str(invalid), "--profile", "software", "--report-only"], capture_output=True).returncode,
            0,
        )
        broken_contract = self.temp_path / "broken-contract"
        (broken_contract / "config").mkdir(parents=True)
        (broken_contract / "STANDARD_VERSION").write_text("invalid\n", encoding="utf-8")
        self.assertEqual(
            subprocess.run(base + ["--root", str(valid), "--contract-root", str(broken_contract)], capture_output=True).returncode,
            2,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
