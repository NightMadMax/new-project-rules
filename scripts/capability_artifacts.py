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
* **Ownership is declared, not guessed.** Policy comes from the manifest, so a
  seed stays a seed even when its text happens to look like a managed file.
  A template whose source still carries placeholders is rendered by bootstrap;
  this handler records it but never creates it, because the values it would
  need (project name, date) exist only at creation time.
* **What bootstrap already installed is adopted, not fought over.** Bootstrap
  is the first delivery and writes no ledger, so on the first run a file whose
  bytes match the release is recorded as ours instead of reported as a
  conflict. Only content that differs is a conflict.
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
ACTIONS = ("create", "adopt", "update", "remove", "skip")


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
    # Set only for a seed created from a template: the values the project states
    # about itself, resolved when the plan was built rather than at write time.
    substitution: Optional[tuple[tuple[str, str], ...]] = None


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


def project_substitution(project_root: Path) -> dict[str, str]:
    """Placeholder values a project already states about itself.

    Read rather than invented: the name and the schema come from the project
    metadata, and the date is today. A value that cannot be read comes back
    empty so the caller refuses instead of writing a guess into a file.
    """
    import datetime

    metadata_path = project_root / ".project-standard.json"
    metadata: dict = {}
    if metadata_path.is_file():
        try:
            loaded = json.loads(metadata_path.read_bytes().decode("utf-8"))
            metadata = loaded if isinstance(loaded, dict) else {}
        except (ValueError, UnicodeDecodeError):
            metadata = {}
    schema = metadata.get("schema_version")
    return {
        "<PROJECT_NAME>": str(metadata.get("project_name") or project_root.resolve().name),
        "<SCHEMA_VERSION>": str(schema) if isinstance(schema, int) and schema > 0 else "",
        "<YYYY-MM-DD>": datetime.date.today().isoformat(),
    }


def needs_rendering(source: Path, payload_class: str) -> bool:
    """True when delivery would require values only bootstrap knows."""
    if artifacts_ledger.manifest_class_to_ledger(payload_class) != "template":
        return False
    return any(placeholder in source.read_bytes() for placeholder in PLACEHOLDERS)


def build_plan(
    project_root: Path,
    capability: str,
    artifacts: Sequence[tuple[str, Path, str, str]],
) -> Plan:
    """Compare the release with the project.

    ``artifacts`` is a sequence of ``(target, source, payload_class, policy)``
    for one capability; the caller resolves it from the manifest, so this module
    stays independent of how the release is described.
    """
    owner = f"capability:{capability}"
    ledger = read_ledger(project_root)
    installed = installed_entries(ledger, owner)

    operations: list[Operation] = []
    conflicts: list[str] = []
    seen: set[str] = set()

    for target, source, payload_class, policy in artifacts:
        if target in seen:
            raise CapabilityArtifactsError(f"Release declares {target} twice")
        seen.add(target)
        if artifacts_ledger.unsafe_target(target):
            raise CapabilityArtifactsError(f"Unsafe target in release: {target}")
        if not source.is_file():
            raise CapabilityArtifactsError(f"Missing release source for {target}")
        if policy not in ("managed", "seed"):
            raise CapabilityArtifactsError(f"Unsupported policy '{policy}' for {target}")
        if payload_class not in artifacts_ledger.MANIFEST_PAYLOAD_CLASSES:
            raise CapabilityArtifactsError(f"Unknown payload class '{payload_class}' for {target}")
        parent = (project_root / target).parent
        if parent.exists() and parent.resolve() != (project_root / target).parent.absolute().resolve():
            raise CapabilityArtifactsError(f"Target leaves the project through a symlink: {target}")
        if parent.exists() and project_root.resolve() not in parent.resolve().parents and parent.resolve() != project_root.resolve():
            raise CapabilityArtifactsError(f"Target leaves the project through a symlink: {target}")

        path = project_root / target
        current = path.read_bytes() if path.is_file() else None
        record = installed.get(target)
        ledger_class = artifacts_ledger.manifest_class_to_ledger(payload_class)
        rendered = needs_rendering(source, payload_class)

        substitution = None
        if rendered and current is None:
            # Adding a capability to an existing project lands here for every
            # seed template, and refusing meant a capability could only ever be
            # chosen at creation. The values are not bootstrap's secret: the
            # project states its own name and schema, and the date is today. The
            # placeholder set stays the one above, so there is no second
            # definition of what a placeholder is.
            substitution = project_substitution(project_root)
            missing = [name for name, value in substitution.items() if not value]
            if missing:
                conflicts.append(
                    f"{target}: needs {', '.join(sorted(missing))}, which this project does not state; "
                    "run the project validator first")
                continue

        if policy == "seed":
            if current is None:
                action, detail = "create", "seed created once"
                if substitution is not None:
                    detail = "seed created once, rendered from project metadata"
            elif record is None:
                action, detail = "adopt", "seed already present, recording it"
            else:
                action, detail = "skip", "seed already present"
            operations.append(Operation(
                target, action, policy, ledger_class, owner, source, None,
                record["hash"] if record else None, detail,
                tuple(substitution.items()) if substitution and action == "create" else None,
            ))
            continue

        if rendered:
            # Rendered at creation, so its bytes legitimately differ from the
            # source: record it, never compare or overwrite.
            operations.append(Operation(
                target, "skip" if record else "adopt", "managed", ledger_class, owner,
                source, None, record["hash"] if record else None, "rendered by bootstrap",
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
            if current_hash == desired:
                # Installed by bootstrap, which writes no ledger: record it.
                operations.append(Operation(
                    target, "adopt", policy, ledger_class, owner, source, desired, None,
                    "already matches the release",
                ))
                continue
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
        if record["policy"] == "owned-block":
            raise CapabilityArtifactsError(
                f"{target}: removing an owned block is not supported; it shares the file with others"
            )
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

    # Build and validate the ledger before touching files: a document that
    # would be rejected must not leave the project half-updated.
    document = ledger_document(project_root, plan)

    staged: list[tuple[Path, Path]] = []
    removed: list[tuple[Path, Path]] = []
    created: list[Path] = []
    created_directories: list[Path] = []
    try:
        verify_preconditions(project_root, plan)
        # Stage first: nothing in the project changes until every file is ready.
        for operation in plan.operations:
            if operation.action in ("create", "update"):
                assert operation.source is not None
                path = project_root / operation.target
                for ancestor in reversed(path.parent.parents):
                    if not ancestor.exists() and project_root in ancestor.parents:
                        created_directories.append(ancestor)
                if not path.parent.exists():
                    created_directories.append(path.parent)
                path.parent.mkdir(parents=True, exist_ok=True)
                staged_path = _staged_name(path)
                if operation.substitution:
                    body = operation.source.read_bytes()
                    for placeholder, value in operation.substitution:
                        body = body.replace(placeholder.encode("utf-8"), value.encode("utf-8"))
                    staged_path.write_bytes(body)
                    # A rendered seed cannot match the source hash — that is the
                    # point of rendering — so the check is that nothing is left
                    # unsubstituted.
                    for placeholder in PLACEHOLDERS:
                        if placeholder in body:
                            raise CapabilityArtifactsError(
                                f"{operation.target}: {placeholder.decode('utf-8')} remains after rendering")
                else:
                    shutil.copyfile(operation.source, staged_path)
                    # A seed carries no recorded hash, so verify against the source.
                    expected = operation.desired_hash or digest_bytes(operation.source.read_bytes())
                    if digest_bytes(staged_path.read_bytes()) != expected:
                        raise CapabilityArtifactsError(
                            f"Staged copy of {operation.target} does not match the release")
                staged.append((staged_path, path))

        for operation in plan.operations:
            if operation.action == "remove":
                path = project_root / operation.target
                backup = _staged_name(path)
                os.replace(path, backup)
                removed.append((backup, path))

        for staged_path, path in staged:
            if path.exists():
                # Keep the original until the whole chain has landed: a failure
                # on a later file must be able to put this one back.
                backup = path.with_name(f".{path.name}.capability-artifacts-previous")
                os.replace(path, backup)
                removed.append((backup, path))
            else:
                created.append(path)
            os.replace(staged_path, path)
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
        for directory in reversed(created_directories):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise CapabilityArtifactsError(f"Apply failed and was rolled back: {exc}") from exc

    try:
        write_ledger_document(project_root, document)
    except OSError as exc:
        for backup, path in reversed(removed):
            if backup.exists():
                os.replace(backup, path)
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise CapabilityArtifactsError(f"Ledger write failed and files were rolled back: {exc}") from exc

    for backup, _ in removed:
        backup.unlink(missing_ok=True)


def verify_preconditions(project_root: Path, plan: Plan) -> None:
    """The project must still look the way the plan was built against."""
    for operation in plan.operations:
        path = project_root / operation.target
        if operation.action == "create":
            if path.exists():
                raise CapabilityArtifactsError(f"{operation.target} appeared after planning")
        elif operation.action in ("update", "remove"):
            if not path.is_file():
                raise CapabilityArtifactsError(f"{operation.target} disappeared after planning")
            if digest_bytes(path.read_bytes()) != operation.installed_hash:
                raise CapabilityArtifactsError(f"{operation.target} changed after planning")


def ledger_document(project_root: Path, plan: Plan) -> dict:
    """The ledger as it will look once the plan has been applied."""
    owner = f"capability:{plan.capability}"
    ledger = read_ledger(project_root)
    entries = [entry for entry in ledger["artifacts"] if entry["owner"] != owner]
    touched = {operation.target for operation in plan.operations}

    # Entries this plan says nothing about stay, as long as their file is there.
    for entry in ledger["artifacts"]:
        if entry["owner"] == owner and entry["target"] not in touched:
            if (project_root / entry["target"]).exists():
                entries.append(dict(entry))

    for operation in plan.operations:
        if operation.action == "remove":
            continue
        path = project_root / operation.target
        if operation.policy == "seed" or operation.detail == "rendered by bootstrap":
            entries.append({
                "target": operation.target, "owner": owner, "policy": "seed",
                "payload_class": operation.payload_class, "hash": None,
            })
            continue
        expected = operation.desired_hash or (
            digest_bytes(path.read_bytes()) if path.is_file() else None
        )
        if expected is None:
            continue
        entries.append({
            "target": operation.target, "owner": owner, "policy": operation.policy,
            "payload_class": operation.payload_class, "hash": expected,
        })

    document = artifacts_ledger.build_ledger(entries)
    issues = artifacts_ledger.validate_ledger(document)
    if issues:
        raise CapabilityArtifactsError(f"Refusing to write an invalid ledger: {issues[0]}")
    return document


def write_ledger_document(project_root: Path, document: dict) -> None:
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
