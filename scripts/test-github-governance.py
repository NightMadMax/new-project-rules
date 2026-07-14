#!/usr/bin/env python3
"""Regression tests for the read-only GitHub governance audit."""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_github_governance", ROOT / "scripts/check_github_governance.py"
)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


class GovernanceTests(unittest.TestCase):
    def state(self, repository="NightMadMax/best-practices"):
        checks = checker.POLICIES[repository]["checks"]
        metadata = {"owner": {"login": "NightMadMax"}, "default_branch": "main"}
        ruleset = {
            "enforcement": "active",
            "bypass_actors": [
                {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
            ],
            "rules": [
                {"type": "deletion"}, {"type": "non_fast_forward"},
                {"type": "pull_request"},
                {"type": "required_status_checks", "parameters": {
                    "required_status_checks": [{"context": item} for item in checks]
                }},
            ],
        }
        collaborators = [{"login": "NightMadMax", "permissions": {"admin": True}}]
        return metadata, ruleset, collaborators

    def test_reviewed_single_admin_state_passes(self):
        self.assertEqual([], checker.validate_state(
            "NightMadMax/best-practices", *self.state()
        ))

    def test_second_admin_breaks_invariant(self):
        metadata, ruleset, collaborators = self.state()
        collaborators.append({"login": "second-admin", "permissions": {"admin": True}})
        problems = checker.validate_state(
            "NightMadMax/best-practices", metadata, ruleset, collaborators
        )
        self.assertTrue(any("sole admin" in problem for problem in problems))

    def test_bypass_or_required_guard_drift_is_rejected(self):
        metadata, ruleset, collaborators = self.state()
        ruleset["bypass_actors"] = []
        ruleset["rules"] = [item for item in ruleset["rules"] if item["type"] != "non_fast_forward"]
        problems = checker.validate_state(
            "NightMadMax/best-practices", metadata, ruleset, collaborators
        )
        self.assertTrue(any("Admin always-bypass" in problem for problem in problems))
        self.assertTrue(any("non_fast_forward" in problem for problem in problems))

    def test_github_token_scope_allows_redacted_role_id_only(self):
        metadata, ruleset, collaborators = self.state()
        ruleset["bypass_actors"][0]["actor_id"] = None
        self.assertEqual([], checker.validate_state(
            "NightMadMax/best-practices", metadata, ruleset, collaborators,
            strict_actor_id=False,
        ))
        self.assertTrue(checker.validate_state(
            "NightMadMax/best-practices", metadata, ruleset, collaborators,
            strict_actor_id=True,
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
