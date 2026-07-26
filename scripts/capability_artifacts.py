"""Deliver and update capability artifacts as one transaction.

The unit of work is a whole capability release, not a file: a project either
ends up with every artifact of the release or with none of them. Three rules
carry most of the weight.

* **Drift is a stop, not an overwrite.** The ledger records the hash we left
  behind. If the file on disk no longer matches it, someone edited a managed
  artifact, and the plan reports a conflict instead of silently discarding that
  edit.
* **Seed artifacts are created once.** They belong to the user afterwards, so
  they are never compared, updated or removed.
* **A template with placeholders cannot be updated.** Its rendered content
  depends on values known only at bootstrap (project name, date), so it is
  delivered as a seed rather than re-rendered from guesses.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import artifacts_ledger

LEDGER_NAME = ".project-standard-artifacts.json"
PLACEHOLDERS = (b"<PROJECT_NAME>", b"<YYYY-MM-DD>", b"<SCHEMA_VERSION>")
ACTIONS = ("create", "update", "remove", "skip")


class CapabilityArtifactsError(Exception):
    """The request cannot be planned or applied."""


@dataclass(frozen=True)
class Operation:
    target: str
    action: str
    policy: str
    payload_class: str
    owner: str
    source: Optional[Path] = None
    desired_hash: Optional[str] = None
    installed_hash: Optional[str] = None
    detail: str = ""


@dataclass(frozen=True)
class Plan:
    capability: str
    status: str
    operations: tuple[Operation, ...] = ()
    conflicts: tuple[str, ...] = ()

    def summary(self) -> str:
        counts: dict[str, int] = {}
        for operation in self.operations:
            counts[operation.action] = counts.get(operation.action, 0) + 1
        parts = [f"{action}: {counts[action]}" for action in ACTIONS if action in counts]
        return ", ".join(parts) or "no operations"


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def read_ledger(project_root: Path) -> dict:
    path = project_root / LEDGER_NAME
    if not path.exists():
        return {"schema_version": artifacts_ledger.LEDGER_SCHEMA, "artifacts": []}
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CapabilityArtifactsError(f"Cannot read {LEDGER_NAME}: {exc}") from exc
    issues = artifacts_ledger.validate_ledger(data)
    if issues:
        raise CapabilityArtifactsError(f"{LEDGER_NAME} is invalid: {issues[0]}")
    return data


def installed_entries(ledger: dict, owner: str) -> dict[str, dict]:
    return {entry["target"]: entry for entry in ledger["artifacts"] if entry["owner"] == owner}


def is_seed(source: Path, payload_class: str) -> bool:
    """A template that still carries placeholders cannot be re-rendered later."""
    if artifacts_ledger.manifest_class_to_ledger(payload_class) != "template":
        return False
    body = source.read_bytes()
    return any(placeholder in body for placeholder in PLACEHOLDERS)


def build_plan(
    project_root: Path,
    capability: str,
    artifacts: Sequence[tuple[str, Path, str]],
) -> Plan:
    """Compare the release with the project.

    ``artifacts`` is a sequence of ``(target, source, payload_class)`` for one
    capability; the caller resolves it from the manifest, so this module stays
    independent of how the release is described.
    """
    owner = f"capability:{capability}"
    ledger = read_ledger(project_root)
    installed = installed_entries(ledger, owner)

    operations: list[Operation] = []
    conflicts: list[str] = []
    seen: set[str] = set()

    for target, source, payload_class in artifacts:
        if target in seen:
            raise CapabilityArtifactsError(f"Release declares {target} twice")
        seen.add(target)
        if artifacts_ledger.unsafe_target(target):
            raise CapabilityArtifactsError(f"Unsafe target in release: {target}")
        if not source.is_file():
            raise CapabilityArtifactsError(f"Missing release source for {target}")

        path = project_root / target
        current = path.read_bytes() if path.is_file() else None
        record = installed.get(target)
        seed = is_seed(source, payload_class)
        policy = "seed" if seed else "managed"
        ledger_class = artifacts_ledger.manifest_class_to_ledger(payload_class)

        if seed:
            action = "skip" if current is not None else "create"
            detail = "seed already present" if current is not None else "seed created once"
            operations.append(Operation(
                target, action, policy, ledger_class, owner, source, None,
                record["hash"] if record else None, detail,
            ))
            continue

        desired = digest_bytes(source.read_bytes())
        if current is None:
            if record is not None:
                conflicts.append(f"{target}: managed artifact was deleted after installation")
                continue
            operations.append(Operation(target, "create", policy, ledger_class, owner, source, desired, None))
            continue

        current_hash = digest_bytes(current)
        if record is None:
            conflicts.append(f"{target}: file exists but is not recorded as ours")
            continue
        if record["hash"] != current_hash:
            conflicts.append(f"{target}: changed after installation")
            continue
        action = "skip" if current_hash == desired else "update"
        operations.append(Operation(
            target, action, policy, ledger_class, owner, source, desired, record["hash"],
        ))

    for target, record in sorted(installed.items()):
        if target in seen:
            continue
        path = project_root / target
        if record["policy"] == "seed":
            continue
        if not path.is_file():
            operations.append(Operation(
                target, "skip", record["policy"], record["payload_class"], owner,
                None, None, record["hash"], "already gone",
            ))
            continue
        if digest_bytes(path.read_bytes()) != record["hash"]:
            conflicts.append(f"{target}: changed after installation, refusing to remove")
            continue
        operations.append(Operation(
            target, "remove", record["policy"], record["payload_class"], owner,
            None, None, record["hash"], "no longer part of the release",
        ))

    if conflicts:
        return Plan(capability, "conflict", tuple(operations), tuple(conflicts))
    if all(operation.action == "skip" for operation in operations):
        return Plan(capability, "up_to_date", tuple(operations))
    return Plan(capability, "ready", tuple(operations))


def _staged_name(path: Path) -> Path:
    return path.with_name(f".{path.name}.capability-artifacts")


def apply_plan(project_root: Path, plan: Plan) -> None:
    """Apply every operation or leave the project untouched."""
    if plan.status == "up_to_date":
        return
    if plan.status != "ready":
        raise CapabilityArtifactsError(f"Plan is not ready to apply: {plan.status}")

    staged: list[tuple[Path, Path]] = []
    removed: list[tuple[Path, Path]] = []
    created: list[Path] = []
    try:
        # Stage first: nothing in the project changes until every file is ready.
        for operation in plan.operations:
            if operation.action in ("create", "update"):
                assert operation.source is not None
                path = project_root / operation.target
                path.parent.mkdir(parents=True, exist_ok=True)
                staged_path = _staged_name(path)
                shutil.copyfile(operation.source, staged_path)
                # A seed carries no recorded hash, so verify against the source.
                expected = operation.desired_hash or digest_bytes(operation.source.read_bytes())
                if digest_bytes(staged_path.read_bytes()) != expected:
                    raise CapabilityArtifactsError(f"Staged copy of {operation.target} does not match the release")
                staged.append((staged_path, path))

        for operation in plan.operations:
            if operation.action == "remove":
                path = project_root / operation.target
                backup = _staged_name(path)
                os.replace(path, backup)
                removed.append((backup, path))

        for staged_path, path in staged:
            existed = path.exists()
            os.replace(staged_path, path)
            if not existed:
                created.append(path)
        staged.clear()
    except (OSError, CapabilityArtifactsError) as exc:
        # Roll back in reverse: restore removals, drop files we created, and
        # delete anything still staged.
        for backup, path in reversed(removed):
            if backup.exists():
                os.replace(backup, path)
        for path in reversed(created):
            path.unlink(missing_ok=True)
        for staged_path, _ in staged:
            staged_path.unlink(missing_ok=True)
        raise CapabilityArtifactsError(f"Apply failed and was rolled back: {exc}") from exc

    for backup, _ in removed:
        backup.unlink(missing_ok=True)
    write_ledger(project_root, plan)


def write_ledger(project_root: Path, plan: Plan) -> None:
    owner = f"capability:{plan.capability}"
    ledger = read_ledger(project_root)
    entries = [entry for entry in ledger["artifacts"] if entry["owner"] != owner]

    for operation in plan.operations:
        if operation.action == "remove":
            continue
        path = project_root / operation.target
        if operation.policy == "seed":
            entries.append({
                "target": operation.target, "owner": owner, "policy": "seed",
                "payload_class": operation.payload_class, "hash": None,
            })
            continue
        if not path.is_file():
            continue
        entries.append({
            "target": operation.target, "owner": owner, "policy": operation.policy,
            "payload_class": operation.payload_class, "hash": digest_bytes(path.read_bytes()),
        })

    document = artifacts_ledger.build_ledger(entries)
    issues = artifacts_ledger.validate_ledger(document)
    if issues:
        raise CapabilityArtifactsError(f"Refusing to write an invalid ledger: {issues[0]}")
    path = project_root / LEDGER_NAME
    staged_path = _staged_name(path)
    staged_path.write_bytes((json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    os.replace(staged_path, path)


def format_plan(plan: Plan) -> str:
    lines = [f"Capability: {plan.capability}", f"Status: {plan.status}", f"Summary: {plan.summary()}"]
    for operation in sorted(plan.operations, key=lambda item: item.target):
        if operation.action == "skip":
            continue
        detail = f" ({operation.detail})" if operation.detail else ""
        lines.append(f"  {operation.action}: {operation.target} [{operation.policy}]{detail}")
    for conflict in plan.conflicts:
        lines.append(f"  conflict: {conflict}")
    return "\n".join(lines)
