"""Shared schema-1 validation and rendering for .project-standard.json."""

from __future__ import annotations

import re
from datetime import date
from typing import Optional, Sequence


PROFILE_NAMES = {"minimal", "software", "operated", "all"}
SOURCE_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


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
    if data.get("profile") not in PROFILE_NAMES:
        issues.append("profile must be minimal, software, operated, or all")
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
    migration_id: str,
    adopted_at: Optional[str] = None,
) -> dict:
    return {
        "schema_version": schema,
        "profile": profile,
        "source": source,
        "source_commit": source_commit,
        "created_at": None,
        "adopted_at": adopted_at or date.today().isoformat(),
        "applied_migrations": [migration_id],
    }
