#!/usr/bin/env python3
"""Read-only audit of main rulesets and the single-admin invariant."""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import List, Mapping, Optional, Sequence


POLICIES = {
    "NightMadMax/new-project-rules": {
        "ruleset_id": 18603924,
        "checks": {
            "shell", "powershell", "cross-repo-e2e (ubuntu-latest)",
            "cross-repo-e2e (windows-latest)", "cross-repo-e2e (macos-latest)",
        },
    },
    "NightMadMax/best-practices": {"ruleset_id": 18538769, "checks": {"validate"}},
}


def cast_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, dict) else {}


def gh_json(path: str):
    result = subprocess.run(
        ["gh", "api", path], check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return json.loads(result.stdout)


def validate_state(repository, metadata, ruleset, collaborators, strict_actor_id=True) -> List[str]:
    policy = POLICIES[repository]
    owner = str(cast_mapping(metadata.get("owner")).get("login", ""))
    problems: List[str] = []
    if metadata.get("default_branch") != "main":
        problems.append("default branch must be main")
    if ruleset.get("enforcement") != "active":
        problems.append("Protect main ruleset must be active")
    bypass = ruleset.get("bypass_actors")
    expected_ids = {5} if strict_actor_id else {5, None}
    bypass_redacted = not strict_actor_id and not bypass
    bypass_ok = bypass_redacted or (
        isinstance(bypass, list) and len(bypass) == 1 and isinstance(bypass[0], dict)
        and bypass[0].get("actor_type") == "RepositoryRole"
        and bypass[0].get("bypass_mode") == "always"
        and bypass[0].get("actor_id") in expected_ids
    )
    if not bypass_ok:
        problems.append("ruleset must keep the reviewed Admin always-bypass")
    rules = [item for item in ruleset.get("rules", []) if isinstance(item, dict)]
    rule_types = {str(item.get("type")) for item in rules}
    for required in ("deletion", "non_fast_forward", "pull_request", "required_status_checks"):
        if required not in rule_types:
            problems.append(f"ruleset misses {required}")
    status_rule = next((item for item in rules if item.get("type") == "required_status_checks"), {})
    parameters = cast_mapping(status_rule.get("parameters"))
    checks = {
        str(item.get("context")) for item in parameters.get("required_status_checks", [])
        if isinstance(item, dict)
    }
    if not policy["checks"].issubset(checks):
        problems.append("ruleset misses required status checks")
    admins = sorted(
        str(item.get("login")) for item in collaborators
        if cast_mapping(item.get("permissions")).get("admin") is True
    )
    if admins != [owner]:
        problems.append(
            f"Admin bypass is safe only when owner {owner!r} is the sole admin; found {admins}"
        )
    return problems


def audit(repository: str, strict_actor_id: bool = True) -> List[str]:
    policy = POLICIES[repository]
    metadata = gh_json(f"repos/{repository}")
    ruleset = gh_json(f"repos/{repository}/rulesets/{policy['ruleset_id']}")
    collaborators = gh_json(f"repos/{repository}/collaborators?affiliation=all&permission=admin")
    if not isinstance(metadata, dict) or not isinstance(ruleset, dict) or not isinstance(collaborators, list):
        return ["GitHub API returned an unexpected response shape"]
    return validate_state(repository, metadata, ruleset, collaborators, strict_actor_id)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", action="append", choices=sorted(POLICIES))
    parser.add_argument(
        "--github-token-scope", action="store_true",
        help="audit one current repository when GITHUB_TOKEN redacts bypass actors",
    )
    args = parser.parse_args(argv)
    repositories = args.repository or sorted(POLICIES)
    if args.github_token_scope and len(repositories) != 1:
        parser.error("--github-token-scope requires exactly one --repository")
    failed = False
    for repository in repositories:
        try:
            problems = audit(repository, strict_actor_id=not args.github_token_scope)
        except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
            problems = [f"cannot query GitHub API: {error}"]
        if problems:
            failed = True
            for problem in problems:
                print(f"ERROR [{repository}]: {problem}")
        else:
            print(f"OK [{repository}]: active ruleset, reviewed bypass, sole owner-admin")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
