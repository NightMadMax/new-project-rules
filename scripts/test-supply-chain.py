#!/usr/bin/env python3
"""Regression tests for GitHub Actions supply-chain policy."""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "scripts" / "check-action-pins.py"
SPEC = importlib.util.spec_from_file_location("check_action_pins", MODULE_PATH)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


class SupplyChainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="supply-chain-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workflows = self.root / ".github" / "workflows"
        self.workflows.mkdir(parents=True)

    def write(self, reference: str):
        (self.workflows / "ci.yml").write_text(
            f"jobs:\n  test:\n    steps:\n      - uses: {reference}\n", encoding="utf-8"
        )

    def test_commit_sha_is_accepted(self):
        self.write("actions/checkout@" + "a" * 40 + " # v5")
        self.assertEqual(checker.check_repository(self.root), [])
        self.write('"actions/checkout@' + "a" * 40 + '"')
        self.assertEqual(checker.check_repository(self.root), [])

    def test_mutable_tag_and_branch_are_rejected(self):
        for reference in ("actions/checkout@v5", "owner/action@main"):
            with self.subTest(reference=reference):
                self.write(reference)
                self.assertTrue(checker.check_repository(self.root))

    def test_local_action_is_accepted(self):
        self.write("./.github/actions/local")
        self.assertEqual(checker.check_repository(self.root), [])

    def test_docker_requires_digest(self):
        self.write("docker://alpine@sha256:" + "b" * 64)
        self.assertEqual(checker.check_repository(self.root), [])
        self.write("docker://alpine:latest")
        self.assertTrue(checker.check_repository(self.root))

    def test_repository_workflows_are_pinned(self):
        self.assertEqual(checker.check_repository(ROOT), [])

    def test_repository_workflow_security_posture(self):
        for path in checker.workflow_files(ROOT):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("permissions:\n  contents: read", text)
                self.assertNotIn("pull_request_target", text)
                checkout_count = text.count("uses: actions/checkout@")
                self.assertEqual(text.count("persist-credentials: false"), checkout_count)

    def test_dependabot_and_macos_smoke_contract(self):
        dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        self.assertIn("package-ecosystem: github-actions", dependabot)
        self.assertIn("interval: weekly", dependabot)
        macos = (ROOT / ".github" / "workflows" / "macos-smoke.yml").read_text(encoding="utf-8")
        self.assertIn("runs-on: macos-latest", macos)
        self.assertIn("workflow_dispatch:", macos)
        self.assertIn('      - "scripts/**"', macos)

    def test_no_script_decodes_a_subprocess_with_the_locale_encoding(self):
        # Defect 231 was this, fixed in the two places it had been noticed:
        # a bare text flag decodes with locale.getpreferredencoding(), which on a
        # Windows machine is the ANSI code page while git answers UTF-8. Cyrillic
        # does not raise there — it comes back mojibake — so `rev-parse
        # --show-toplevel` stops matching the path and the repository looks like
        # it is not a repository root. This project's own root is a Cyrillic
        # name. The rule is asserted for the whole tree instead of per call.
        offenders = []
        for path in sorted((ROOT / "scripts").glob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "text=True" in line and "encoding=" not in line:
                    offenders.append(f"{path.name}:{number}")
        self.assertEqual([], offenders, "a text subprocess without an explicit encoding")

    def test_vendored_upstream_states_where_it_came_from(self):
        # This subtree is somebody else's code and the capability copies part of
        # it into every created project. The permission exists — the upstream
        # README grants it in as many words — but it lived only in that README,
        # so a reader of this repository saw 161 files of foreign code and no
        # basis for them. The commit is asserted against the inventory so that
        # refreshing the pin cannot leave the notice describing another release.
        notice_path = ROOT / "templates/new-project/capabilities/1c/upstream/NOTICE.md"
        self.assertTrue(notice_path.is_file(), "vendored upstream carries no NOTICE.md")
        notice = notice_path.read_text(encoding="utf-8")
        inventory = (ROOT / "config/1c-upstream-inventory.txt").read_text(encoding="utf-8")
        pinned = re.search(r"@\s*([0-9a-f]{40})", inventory)
        self.assertIsNotNone(pinned, "the upstream inventory names no pinned commit")
        self.assertIn(pinned.group(1), notice,
                      "NOTICE.md describes a different commit than the inventory pins")
        for expected in ("comol/ai_rules_1c", "Никакой лицензии"):
            self.assertIn(expected, notice, f"NOTICE.md does not state {expected!r}")

    def test_codeowners_protects_governance_surfaces(self):
        codeowners = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
        self.assertIn("* @NightMadMax", codeowners)
        for path in ("/.github/", "/.agents/", "/config/", "/scripts/", "/templates/"):
            with self.subTest(path=path):
                self.assertIn(f"{path} @NightMadMax", codeowners)


if __name__ == "__main__":
    unittest.main(verbosity=2)
