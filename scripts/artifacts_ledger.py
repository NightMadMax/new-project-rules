"""Shared validation for .project-standard-artifacts.json.

The ledger records what a capability installed into a project and in what state
it left it, so an update can tell "unchanged", "updated by us" and "changed by
the user" apart. It is deliberately narrow:

* only stable Git artifacts — machine paths, ports, CLI availability and local
  runtime state never enter it;
* for a mixed file the hash covers the owned block or key set, not the whole
  file, so a user's edit next door is not read as drift;
* it carries no capability version — that lives in .project-standard.json.
"""

from __future__ import annotations

import os
import re
from typing import Iterable, Sequence

LEDGER_SCHEMA = 1
POLICIES = {"managed", "seed", "owned-block"}
PAYLOAD_CLASSES = {"template", "verbatim", "binary", "owned-block"}
OWNER_RE = re.compile(r"^(standard|capability:[a-z0-9][a-z0-9-]*)$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ENTRY_FIELDS = {"target", "owner", "policy", "payload_class", "hash"}


def unsafe_target(value: object) -> bool:
    """Repo-relative, forward slashes, no escape and no absolute paths."""
    if not isinstance(value, str) or not value or value.strip() != value:
        return True
    if value.startswith("/") or "\\" in value or ":" in value:
        return True
    return os.path.normpath(value).split(os.sep)[0] == ".."


def validate_entry(entry: object, position: int) -> list[str]:
    where = f"artifacts[{position}]"
    if not isinstance(entry, dict):
        return [f"{where} must be a JSON object"]

    issues: list[str] = []
    unknown = sorted(set(entry) - ENTRY_FIELDS)
    if unknown:
        issues.append(f"{where} has unknown fields: {', '.join(unknown)}")
    missing = sorted(ENTRY_FIELDS - set(entry))
    if missing:
        issues.append(f"{where} is missing fields: {', '.join(missing)}")
        return issues

    if unsafe_target(entry["target"]):
        issues.append(f"{where}.target must be a safe repository-relative path")
    if not isinstance(entry["owner"], str) or not OWNER_RE.fullmatch(entry["owner"]):
        issues.append(f"{where}.owner must be 'standard' or 'capability:<id>'")
    policy = entry["policy"]
    if policy not in POLICIES:
        issues.append(f"{where}.policy must be one of {', '.join(sorted(POLICIES))}")
    payload_class = entry["payload_class"]
    if payload_class not in PAYLOAD_CLASSES:
        issues.append(f"{where}.payload_class must be one of {', '.join(sorted(PAYLOAD_CLASSES))}")

    digest = entry["hash"]
    if policy == "seed":
        # A seed is created once and then owned by the user: comparing it to a
        # recorded hash would turn every legitimate edit into drift.
        if digest is not None:
            issues.append(f"{where}.hash must be null for a seed artifact")
    elif not isinstance(digest, str) or not HASH_RE.fullmatch(digest):
        issues.append(f"{where}.hash must be 'sha256:<64 hex>'")

    if policy == "owned-block" and payload_class != "owned-block":
        issues.append(f"{where} with policy owned-block must use payload_class owned-block")
    if payload_class == "owned-block" and policy != "owned-block":
        issues.append(f"{where} with payload_class owned-block must use policy owned-block")
    return issues


def validate_ledger(data: object, known_owners: Iterable[str] = ()) -> list[str]:
    if not isinstance(data, dict):
        return ["ledger root must be a JSON object"]

    schema = data.get("schema_version")
    if not isinstance(schema, int) or isinstance(schema, bool) or schema < 1:
        return ["schema_version must be a positive integer"]
    if schema > LEDGER_SCHEMA:
        return [f"schema_version {schema} is newer than supported ledger schema {LEDGER_SCHEMA}"]
    if schema < LEDGER_SCHEMA:
        return [f"schema_version {schema} requires an explicit migration to {LEDGER_SCHEMA}"]

    issues: list[str] = []
    unknown_keys = sorted(set(data) - {"schema_version", "artifacts"})
    if unknown_keys:
        issues.append(f"ledger has unknown keys: {', '.join(unknown_keys)}")

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        return issues + ["artifacts must be an array"]

    targets: list[str] = []
    owners = set(known_owners)
    for position, entry in enumerate(artifacts):
        entry_issues = validate_entry(entry, position)
        issues.extend(entry_issues)
        if entry_issues or not isinstance(entry, dict):
            continue
        targets.append(entry["target"])
        owner = entry["owner"]
        if owners and owner not in owners:
            issues.append(f"artifacts[{position}].owner is unknown: {owner}")

    duplicates = sorted({target for target in targets if targets.count(target) > 1})
    if duplicates:
        issues.append(f"artifacts must not repeat a target: {', '.join(duplicates)}")
    if targets != sorted(targets):
        # Sorted entries keep the diff of an update readable and deterministic.
        issues.append("artifacts must be sorted by target")
    return issues


def build_ledger(entries: Sequence[dict]) -> dict:
    return {
        "schema_version": LEDGER_SCHEMA,
        "artifacts": sorted(entries, key=lambda entry: entry["target"]),
    }
