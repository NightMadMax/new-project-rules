#!/usr/bin/env python3
"""Regression tests for the pinned Best Practices compatibility contract."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_best_practices_contract.py"
SPEC = importlib.util.spec_from_file_location("check_best_practices_contract", MODULE_PATH)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


class BestPracticesContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = checker.load_contract(ROOT / "config/best-practices-contract.json")

    def test_repository_contract_is_valid(self):
        self.assertEqual([], checker.validate_contract(self.contract))
        self.assertEqual([], checker.verify_npr_decision(self.contract, ROOT))

    def test_missing_skill_is_rejected(self):
        changed = json.loads(json.dumps(self.contract))
        changed["required_files"].pop(".agents/skills/apply-best-practices/SKILL.md")
        self.assertTrue(any("misses skills" in item for item in checker.validate_contract(changed)))

    def test_trial_promotion_source_is_rejected(self):
        changed = json.loads(json.dumps(self.contract))
        changed["promotion_source"]["required_status"] = "trial"
        self.assertTrue(any("must be accepted" in item for item in checker.validate_contract(changed)))

    def test_unsupported_schema_is_rejected(self):
        changed = json.loads(json.dumps(self.contract))
        changed["schema_version"] = 2
        self.assertIn("schema_version must be 1", checker.validate_contract(changed))

    def test_changed_adr_is_rejected(self):
        changed = json.loads(json.dumps(self.contract))
        changed["npr_decision"]["sha256"] = "0" * 64
        self.assertIn(
            "NPR decision hash differs from reviewed contract",
            checker.verify_npr_decision(changed, ROOT),
        )

    def test_checkout_commit_hash_and_status_are_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "git@github.com:NightMadMax/best-practices.git"],
                cwd=root,
                check=True,
            )
            required = {}
            for relative in checker.REQUIRED_SKILLS:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("skill\n", encoding="utf-8")
                required[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            practice = root / "practices/common/PC-2026-001-example.md"
            practice.parent.mkdir(parents=True)
            practice.write_text("---\nid: PC-2026-001\nstatus: accepted\n---\n", encoding="utf-8")
            required[str(practice.relative_to(root))] = hashlib.sha256(practice.read_bytes()).hexdigest()
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip()
            contract = {
                "schema_version": 1,
                "repository": "NightMadMax/best-practices",
                "source_commit": head,
                "supported_practice_statuses": ["accepted"],
                "retired_routes": ["retired-route"],
                "active_routing_surfaces": ["README.md"],
                "governance": {"default_branch": "main", "requires_protection": True},
                "npr_decision": self.contract["npr_decision"],
                "required_files": required,
                "promotion_source": {
                    "id": "PC-2026-001",
                    "path": str(practice.relative_to(root)),
                    "required_status": "accepted",
                },
            }
            (root / "README.md").write_text("active route\n", encoding="utf-8")
            self.assertEqual([], checker.verify_checkout(contract, root))
            practice.write_text("---\nid: PC-2026-001\nstatus: trial\n---\n", encoding="utf-8")
            problems = checker.verify_checkout(contract, root)
            self.assertTrue(any("sha256 mismatch" in item for item in problems))
            self.assertTrue(any("not accepted" in item for item in problems))

    def test_retired_route_in_active_surface_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "remote", "add", "origin", "git@github.com:NightMadMax/best-practices.git"], cwd=root, check=True)
            required = {}
            for relative in checker.REQUIRED_SKILLS:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("skill\n", encoding="utf-8")
                required[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            practice = root / "practices/common/PC-2026-001-example.md"
            practice.parent.mkdir(parents=True)
            practice.write_text("---\nid: PC-2026-001\nstatus: accepted\n---\n", encoding="utf-8")
            required[str(practice.relative_to(root))] = hashlib.sha256(practice.read_bytes()).hexdigest()
            (root / "README.md").write_text("retired-route\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            changed = json.loads(json.dumps(self.contract))
            changed["source_commit"] = head
            changed["required_files"] = required
            changed["promotion_source"] = {"id": "PC-2026-001", "path": str(practice.relative_to(root)), "required_status": "accepted"}
            changed["retired_routes"] = ["retired-route"]
            changed["active_routing_surfaces"] = ["README.md"]
            problems = checker.verify_checkout(changed, root)
            self.assertTrue(any("retired route" in item for item in problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
