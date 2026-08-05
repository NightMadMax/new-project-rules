"""Shared validation and rendering for .project-standard.json."""

from __future__ import annotations

import re
from datetime import date
from typing import Optional, Sequence


PROFILE_RANKS = {"minimal": 0, "software": 1, "operated": 2, "all": 3}
PROFILE_NAMES = set(PROFILE_RANKS)
# The core a capability cannot be created without. Mirrored in
# config/capability-core.tsv for the shell and PowerShell bootstrap; a test
# keeps the two in step. The operational half of a 1C project (environments,
# databases, diagnostics) has no place in a lighter profile.
CAPABILITY_CORE = {
    "1c": {"min_profile": "operated", "stack": "1c"},
    # These two carry no mandatory stack, but they do carry documents with a
    # docs section — and a docs section needs `docs/README.md`, which appears at
    # `software`. Without the minimum here, `minimal` + capability wrote every
    # file, failed while indexing, and the rollback removed the destination.
    "jira-confluence": {"min_profile": "software", "stack": "-"},
    "transcribe": {"min_profile": "software", "stack": "-"},
}
CAPABILITY_MIN_PROFILE = {name: core["min_profile"] for name, core in CAPABILITY_CORE.items()}
CAPABILITY_REQUIRED_STACK = {name: core["stack"] for name, core in CAPABILITY_CORE.items()
                             if core["stack"] != "-"}
CAPABILITY_NAMES = {"jira-confluence", "1c", "transcribe"}
# The ports capability `1c` reserves for the per-base Toolkit (decision 1.8).
# Declared once: the validator accepted a base the renderer then dropped without
# a word, because widening the range in one module never reached the other.
ONE_C_TOOLKIT_PORTS = range(6003, 6013)
SOURCE_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
RELEASE_ID_RE = re.compile(r"^[0-9a-f]{64}$")


def valid_date(value: object) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def validate_metadata(
    data: object,
    current_schema: int,
    expected_source: str,
    known_project_migrations: Sequence[str],
) -> list[str]:
    if not isinstance(data, dict):
        return ["metadata root must be a JSON object"]
    issues: list[str] = []
    schema = data.get("schema_version")
    if not isinstance(schema, int) or isinstance(schema, bool) or schema < 1:
        return ["schema_version must be a positive integer"]
    if schema > current_schema:
        return [f"schema_version {schema} is newer than supported schema {current_schema}"]
    if schema < current_schema:
        return [f"schema_version {schema} requires an explicit migration to {current_schema}"]
    profile = data.get("profile")
    if profile not in PROFILE_NAMES:
        issues.append("profile must be minimal, software, operated, or all")
    capabilities = data.get("capabilities", [])
    if current_schema >= 3 and "capabilities" not in data:
        issues.append("capabilities must be present in schema 3+ metadata")
    if not isinstance(capabilities, list) or not all(isinstance(item, str) for item in capabilities):
        issues.append("capabilities must be a string array")
    elif len(capabilities) != len(set(capabilities)):
        issues.append("capabilities must not contain duplicates")
    else:
        unknown_capabilities = sorted(set(capabilities) - CAPABILITY_NAMES)
        if unknown_capabilities:
            issues.append(f"capabilities contains unknown IDs: {', '.join(unknown_capabilities)}")
        for name in sorted(set(capabilities) & set(CAPABILITY_MIN_PROFILE)):
            minimum = CAPABILITY_MIN_PROFILE[name]
            if profile in PROFILE_RANKS and PROFILE_RANKS[profile] < PROFILE_RANKS[minimum]:
                issues.append(
                    f"capability '{name}' requires profile '{minimum}' or higher, not '{profile}'"
                )
    releases = data.get("capability_releases", {})
    if current_schema >= 5 and "capability_releases" not in data:
        issues.append("capability_releases must be present in schema 5+ metadata")
    if not isinstance(releases, dict):
        issues.append("capability_releases must be a JSON object")
    else:
        for name, record in sorted(releases.items()):
            if name not in CAPABILITY_NAMES:
                issues.append(f"capability_releases contains unknown capability: {name}")
                continue
            if isinstance(capabilities, list) and name not in capabilities:
                # A recorded release is the project's own evidence that it was
                # created with the capability. Dropping the capability while the
                # record stays is exactly the removal decision 1.5 forbids.
                issues.append(
                    f"capability '{name}' has an installed release and cannot be removed from capabilities"
                )
            if not isinstance(record, dict) or set(record) != {"version", "release_id"}:
                issues.append(f"capability_releases[{name}] must hold version and release_id only")
                continue
            if not isinstance(record["version"], str) or not SEMVER_RE.fullmatch(record["version"]):
                issues.append(f"capability_releases[{name}].version must be SemVer")
            if not isinstance(record["release_id"], str) or not RELEASE_ID_RE.fullmatch(record["release_id"]):
                issues.append(f"capability_releases[{name}].release_id must be a 64-hex digest")
    source = data.get("source")
    if not isinstance(source, str) or not SOURCE_RE.fullmatch(source):
        issues.append("source must use owner/repository format")
    elif source != expected_source:
        issues.append(f"source must match {expected_source}")
    commit = data.get("source_commit")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        issues.append("source_commit must be a lowercase 40-hex commit ID")
    created = data.get("created_at")
    if created is not None and not valid_date(created):
        issues.append("created_at must be null or an ISO date")
    if not valid_date(data.get("adopted_at")):
        issues.append("adopted_at must be an ISO date")
    applied = data.get("applied_migrations")
    if not isinstance(applied, list) or not all(isinstance(item, str) for item in applied):
        issues.append("applied_migrations must be a string array")
    elif len(applied) != len(set(applied)):
        issues.append("applied_migrations must not contain duplicates")
    else:
        unknown = sorted(set(applied) - set(known_project_migrations))
        if unknown:
            issues.append(f"applied_migrations contains unknown IDs: {', '.join(unknown)}")
    return issues


def build_legacy_metadata(
    schema: int,
    profile: str,
    source: str,
    source_commit: str,
    migration_ids: Sequence[str],
    adopted_at: Optional[str] = None,
    capabilities: Sequence[str] = (),
) -> dict:
    return {
        "schema_version": schema,
        "profile": profile,
        "capabilities": list(capabilities),
        "capability_releases": {},
        "source": source,
        "source_commit": source_commit,
        "created_at": None,
        "adopted_at": adopted_at or date.today().isoformat(),
        "applied_migrations": list(migration_ids),
    }
