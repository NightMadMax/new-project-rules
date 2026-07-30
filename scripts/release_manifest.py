"""Contract for a capability release: the passport and the artifact ledger.

A release is one aggregate: a person installs and updates it as a whole, so the
build has to answer two questions before it can be published.

* **Is the inventory complete?** Every tracked file of every pinned source must
  have a row. Nothing is dropped silently: even a file we decide not to install
  is routed to an owner, because "not mentioned" and "deliberately excluded"
  look the same in a diff a year later.
* **Is the output the same for the same input?** ``release_id`` is a digest of
  the canonical passport and ledger, with no timestamp in it, so rebuilding an
  unchanged input produces an unchanged identifier.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Iterable

RELEASE_NAME = "config/1c-release.json"
ARTIFACTS_NAME = "config/1c-artifacts.tsv"
RELEASE_SCHEMA = 1
ARTIFACT_FIELDS = (
    "source", "source_path", "source_selector", "source_sha256", "action", "action_id",
    "ownership", "target_path", "target_sha256",
)
ACTIONS = ("copy", "adapt", "compile", "route")
DEPENDENCY_CLASSES = ("required", "conditional", "optional")
OWNERSHIPS = ("project-managed", "project-seed", "provider-only", "pinned-external")
BLOCKED, REVIEW = "blocked", "review"
SEVERITIES = (BLOCKED, REVIEW)
# The mandatory core stack of the capability, inside a Best Practices checkout.
BEST_PRACTICES_SOURCE = "best-practices"
PRACTICE_DIRECTORY = "practices/1c"
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def unsafe_path(value: str) -> bool:
    """Repo-relative, no escape, no absolute path."""
    if not value or value.strip() != value:
        return True
    if value.startswith("/") or "\\" in value or ":" in value:
        return True
    return ".." in value.split("/")


class ReleaseError(Exception):
    """The release passport or the artifact ledger is invalid."""


class Finding(str):
    """A finding that carries how badly it lands.

    A flat list of sentences cannot say whether a release is unpublishable or
    merely needs a human to look at it, so "требует semantic review" was
    indistinguishable from "всё хорошо" and from "блокировано". The finding
    stays a string — every caller that prints or greps one keeps working — and
    gains the one thing that was missing.
    """

    severity: str

    def __new__(cls, severity: str, message: str) -> "Finding":
        if severity not in SEVERITIES:
            raise ValueError(f"unknown severity: {severity}")
        finding = super().__new__(cls, message)
        finding.severity = severity
        return finding


def release_status(findings: Iterable[str]) -> str:
    """`blocked`, `review-required` or `ready`.

    A finding without a severity counts as blocking: an unclassified problem is
    not a problem somebody decided was safe.
    """
    severities = {getattr(finding, "severity", BLOCKED) for finding in findings}
    if BLOCKED in severities:
        return "blocked"
    if REVIEW in severities:
        return "review-required"
    return "ready"


def practice_gate(best_practices_root: Path) -> list[Finding]:
    """The mandatory core stack must contain a practice, not a promise.

    Every 1C project created from the standard is wired to the Best Practices
    stack `1c` and cannot drop it. Publishing a release while that index is
    empty ships a mandatory element with nothing inside it (decision 1.29).
    """
    directory = best_practices_root / PRACTICE_DIRECTORY
    if not directory.is_dir():
        return [Finding(BLOCKED, f"{PRACTICE_DIRECTORY} does not exist in the Best Practices checkout")]

    seen: list[str] = []
    for path in sorted(directory.glob("*.md")):
        if path.name == "README.md":
            continue
        fields = frontmatter(path)
        status, evidence = fields.get("status", ""), fields.get("evidence", "")
        seen.append(f"{path.name}: status={status or '—'}")
        if status == "accepted" and evidence:
            return []
    if not seen:
        return [Finding(BLOCKED, f"{PRACTICE_DIRECTORY} holds no practice; decision 1.29 blocks the first release")]
    return [Finding(
        BLOCKED,
        f"{PRACTICE_DIRECTORY} has no accepted practice with evidence: {'; '.join(seen)}",
    )]


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_bytes().decode("utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        if ":" in line and not line[:1].isspace():
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"')
    return fields


def canonical_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def read_release(contract_root: Path) -> dict:
    path = contract_root / RELEASE_NAME
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"Cannot read {RELEASE_NAME}: {exc}") from exc
    issues = validate_release(data)
    if issues:
        raise ReleaseError(f"{RELEASE_NAME} is invalid: {issues[0]}")
    return data


def validate_release(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["release passport must be a JSON object"]

    issues: list[str] = []
    expected = {
        "schema_version", "capability", "version", "release_id", "sources", "inventory_count",
        "dependencies", "mcp_roles", "binaries",
    }
    unknown = sorted(set(data) - expected)
    if unknown:
        issues.append(f"unknown keys: {', '.join(unknown)}")
    missing = sorted(expected - set(data))
    if missing:
        return issues + [f"missing keys: {', '.join(missing)}"]

    if data["schema_version"] != RELEASE_SCHEMA:
        issues.append(f"schema_version must be {RELEASE_SCHEMA}")
    if not isinstance(data["capability"], str) or not data["capability"]:
        issues.append("capability must be a non-empty string")
    if not isinstance(data["version"], str) or not SEMVER_RE.fullmatch(data["version"]):
        issues.append("version must be SemVer")
    if not isinstance(data["release_id"], str) or not SHA_RE.fullmatch(data["release_id"]):
        issues.append("release_id must be a 64-hex digest")
    if not isinstance(data["inventory_count"], int) or isinstance(data["inventory_count"], bool) or data["inventory_count"] < 0:
        issues.append("inventory_count must be a non-negative integer")

    for name in ("dependencies", "mcp_roles", "binaries"):
        if not isinstance(data[name], list):
            issues.append(f"{name} must be an array")

    if isinstance(data["dependencies"], list):
        for position, dependency in enumerate(data["dependencies"]):
            where = f"dependencies[{position}]"
            if not isinstance(dependency, dict) or set(dependency) != {"name", "class", "reason"}:
                issues.append(f"{where} must hold name, class and reason")
                continue
            if dependency["class"] not in DEPENDENCY_CLASSES:
                issues.append(f"{where}.class must be one of {', '.join(DEPENDENCY_CLASSES)}")

    if isinstance(data["mcp_roles"], list):
        for position, role in enumerate(data["mcp_roles"]):
            where = f"mcp_roles[{position}]"
            if not isinstance(role, dict) or set(role) != {"role", "provider_id", "tier"}:
                issues.append(f"{where} must hold role, provider_id and tier")

    if isinstance(data["binaries"], list):
        # Executable payload the project trusts by hash: EPF and the like.
        for position, binary in enumerate(data["binaries"]):
            where = f"binaries[{position}]"
            if not isinstance(binary, dict) or set(binary) != {"name", "sha256", "application_kind"}:
                issues.append(f"{where} must hold name, sha256 and application_kind")
                continue
            if not isinstance(binary["sha256"], str) or not SHA_RE.fullmatch(binary["sha256"]):
                issues.append(f"{where}.sha256 must be a 64-hex digest")

    sources = data["sources"]
    if not isinstance(sources, list) or not sources:
        issues.append("sources must be a non-empty array")
        return issues
    names: list[str] = []
    for position, source in enumerate(sources):
        where = f"sources[{position}]"
        if not isinstance(source, dict) or set(source) != {"name", "repository", "commit"}:
            issues.append(f"{where} must hold name, repository and commit")
            continue
        if not isinstance(source["name"], str) or not source["name"]:
            issues.append(f"{where}.name must be a non-empty string")
            continue
        names.append(source["name"])
        if not isinstance(source["commit"], str) or not COMMIT_RE.fullmatch(source["commit"]):
            issues.append(f"{where}.commit must be a 40-hex commit id")
        if not isinstance(source["repository"], str) or "/" not in source["repository"]:
            issues.append(f"{where}.repository must use owner/repository form")
    if len(names) != len(set(names)):
        issues.append("sources must not repeat a name")
    return issues


def read_artifacts(contract_root: Path, known_sources: Iterable[str] = ()) -> list[dict[str, str]]:
    path = contract_root / ARTIFACTS_NAME
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleaseError(f"Cannot read {ARTIFACTS_NAME}: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if tuple(reader.fieldnames or ()) != ARTIFACT_FIELDS:
        raise ReleaseError(f"Unexpected header in {ARTIFACTS_NAME}")

    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    sources = set(known_sources)
    targets: set[str] = set()
    for number, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} does not match the header")
        for field, value in row.items():
            # The ledger is written back verbatim, so a value that carries a
            # separator or a quote would not survive the round trip.
            if any(mark in value for mark in ("\t", "\r", "\n", '"')):
                raise ReleaseError(f"{ARTIFACTS_NAME}:{number} field '{field}' contains a separator or quote")
        if unsafe_path(row["source_path"]):
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} unsafe source_path '{row['source_path']}'")
        if row["target_path"] != "-" and unsafe_path(row["target_path"]):
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} unsafe target_path '{row['target_path']}'")
        if sources and row["source"] not in sources:
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} unknown source '{row['source']}'")
        action = row["action"]
        if action not in ACTIONS:
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} unknown action '{action}'")
        if row["ownership"] not in OWNERSHIPS:
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} unknown ownership '{row['ownership']}'")
        if not SHA_RE.fullmatch(row["source_sha256"]):
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} source_sha256 must be a 64-hex digest")

        # A byte-for-byte copy cannot change the hash; anything else must say
        # which adaptation produced the output.
        if action == "copy" and row["target_sha256"] != row["source_sha256"]:
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} copy must not change the file")
        if action in ("adapt", "compile") and row["action_id"] in ("", "-"):
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} {action} requires an action_id")
        if action == "route":
            if row["target_path"] != "-" or row["target_sha256"] != "-":
                raise ReleaseError(f"{ARTIFACTS_NAME}:{number} route produces no output")
            if row["action_id"] in ("", "-"):
                raise ReleaseError(f"{ARTIFACTS_NAME}:{number} route requires an owner in action_id")
        elif not SHA_RE.fullmatch(row["target_sha256"]):
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} target_sha256 must be a 64-hex digest")

        key = (row["source"], row["source_path"], row["source_selector"])
        if key in seen:
            raise ReleaseError(f"{ARTIFACTS_NAME}:{number} duplicate source {row['source_path']}")
        seen.add(key)
        if row["target_path"] != "-":
            if row["target_path"] in targets:
                raise ReleaseError(f"{ARTIFACTS_NAME}:{number} two rows deliver into {row['target_path']}")
            targets.add(row["target_path"])
        rows.append(row)
    if not rows:
        raise ReleaseError(f"{ARTIFACTS_NAME} declares no artifacts")
    return rows


def artifacts_text(rows: Iterable[dict[str, str]]) -> str:
    lines = ["\t".join(ARTIFACT_FIELDS)]
    for row in sorted(rows, key=lambda item: (item["source"], item["source_path"], item["source_selector"])):
        lines.append("\t".join(row[field] for field in ARTIFACT_FIELDS))
    return "\n".join(lines) + "\n"


def compute_release_id(passport: dict, rows: Iterable[dict[str, str]]) -> str:
    """Deterministic identity of a release: same input, same id, no timestamp."""
    without_id = {key: value for key, value in passport.items() if key != "release_id"}
    digest = hashlib.sha256()
    passport_bytes = canonical_json(without_id).encode("utf-8")
    ledger_bytes = artifacts_text(rows).encode("utf-8")
    # Lengths first: without them, text moved between the two documents could
    # produce the same concatenation and therefore the same identifier.
    digest.update(f"{len(passport_bytes)}:{len(ledger_bytes)}\n".encode("utf-8"))
    digest.update(passport_bytes)
    digest.update(ledger_bytes)
    return digest.hexdigest()


def check_release(contract_root: Path) -> list[Finding]:
    """Everything the build must be able to answer before publishing."""
    findings: list[Finding] = []
    try:
        passport = read_release(contract_root)
        rows = read_artifacts(contract_root, {source["name"] for source in passport["sources"]})
    except ReleaseError as error:
        return [Finding(BLOCKED, str(error))]

    if len(rows) != passport["inventory_count"]:
        findings.append(Finding(
            BLOCKED,
            f"inventory is incomplete: {len(rows)} rows against inventory_count "
            f"{passport['inventory_count']}",
        ))
    expected_id = compute_release_id(passport, rows)
    if passport["release_id"] != expected_id:
        findings.append(Finding(BLOCKED, f"release_id does not match the content: expected {expected_id}"))

    # Without this the practice gate is optional in practice: a passport that
    # simply does not mention Best Practices never gets its checkout, so the
    # gate never runs and the release looks clean. The mandatory core stack has
    # to be a pinned source like any other.
    if BEST_PRACTICES_SOURCE not in {source["name"] for source in passport["sources"]}:
        findings.append(Finding(
            BLOCKED,
            f"sources must pin '{BEST_PRACTICES_SOURCE}': it carries the mandatory core stack "
            f"{PRACTICE_DIRECTORY} (decision 1.29)",
        ))
    return findings
