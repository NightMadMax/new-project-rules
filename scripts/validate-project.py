#!/usr/bin/env python3
"""Read-only validator for new-project-rules and generated projects."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable, Optional, Sequence

import sync_global_agents as agent_sync
import artifacts_ledger
import presets as preset_manifest
import project_metadata
import plan_migration as migration_planner
import promotion_candidates


MIN_PYTHON = (3, 9)
PROFILE_RANKS = {"minimal": 0, "software": 1, "operated": 2, "all": 3}
EXPECTED_PROFILE_FIELDS = (
    "minimum_profile",
    "source",
    "destination",
    "root_purpose",
    "docs_section",
    "docs_label",
)
EXPECTED_CAPABILITY_FIELDS = (
    "capability", "source", "destination", "root_purpose", "docs_section", "docs_label",
    "payload_class", "policy",
)
# How an artifact is delivered; the vocabulary lives with the ledger contract so
# the manifest and the ledger cannot drift apart.
PAYLOAD_CLASSES = artifacts_ledger.MANIFEST_PAYLOAD_CLASSES
# Who owns the artifact after delivery: the standard keeps updating a managed
# file, while a seed is created once and belongs to the user afterwards.
ARTIFACT_POLICIES = {"managed", "seed"}
CAPABILITY_REQUIRED_STACK = project_metadata.CAPABILITY_REQUIRED_STACK
TEMPLATE_MARKS = (b"<PROJECT_NAME>", b"<YYYY-MM-DD>", b"<SCHEMA_VERSION>")
# Documents that stay `managed` on purpose: instructions owned by the standard,
# which a project reads rather than fills in, and which must keep updating. Every
# other Markdown target in the root or in `docs/` belongs to the project the
# moment somebody writes in it.
STANDARD_OWNED_PROSE = frozenset({
    # Installation order and what the diagnosis checks — read, not filled in.
    "docs/operations/EDT_SETUP.md",
    # Byte-exact upstream reference index (decision S.13): project-managed
    # on-demand material, and a local edit would break its provenance.
    "References.md",
})
IGNORED_PARTS = {
    ".git",
    "__pycache__",
    ".trash",
    "node_modules",
    ".venv",
    "venv",
    ".astro",
    ".next",
    "vendor",
}
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".ps1", ".sh"}
PLACEHOLDERS = ("<PROJECT_NAME>", "<YYYY-MM-DD>")
RAW_MEMORY_PATHS = (
    (".codex", "memories"),
    (".claude", "projects"),
    (".claude", "memory"),
)
LOCAL_PATH_PATTERNS = (
    re.compile(r"(?i)\b[A-Z]:\\Users\\(?!<|\{)[^\\\s]+\\"),
    re.compile(r"/(?:Users|home)/(?!<|\{)[^/\s]+/"),
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"\b" + "gh" + r"p_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ContractError(Exception):
    """The validator contract itself is invalid."""


@dataclass(frozen=True)
class Artifact:
    minimum_profile: str
    source: str
    destination: str
    root_purpose: str
    docs_section: str
    docs_label: str


@dataclass(frozen=True)
class CapabilityArtifact:
    capability: str
    source: str
    destination: str
    root_purpose: str
    docs_section: str
    docs_label: str
    payload_class: str
    policy: str


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    path: str = ""
    fix: str = ""


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def git_listed_files(root: Path) -> Optional[list[Path]]:
    """Files Git would keep: tracked plus untracked, minus everything .gitignore excludes.

    Returns None when Git cannot answer, so the caller falls back to a plain walk.
    """
    git = shutil.which("git")
    if not git:
        return None
    try:
        listing = subprocess.run(
            [git, "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if listing.returncode != 0:
        return None
    return [root / name for name in listing.stdout.split("\0") if name]


def iter_files(root: Path) -> Iterable[Path]:
    listed = git_listed_files(root)
    candidates: Iterable[Path] = listed if listed is not None else root.rglob("*")
    for path in candidates:
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in IGNORED_PARTS for part in parts):
            continue
        if path.is_file():
            yield path


def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def load_standard_version(contract_root: Path) -> int:
    path = contract_root / "STANDARD_VERSION"
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ContractError(f"Cannot read {path}: {exc}") from exc
    if not re.fullmatch(r"[1-9][0-9]*", raw):
        raise ContractError(f"STANDARD_VERSION must be a positive integer: {path}")
    return int(raw)


def load_artifacts(contract_root: Path) -> list[Artifact]:
    path = contract_root / "config" / "profiles.tsv"
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if tuple(reader.fieldnames or ()) != EXPECTED_PROFILE_FIELDS:
                raise ContractError(f"Unexpected profiles.tsv header: {path}")
            rows = [Artifact(**row) for row in reader]
    except OSError as exc:
        raise ContractError(f"Cannot read {path}: {exc}") from exc

    seen: set[str] = set()
    templates = contract_root / "templates" / "new-project"
    generated = {".editorconfig", ".gitattributes", ".gitignore", ".project-standard.json", "CLAUDE.md"}
    for row in rows:
        if row.minimum_profile not in PROFILE_RANKS:
            raise ContractError(f"Unknown minimum_profile: {row.minimum_profile}")
        destination = Path(row.destination)
        if destination.is_absolute() or ".." in destination.parts:
            raise ContractError(f"Unsafe destination: {row.destination}")
        if row.destination in seen:
            raise ContractError(f"Duplicate destination: {row.destination}")
        seen.add(row.destination)
        if row.source == "@generated":
            if row.destination not in generated:
                raise ContractError(f"Unknown generated artifact: {row.destination}")
        elif not (templates / row.source).is_file():
            raise ContractError(f"Missing template: {row.source}")
        if (row.docs_section == "-") != (row.docs_label == "-"):
            raise ContractError(f"Incomplete docs relationship: {row.destination}")
        if not row.root_purpose:
            raise ContractError(f"Missing root_purpose: {row.destination}")
    return rows


def load_capability_artifacts(contract_root: Path) -> list[CapabilityArtifact]:
    path = contract_root / "config" / "capabilities.tsv"
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if tuple(reader.fieldnames or ()) != EXPECTED_CAPABILITY_FIELDS:
                raise ContractError(f"Unexpected capabilities.tsv header: {path}")
            rows = []
            for number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise ContractError(f"capabilities.tsv:{number} does not match the header")
                rows.append(CapabilityArtifact(**row))
    except OSError as exc:
        raise ContractError(f"Cannot read {path}: {exc}") from exc
    templates = contract_root / "templates" / "new-project"
    for row in rows:
        if row.capability not in project_metadata.CAPABILITY_NAMES:
            raise ContractError(f"Unknown capability: {row.capability}")
        destination = Path(row.destination)
        if destination.is_absolute() or ".." in destination.parts:
            raise ContractError(f"Unsafe capability destination: {row.destination}")
        if not (templates / row.source).is_file():
            raise ContractError(f"Missing capability template: {row.source}")
        if (row.docs_section == "-") != (row.docs_label == "-"):
            raise ContractError(f"Incomplete capability docs relationship: {row.destination}")
        if row.payload_class not in PAYLOAD_CLASSES:
            raise ContractError(f"Unknown payload class '{row.payload_class}': {row.destination}")
        if row.policy not in ARTIFACT_POLICIES:
            raise ContractError(f"Unknown artifact policy '{row.policy}': {row.destination}")
        # A template is rewritten during delivery, so a source that is not text
        # would be corrupted. Catch it in the manifest, not in the project.
        if artifacts_ledger.manifest_class_to_ledger(row.payload_class) == "template":
            try:
                body = (templates / row.source).read_bytes()
                body.decode("utf-8")
            except (UnicodeDecodeError, ValueError):
                raise ContractError(
                    f"Source is not text but is declared as a template: {row.source}"
                ) from None
            if row.policy == "managed" and any(mark in body for mark in TEMPLATE_MARKS):
                raise ContractError(
                    f"A managed template cannot carry placeholders, it could never be updated: {row.source}"
                )
        # A document a team is expected to fill in cannot be `managed`: the first
        # edit becomes drift, and drift stops the whole capability transaction —
        # including its skills. `jira-confluence` shipped eleven such documents
        # as managed, and the failure was invisible until a user's first update.
        # The list below is the reviewed exception: prose owned by the standard.
        if (row.policy == "managed" and row.destination.endswith(".md")
                and (row.destination.startswith("docs/") or "/" not in row.destination)
                and row.destination not in STANDARD_OWNED_PROSE):
            raise ContractError(
                f"A managed document a project is expected to edit: {row.destination}. "
                "Either declare it seed, or add it to STANDARD_OWNED_PROSE with a reason."
            )
    # The manifest catches a row naming a capability the code does not know. The
    # opposite direction had nothing: `transcribe` was a known name delivering
    # nothing for a while, and a capability that delivers nothing is a promise
    # with no artifacts behind it.
    declared = {row.capability for row in rows}
    missing = sorted(project_metadata.CAPABILITY_NAMES - declared)
    if missing:
        raise ContractError(
            f"Capability with no artifacts in the manifest: {', '.join(missing)}. "
            "Either deliver something or remove it from CAPABILITY_NAMES."
        )
    return rows


def artifacts_for_profile(rows: Sequence[Artifact], profile: str) -> list[Artifact]:
    return [
        row for row in rows
        if PROFILE_RANKS[row.minimum_profile] <= PROFILE_RANKS[profile]
        and row.destination != ".project-standard.json"
    ]


def infer_profile(root: Path, rows: Sequence[Artifact]) -> Optional[str]:
    known = {row.destination for row in rows if row.destination != ".project-standard.json"}
    present = {item for item in known if (root / item).is_file()}
    matches = []
    for profile in PROFILE_RANKS:
        expected = {row.destination for row in artifacts_for_profile(rows, profile)}
        if expected == present:
            matches.append(profile)
    return matches[0] if len(matches) == 1 else None


def load_metadata(
    root: Path,
    standard_version: int,
    source: str,
    project_migrations: Sequence[str],
) -> tuple[Optional[dict], list[Finding]]:
    path = root / ".project-standard.json"
    if not path.exists():
        return None, [Finding(
            "INFO",
            "metadata.missing",
            "Project has no .project-standard.json and is treated as legacy.",
            ".project-standard.json",
            "Add metadata through the future migration workflow; do not invent provenance manually.",
        )]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [Finding("ERROR", "metadata.invalid", f"Invalid project metadata: {exc}", relative(path, root))]
    findings = [
        Finding("ERROR", "metadata.schema", issue, relative(path, root))
        for issue in project_metadata.validate_metadata(data, standard_version, source, project_migrations)
    ]
    return data if isinstance(data, dict) else None, findings


def check_capability_core(root: Path, capabilities: Sequence[str]) -> list[Finding]:
    """A capability may require a practice stack to be connected.

    The manifest stores preferences, not membership, so "the section exists" is
    not enough: a section set to optout means the stack was declined, and the
    core of the preset would be missing while looking present.
    """
    required = {
        name: CAPABILITY_REQUIRED_STACK[name]
        for name in capabilities if name in CAPABILITY_REQUIRED_STACK
    }
    if not required:
        return []
    path = root / ".best-practices.json"
    if not path.exists():
        return [Finding(
            "ERROR", "capability.stack_missing",
            f"Capability {', '.join(sorted(required))} requires a Best Practices stack, but .best-practices.json is missing.",
            ".best-practices.json",
            "Record the stack through the Best Practices manifest tooling.",
        )]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        preferences = data["preferences"]
        sections = preferences["sections"]
        if not isinstance(sections, dict):
            raise ValueError("sections must be an object")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return [Finding("ERROR", "capability.stack_unreadable", f"Cannot read Best Practices preferences: {exc}", ".best-practices.json")]

    findings: list[Finding] = []
    for capability, stack in sorted(required.items()):
        # Connected means recorded and not declined. A missing section is not
        # "connected by default": the core would look present while nothing
        # ever chose the stack.
        if stack not in sections:
            findings.append(Finding(
                "ERROR", "capability.stack_missing",
                f"Capability '{capability}' requires the '{stack}' practice stack, which is not recorded.",
                ".best-practices.json",
            ))
        elif sections[stack] == "optout":
            findings.append(Finding(
                "ERROR", "capability.stack_declined",
                f"Capability '{capability}' requires the '{stack}' practice stack, which is set to optout.",
                ".best-practices.json",
            ))
        elif preferences.get("global") == "optout":
            findings.append(Finding(
                "ERROR", "capability.stack_declined",
                f"Capability '{capability}' requires the '{stack}' practice stack, but the whole base is set to optout.",
                ".best-practices.json",
            ))
    return findings


def check_artifacts_ledger(root: Path) -> list[Finding]:
    """Validate the artifacts ledger when a project has one.

    The ledger is optional: only projects that received capability artifacts
    have it. A malformed ledger is an error, because the update workflow reads
    it to tell drift from an untouched artifact.
    """
    path = root / ".project-standard-artifacts.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [Finding("ERROR", "ledger.invalid", f"Invalid artifacts ledger: {exc}", relative(path, root))]
    known_owners = {"standard"} | {f"capability:{name}" for name in project_metadata.CAPABILITY_NAMES}
    return [
        Finding("ERROR", "ledger.schema", issue, relative(path, root))
        for issue in artifacts_ledger.validate_ledger(data, known_owners)
    ]


ONE_C_REGISTRY = "config/1c-projects.tsv"
ONE_C_REGISTRY_FIELDS = (
    "project_id", "environment_id", "folder", "configuration", "platform_version",
    "compatibility_mode", "application_kind", "support_mode", "source_format",
    "edt_workspace", "edt_profile", "toolkit_channel", "is_production", "mcp_enabled", "owner",
)
ONE_C_ENUMS = {
    "application_kind": {"ordinary", "managed"},
    "support_mode": {"on-support", "partially", "off-support"},
    "source_format": {"edt", "designer-xml"},
    "is_production": {"true", "false"},
    "mcp_enabled": {"true", "false"},
}
ONE_C_CHANNEL_RE = project_metadata.ONE_C_TOOLKIT_CHANNEL_RE
ONE_C_REQUIRED = ("project_id", "environment_id", "folder", "configuration")
ONE_C_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


def machine_path(value: str) -> bool:
    """A path that only resolves on the machine that wrote it.

    Both conventions are checked on every host: the repository is prepared on
    macOS and used on Windows, so a check that depends on where it runs would
    let each side through the other's mistake.
    """
    return bool(
        PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
        or DRIVE_PATH_RE.match(value)
        or value.startswith("~")
        or ".." in value.replace("\\", "/").split("/")
    )


def check_one_c_registry(root: Path) -> list[Finding]:
    """The registry of infobases: identity, ports and no credentials.

    Every rule here exists because getting it wrong is expensive at runtime: a
    duplicate identity makes "which base" ambiguous, a shared port sends an
    operation to the wrong infobase, and a credential column would put a
    password into Git.
    """
    path = root / ONE_C_REGISTRY
    if not path.is_file():
        return []
    try:
        # The registry is a TSV people open in a spreadsheet, which is where a
        # BOM comes from; quoting is not a TSV convention, so a value that
        # starts with a quote must stay the value it is.
        text = path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return [Finding("ERROR", "registry.unreadable", f"Cannot read the 1C registry: {exc}", ONE_C_REGISTRY)]

    reader = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    header = tuple(reader.fieldnames or ())
    # The known columns are a prefix, not the whole header: the standard adds
    # columns over time and a project may keep its own after them, and this file
    # belongs to the project, so nothing can rewrite it on upgrade.
    if header[:len(ONE_C_REGISTRY_FIELDS)] != ONE_C_REGISTRY_FIELDS:
        return [Finding(
            "ERROR", "registry.header",
            f"{ONE_C_REGISTRY} header must start with: {', '.join(ONE_C_REGISTRY_FIELDS)}.",
            ONE_C_REGISTRY,
        )]

    findings: list[Finding] = []
    identities: set[tuple[str, str]] = set()
    channels: dict[str, str] = {}
    exposed = 0
    for row in reader:
        where = f"{ONE_C_REGISTRY}:{reader.line_num}"
        if None in row or any(value is None for value in row.values()):
            findings.append(Finding("ERROR", "registry.row", f"{where} does not match the header.", ONE_C_REGISTRY))
            continue

        for column in ONE_C_REQUIRED:
            if not row[column]:
                findings.append(Finding(
                    "ERROR", "registry.value", f"{where} column '{column}' must not be empty.", ONE_C_REGISTRY,
                ))
        for column in ("project_id", "environment_id"):
            # These two become a base name and an MCP namespace downstream, so a
            # space or a slash here breaks routing after installation.
            if row[column] and not ONE_C_ID_RE.fullmatch(row[column]):
                findings.append(Finding(
                    "ERROR", "registry.value",
                    f"{where} column '{column}' must match {ONE_C_ID_RE.pattern}.", ONE_C_REGISTRY,
                ))

        identity = (row["project_id"], row["environment_id"])
        if identity in identities:
            findings.append(Finding(
                "ERROR", "registry.duplicate",
                f"{where} repeats the identity {identity[0]}/{identity[1]}.", ONE_C_REGISTRY,
            ))
        identities.add(identity)

        for column, allowed in ONE_C_ENUMS.items():
            if row[column] not in allowed:
                findings.append(Finding(
                    "ERROR", "registry.value",
                    f"{where} column '{column}' must be one of {', '.join(sorted(allowed))}.", ONE_C_REGISTRY,
                ))

        if row["mcp_enabled"] == "true":
            exposed += 1
            channel = row["toolkit_channel"]
            if not ONE_C_CHANNEL_RE.match(channel):
                findings.append(Finding(
                    "ERROR", "registry.channel",
                    f"{where} exposes MCP and needs a Toolkit channel of 1-64 characters "
                    "from a-z, A-Z, 0-9, '_' or '-'.",
                    ONE_C_REGISTRY,
                ))
            elif channel in channels:
                findings.append(Finding(
                    "ERROR", "registry.channel",
                    f"{where} shares channel {channel} with {channels[channel]}; "
                    "an operation would reach the wrong infobase.",
                    ONE_C_REGISTRY,
                ))
            else:
                channels[channel] = f"{row['project_id']}/{row['environment_id']}"
        elif row["toolkit_channel"]:
            findings.append(Finding(
                "ERROR", "registry.channel",
                f"{where} does not expose MCP, so its Toolkit channel must stay empty.", ONE_C_REGISTRY,
            ))

        for column in ("edt_workspace", "edt_profile", "folder"):
            if row[column] not in ("", "-") and machine_path(row[column]):
                findings.append(Finding(
                    "ERROR", "registry.path",
                    f"{where} column '{column}' must not hold a machine path.", ONE_C_REGISTRY,
                ))

    # The ten-base ceiling went away with the port range (decision 1.8, revised
    # 2026-08-18): one proxy serves every channel, so the number of exposed bases
    # is no longer bounded by the topology. Uniqueness of the channel is checked
    # per row above and remains the thing that keeps an operation from reaching
    # the wrong infobase.
    del exposed
    return findings


def check_capability_evidence(root: Path, capabilities: Sequence[str]) -> list[Finding]:
    """The ledger is the project's own record of what was installed.

    Metadata is a file a person edits; the ledger is written by the delivery
    transaction. If the ledger still owns artifacts of a capability that
    metadata no longer lists, the capability was removed by hand - which the
    standard does not allow.
    """
    path = root / ".project-standard-artifacts.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data["artifacts"]
        if not isinstance(entries, list):
            raise ValueError("artifacts must be an array")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return []  # the ledger check above already reports a broken ledger

    installed = {
        entry["owner"].split(":", 1)[1]
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("owner"), str)
        and entry["owner"].startswith("capability:")
    }
    return [
        Finding(
            "ERROR", "capability.removed",
            f"Capability '{name}' installed artifacts recorded in the ledger but is missing from metadata.",
            ".project-standard.json",
            "A capability cannot be removed from a project; recreate the project instead.",
        )
        for name in sorted(installed - set(capabilities))
    ]


def check_frontmatter(root: Path, files: Sequence[Path], rules_repo: bool) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if path.suffix.lower() != ".md":
            continue
        text = read_text(path)
        if not text or not text.startswith("---\n"):
            continue
        lines = text.splitlines()
        try:
            end = lines.index("---", 1)
        except ValueError:
            findings.append(Finding("ERROR", "frontmatter.unclosed", "Frontmatter is not closed.", relative(path, root)))
            continue
        fields: dict[str, str] = {}
        for line in lines[1:end]:
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
            if match:
                fields[match.group(1)] = match.group(2).strip().strip('"\'')
        rel = relative(path, root)
        skill_frontmatter = any(
            marker in f"/{rel}" for marker in ("/.agents/skills/", "/.claude/skills/", "/.codex/skills/"))
        # A client-owned definition is not one of our documents: an agent or a
        # slash command is delivered byte for byte from upstream and carries the
        # frontmatter its client reads. Demanding `type`/`status` there would
        # require editing vendored payload the release records by hash.
        client_owned = any(
            marker in f"/{rel}"
            for marker in ("/.claude/agents/", "/.codex/agents/", "/.claude/commands/", "/.codex/commands/"))
        if client_owned:
            continue
        required_fields = ("name", "description") if skill_frontmatter else ("type", "status")
        for required in required_fields:
            if not fields.get(required):
                findings.append(Finding("ERROR", "frontmatter.required", f"Missing frontmatter field '{required}'.", relative(path, root)))
        date = fields.get("last_verified")
        in_template = rules_repo and (
            relative(path, root).startswith("templates/new-project/") or path.name == "_TEMPLATE.md"
        )
        if date and not in_template and not ISO_DATE_RE.fullmatch(date):
            findings.append(Finding("ERROR", "frontmatter.date", "last_verified must use YYYY-MM-DD.", relative(path, root)))
    return findings


def check_wikilinks(root: Path, files: Sequence[Path]) -> list[Finding]:
    findings: list[Finding] = []
    markdown = [path for path in files if path.suffix.lower() == ".md"]
    by_stem: dict[str, list[Path]] = {}
    by_stem_attachment: dict[str, list[Path]] = {}
    direct: set[str] = set()
    for path in files:
        rel = relative(path, root)
        direct.add(rel)
        if path.suffix:
            direct.add(rel[: -len(path.suffix)])
        if path.suffix.lower() == ".md":
            by_stem.setdefault(path.stem, []).append(path)
        else:
            by_stem_attachment.setdefault(path.stem, []).append(path)
    for path in markdown:
        text = read_text(path) or ""
        for match in WIKILINK_RE.finditer(text):
            # Obsidian requires escaping the alias pipe as \| inside Markdown tables, so a
            # trailing backslash is syntax rather than part of the target path.
            target = match.group(1).strip().rstrip("\\").replace("\\", "/")
            if target in direct or f"{target}.md" in direct:
                continue
            basename = Path(target).name
            # A note wins over an attachment of the same stem, so linking between notes keeps
            # resolving exactly as before; attachments only answer what notes cannot.
            candidates = by_stem.get(basename) or by_stem_attachment.get(basename, [])
            if len(candidates) == 1:
                continue
            if not candidates:
                findings.append(Finding("ERROR", "wikilink.missing", f"Unresolved wikilink target '{target}'.", relative(path, root)))
            else:
                findings.append(Finding("WARN", "wikilink.ambiguous", f"Ambiguous wikilink target '{target}'.", relative(path, root)))
    return findings


def check_content(root: Path, files: Sequence[Path], rules_repo: bool,
                  byte_exact: frozenset[str] = frozenset()) -> list[Finding]:
    findings: list[Finding] = []
    for memory_path in RAW_MEMORY_PATHS:
        candidate = root.joinpath(*memory_path)
        if candidate.exists():
            findings.append(Finding(
                "ERROR", "memory.raw", "Raw agent memory directory must not be committed to a project.",
                relative(candidate, root), "Keep generated memory local and promote only reviewed knowledge.",
            ))

    for path in files:
        rel = relative(path, root)
        text = read_text(path)
        if text is None:
            continue
        in_template = rules_repo and rel.startswith("templates/new-project/")
        # A byte-exact artifact is delivered as it was written upstream, and the
        # release records its hash: a placeholder-looking token there is their
        # text, not our unsubstituted template, and editing it would break the
        # hash the delivery is verified by.
        if path.suffix.lower() == ".md" and not in_template and rel not in byte_exact:
            for placeholder in PLACEHOLDERS:
                if placeholder in text:
                    findings.append(Finding("ERROR", "placeholder.remaining", f"Template placeholder remains: {placeholder}.", rel))
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        for pattern in LOCAL_PATH_PATTERNS:
            if pattern.search(text):
                findings.append(Finding(
                    "WARN", "path.machine_specific", "Machine-specific absolute path found.", rel,
                    "Use a relative path, environment variable, or documented placeholder.",
                ))
                break
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(Finding(
                    "ERROR", "secret.detected", "Probable secret or private key material found.", rel,
                    "Remove and rotate the credential; document only a placeholder.",
                ))
                break
    return findings


def check_project_structure(
    root: Path,
    rows: Sequence[Artifact],
    profile: str,
) -> list[Finding]:
    findings: list[Finding] = []
    selected = artifacts_for_profile(rows, profile)
    for artifact in selected:
        if not (root / artifact.destination).is_file():
            findings.append(Finding(
                "ERROR", "profile.missing", f"Required {profile} artifact is missing.", artifact.destination,
                "Restore the artifact from the matching new-project-rules template or migration.",
            ))
    claude = root / "CLAUDE.md"
    if claude.is_file() and (read_text(claude) or "").rstrip("\r\n") != "@AGENTS.md":
        findings.append(Finding("ERROR", "claude.import", "CLAUDE.md must contain only '@AGENTS.md'.", "CLAUDE.md"))
    if (root / ".obsidian").exists():
        findings.append(Finding(
            "ERROR", "obsidian.nested_vault", "Project contains a nested .obsidian directory.", ".obsidian",
            "Open the shared parent folder as the vault and remove project-local Obsidian state after review.",
        ))

    index_text = read_text(root / "INDEX.md") or ""
    docs_text = read_text(root / "docs" / "README.md") or ""
    for artifact in selected:
        link_path = re.sub(r"\.md$", "", artifact.destination)
        if artifact.root_purpose != "-" and f"[[{link_path}" not in index_text:
            findings.append(Finding("ERROR", "index.root", f"INDEX.md does not link '{link_path}'.", "INDEX.md"))
        if artifact.docs_section != "-" and f"[[{link_path}" not in docs_text:
            findings.append(Finding("ERROR", "index.docs", f"docs/README.md does not link '{link_path}'.", "docs/README.md"))
    return findings


def check_capabilities(root: Path, rows: Sequence[CapabilityArtifact], capabilities: Sequence[str]) -> list[Finding]:
    findings: list[Finding] = []
    index_text = read_text(root / "INDEX.md") or ""
    docs_text = read_text(root / "docs" / "README.md") or ""
    for artifact in rows:
        if artifact.capability not in capabilities:
            continue
        path = root / artifact.destination
        if not path.is_file():
            findings.append(Finding("ERROR", "capability.missing", f"Required {artifact.capability} artifact is missing.", artifact.destination))
            continue
        link_path = re.sub(r"\.md$", "", artifact.destination)
        if artifact.root_purpose != "-" and f"[[{link_path}" not in index_text:
            findings.append(Finding("ERROR", "capability.index.root", f"INDEX.md does not link '{link_path}'.", "INDEX.md"))
        if artifact.docs_section != "-" and f"[[{link_path}" not in docs_text:
            findings.append(Finding("ERROR", "capability.index.docs", f"docs/README.md does not link '{link_path}'.", "docs/README.md"))
    return findings


def check_policy_contract(root: Path) -> list[Finding]:
    path = root / "config" / "policy-contract.tsv"
    findings: list[Finding] = []
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    except OSError as exc:
        raise ContractError(f"Cannot read {path}: {exc}") from exc
    for row in rows:
        target = root / row.get("file", "")
        literal = row.get("required_literal", "")
        text = read_text(target)
        if text is None or literal not in text:
            findings.append(Finding("ERROR", "policy.literal", f"Required policy literal is missing: {literal!r}.", relative(target, root)))
    return findings


def check_project_baseline(root: Path, contract_root: Path, version: int) -> list[Finding]:
    template = contract_root / "templates" / "new-project" / "AGENTS.template.md"
    template_text = read_text(template)
    if template_text is None:
        return []
    baseline = agent_sync.extract_managed_region(template_text)
    if baseline is None:
        return []
    agents = root / "AGENTS.md"
    if not agents.is_file():
        return []
    try:
        state = agent_sync.inspect_state(baseline, agents, version, template)
    except agent_sync.SyncConfigError:
        return []
    if state.status in {"managed_match", "missing"}:
        return []
    messages = {
        "managed_drift": "Project AGENTS.md baseline drifted from the standard.",
        "unmanaged_conflict": "Project AGENTS.md has no managed markers around the standard baseline.",
        "legacy_exact": "Project AGENTS.md baseline matches the standard but lacks managed markers.",
        "malformed": "Project AGENTS.md managed markers are malformed or duplicated.",
        "unsupported_schema": "Project AGENTS.md managed block schema is unsupported by this rules version.",
    }
    level = "ERROR" if state.status in {"malformed", "unsupported_schema"} else "WARN"
    hint = "Adopt or refresh via plan-migration --target project-agents."
    message = messages.get(state.status, f"Project AGENTS baseline state {state.status}.")
    return [Finding(level, "agents.baseline", message, "AGENTS.md", hint)]


def check_global_rules(contract_root: Path, home: Optional[Path] = None) -> list[Finding]:
    findings: list[Finding] = []
    home = home or Path.home()
    portable = contract_root / "GLOBAL_AGENT_INSTRUCTIONS.md"
    active = home / ".codex" / "AGENTS.md"
    try:
        state = agent_sync.inspect_sync_state(portable, active, agent_sync.read_schema(contract_root))
    except agent_sync.SyncConfigError as exc:
        findings.append(Finding("ERROR", "doctor.sync_config", f"Cannot inspect global policy sync: {exc}"))
        state = None
    if state is not None:
        if state.status == "managed_match":
            findings.append(Finding("INFO", "doctor.global_match", "Managed global policy matches the portable source.", str(active)))
        elif state.status == "legacy_exact":
            findings.append(Finding(
                "WARN", "doctor.global_legacy", "Global policy matches content but has no managed ownership markers.",
                str(active), "Run sync-global-agents --diff to review the marker-only migration plan.",
            ))
        elif state.status == "missing":
            findings.append(Finding(
                "WARN", "doctor.global_missing", "Active ~/.codex/AGENTS.md is missing.", str(active),
                "Run setup-global-agents and review the portable policy before applying it.",
            ))
        elif state.status == "managed_drift":
            findings.append(Finding(
                "WARN", "doctor.global_drift", "Managed global policy differs from the portable source.", str(active),
                "Run sync-global-agents --diff for a secret-safe structural report.",
            ))
        elif state.status == "unmanaged_conflict":
            findings.append(Finding(
                "WARN", "doctor.global_unmanaged_conflict",
                "Unmanaged active policy differs; ownership cannot be inferred safely.", str(active),
                "Review the secret-safe sync diff and choose ownership before any migration.",
            ))
        else:
            findings.append(Finding(
                "ERROR", "doctor.global_markers", f"Global managed policy state is {state.status}: {state.detail}",
                str(active), "Repair markers through a reviewed migration; do not edit around ambiguous boundaries.",
            ))

    claude = home / ".claude" / "CLAUDE.md"
    if claude.exists():
        content = (read_text(claude) or "").rstrip("\r\n")
        if content == "@~/.codex/AGENTS.md":
            findings.append(Finding("INFO", "doctor.claude_import", "Claude global import is configured.", str(claude)))
        else:
            findings.append(Finding(
                "WARN", "doctor.claude_import_invalid", "Claude global instructions are not the canonical one-line import.",
                str(claude), "Review the file before running setup-global-agents.",
            ))
    return findings


def check_doctor_context(root: Path, contract_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    git = shutil.which("git")
    if not git:
        findings.append(Finding("WARN", "doctor.git_missing", "Git diagnostics skipped because git is unavailable."))
    else:
        probe = subprocess.run([git, "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if probe.returncode != 0:
            findings.append(Finding("WARN", "doctor.not_git", "Root is not inside a Git repository.", str(root)))
        else:
            status = subprocess.run([git, "-C", str(root), "status", "--porcelain"], capture_output=True, text=True)
            if status.returncode != 0:
                findings.append(Finding("ERROR", "doctor.git_status", "git status failed.", str(root)))
            elif status.stdout.strip():
                findings.append(Finding(
                    "WARN", "doctor.dirty", "Git working tree contains uncommitted changes.", str(root),
                    "Commit, stash, or review changes before migration or other mutation.",
                ))
            remote = subprocess.run([git, "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True)
            if remote.returncode != 0:
                findings.append(Finding("WARN", "doctor.no_origin", "Git remote 'origin' is not configured.", str(root)))
            else:
                findings.append(Finding("INFO", "doctor.origin", f"origin: {remote.stdout.strip()}", str(root)))

    vault = None
    for parent in (root, *root.parents):
        if (parent / ".obsidian").is_dir():
            vault = parent
            break
    if vault is None:
        findings.append(Finding(
            "WARN", "doctor.vault_unknown", "No parent .obsidian directory was found.", str(root),
            "Confirm that the shared parent folder is opened as the Obsidian vault.",
        ))
    elif vault == root:
        findings.append(Finding("ERROR", "doctor.nested_vault", "The project root is an Obsidian vault.", str(root)))
    else:
        findings.append(Finding("INFO", "doctor.vault", f"Parent Obsidian vault: {vault}", str(root)))
    findings.extend(check_global_rules(contract_root))
    return findings


def validate(
    root: Path,
    contract_root: Path,
    kind: str,
    requested_profile: str,
    doctor: bool = False,
) -> tuple[str, Optional[str], list[Finding]]:
    root = root.resolve()
    contract_root = contract_root.resolve()
    if not root.is_dir():
        raise ContractError(f"Validation root is not a directory: {root}")
    version = load_standard_version(contract_root)
    rows = load_artifacts(contract_root)
    capability_rows = load_capability_artifacts(contract_root)
    try:
        migrations = migration_planner.read_migrations(contract_root, version)
        source = (contract_root / "config" / "standard-source.txt").read_text(encoding="utf-8").strip()
    except (migration_planner.MigrationConfigError, OSError) as exc:
        raise ContractError(f"Invalid migration contract: {exc}") from exc
    if not project_metadata.SOURCE_RE.fullmatch(source):
        raise ContractError("config/standard-source.txt must contain owner/repository")
    project_migrations = [row.migration_id for row in migrations if row.target == "project"]
    if kind == "auto":
        kind = "rules" if (root / "STANDARD_VERSION").is_file() and (root / "config" / "profiles.tsv").is_file() else "project"

    files = list(iter_files(root))
    findings: list[Finding] = []
    profile: Optional[str] = None
    if kind == "rules":
        for required in (
            "README.md", "AGENTS.md", "INDEX.md", "PROJECT.md", "STANDARD_VERSION",
            "config/profiles.tsv", "config/capabilities.tsv", "config/migrations.tsv", "config/standard-source.txt",
        ):
            if not (root / required).is_file():
                findings.append(Finding("ERROR", "rules.required", "Required rules-repository artifact is missing.", required))
        findings.extend(check_policy_contract(root))
        try:
            preset_manifest.read_presets(root)
        except preset_manifest.PresetError as error:
            findings.append(Finding("ERROR", "presets.invalid", str(error), "config/presets.tsv"))
        findings.extend(
            Finding("ERROR", "promotion.candidate", message, path)
            for path, message in promotion_candidates.validate_candidates(root)
        )
    else:
        metadata, metadata_findings = load_metadata(root, version, source, project_migrations)
        findings.extend(metadata_findings)
        findings.extend(check_artifacts_ledger(root))
        metadata_profile = metadata.get("profile") if metadata else None
        if requested_profile != "auto":
            profile = requested_profile
            if metadata_profile and metadata_profile != profile:
                findings.append(Finding(
                    "ERROR", "profile.conflict",
                    f"Requested profile '{profile}' differs from metadata profile '{metadata_profile}'.",
                    ".project-standard.json",
                ))
        elif metadata_profile in PROFILE_RANKS:
            profile = metadata_profile
        else:
            profile = infer_profile(root, rows)
            if profile is None:
                findings.append(Finding(
                    "ERROR", "profile.ambiguous", "Cannot infer an exact profile from known managed artifacts.",
                    "", "Pass --profile explicitly or adopt metadata through a reviewed migration.",
                ))
        if profile:
            findings.extend(check_project_structure(root, rows, profile))
        if metadata:
            findings.extend(check_capabilities(root, capability_rows, metadata.get("capabilities", [])))
            findings.extend(check_capability_core(root, metadata.get("capabilities", [])))
            findings.extend(check_capability_evidence(root, metadata.get("capabilities", [])))
            findings.extend(check_one_c_registry(root))
        findings.extend(check_project_baseline(root, contract_root, version))

    findings.extend(check_frontmatter(root, files, kind == "rules"))
    findings.extend(check_wikilinks(root, files))
    byte_exact = frozenset(row.destination for row in capability_rows
                           if row.payload_class in ("verbatim", "binary"))
    findings.extend(check_content(root, files, kind == "rules", byte_exact))
    if doctor:
        findings.extend(check_doctor_context(root, contract_root))
    return kind, profile, findings


def print_report(root: Path, kind: str, profile: Optional[str], findings: Sequence[Finding]) -> None:
    profile_text = f", profile={profile}" if profile else ""
    print(f"Validation: {root.resolve()} (kind={kind}{profile_text})")
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    for finding in sorted(findings, key=lambda item: (order[item.severity], item.code, item.path, item.message)):
        location = f" {finding.path}:" if finding.path else ":"
        print(f"[{finding.severity}] {finding.code}{location} {finding.message}")
        if finding.fix:
            print(f"        Fix: {finding.fix}")
    counts = {severity: sum(1 for item in findings if item.severity == severity) for severity in order}
    print(f"Summary: {counts['ERROR']} error(s), {counts['WARN']} warning(s), {counts['INFO']} info message(s).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only project contract validator.")
    parser.add_argument("--root", default=".", help="Project or rules-repository root.")
    parser.add_argument("--contract-root", default=str(Path(__file__).resolve().parent.parent), help="new-project-rules root.")
    parser.add_argument("--kind", choices=("auto", "rules", "project"), default="auto")
    parser.add_argument("--profile", choices=("auto", *PROFILE_RANKS), default="auto")
    parser.add_argument("--doctor", action="store_true", help="Include read-only Git and Obsidian diagnostics.")
    parser.add_argument("--report-only", action="store_true", help="Always exit 0 after producing the report.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if sys.version_info < MIN_PYTHON:
        print(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required.", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    try:
        kind, profile, findings = validate(
            Path(args.root), Path(args.contract_root), args.kind, args.profile, args.doctor
        )
    except ContractError as exc:
        print(f"Contract error: {exc}", file=sys.stderr)
        return 0 if args.report_only else 2
    print_report(Path(args.root), kind, profile, findings)
    has_errors = any(item.severity == "ERROR" for item in findings)
    return 0 if args.report_only or not has_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
