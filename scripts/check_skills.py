#!/usr/bin/env python3
"""Check agent skills declared in config/skills.tsv.

Two classes of skill are checked differently, because they are owned differently:

* ``canonical`` — authored here. The canonical ``SKILL.md``, its Codex discovery
  metadata and (when declared) the Claude bridge must agree.
* ``vendored`` — copied byte for byte from an upstream source. Its inside is not
  ours to shape, so the check is a payload manifest: every listed file matches
  its recorded hash and nothing extra hides in the subtree. The manifest lives
  in ``config/`` rather than inside the subtree: a hash list that sits next to
  the files it guards can be recomputed in the same edit, and the subtree must
  stay byte-identical to upstream.

The manifest is not the only driver: every skill directory found under a known
root must be declared, so a forgotten row fails instead of silently skipping.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import sys
from pathlib import Path, PurePosixPath

MANIFEST = Path("config/skills.tsv")
CAPABILITIES = Path("config/capabilities.tsv")
HEADER = ["skill", "class", "root", "bridge", "payload_manifest"]
CLASSES = ("canonical", "vendored")
BRIDGE_VALUES = ("required", "none")
CANONICAL_ROOT = "agents/skills"
BRIDGE_ROOT = Path(".claude/skills")


class ManifestError(Exception):
    """The manifest itself is malformed; checking cannot start."""


def unsafe_relative(value: str) -> bool:
    """Reject anything that could leave the directory it is relative to."""
    if not value or value in (".", "-"):
        return True
    if value.startswith(("/", "\\")) or "\\" in value or ":" in value:
        return True
    if PurePosixPath(value).is_absolute():
        return True
    return os.path.normpath(value).split(os.sep)[0] == ".."


def read_text(path: Path) -> tuple[str, str]:
    """Return (text, error). Bad encoding is a finding, never a traceback."""
    try:
        return path.read_bytes().decode("utf-8"), ""
    except UnicodeDecodeError:
        return "", f"file is not valid UTF-8: {path}"


def read_manifest(root: Path) -> list[dict[str, str]]:
    path = root / MANIFEST
    if not path.is_file():
        raise ManifestError(f"missing manifest {MANIFEST}")
    text, error = read_text(path)
    if error:
        raise ManifestError(error)
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if reader.fieldnames != HEADER:
        raise ManifestError(f"{MANIFEST} header must be {chr(9).join(HEADER)}")

    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    bridged: set[str] = set()
    for number, row in enumerate(reader, start=2):
        if all(not (value or "").strip() for value in row.values()):
            continue
        if None in row or any(value is None for value in row.values()):
            raise ManifestError(f"{MANIFEST}:{number} expects {len(HEADER)} columns")
        if row["class"] not in CLASSES:
            raise ManifestError(f"{MANIFEST}:{number} unknown class '{row['class']}'")
        if row["bridge"] not in BRIDGE_VALUES:
            raise ManifestError(f"{MANIFEST}:{number} unknown bridge '{row['bridge']}'")
        if unsafe_relative(row["root"]):
            raise ManifestError(f"{MANIFEST}:{number} unsafe root '{row['root']}'")
        if unsafe_relative(row["skill"]) or "/" in row["skill"]:
            raise ManifestError(f"{MANIFEST}:{number} unsafe skill name '{row['skill']}'")
        if row["class"] == "vendored":
            if row["payload_manifest"] == "-" or unsafe_relative(row["payload_manifest"]):
                raise ManifestError(f"{MANIFEST}:{number} vendored skill needs a payload manifest")
        elif row["payload_manifest"] != "-":
            raise ManifestError(f"{MANIFEST}:{number} canonical skill must not declare a payload manifest")
        key = (row["root"], row["skill"])
        if key in seen:
            raise ManifestError(f"{MANIFEST}:{number} duplicate skill '{row['skill']}'")
        seen.add(key)
        if row["bridge"] == "required":
            if row["skill"] in bridged:
                raise ManifestError(f"{MANIFEST}:{number} two skills claim the bridge '{row['skill']}'")
            bridged.add(row["skill"])
        rows.append(row)
    if not rows:
        raise ManifestError(f"{MANIFEST} declares no skills")
    return rows


def has_frontmatter(text: str) -> bool:
    lines = text.splitlines()
    return bool(lines) and lines[0].lstrip("\ufeff").strip() == "---"


def frontmatter_field(text: str, field: str) -> str:
    """Read a field from the leading --- block only, not from the body."""
    if not has_frontmatter(text):
        return ""
    lines = text.splitlines()
    prefix = f"{field}: "
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith(prefix):
            return line[len(prefix):].strip().strip('"').strip("'")
    return ""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iter_files(directory: Path) -> tuple[list[Path], list[str]]:
    """List regular files without following symlinks; symlinks are findings."""
    files: list[Path] = []
    findings: list[str] = []
    for current, subdirectories, names in os.walk(directory, followlinks=False):
        current_path = Path(current)
        for name in list(subdirectories):
            candidate = current_path / name
            if candidate.is_symlink():
                findings.append(f"symlinked directory in vendored skill: {candidate.relative_to(directory)}")
                subdirectories.remove(name)
        for name in names:
            candidate = current_path / name
            if candidate.is_symlink():
                findings.append(f"symlinked file in vendored skill: {candidate.relative_to(directory)}")
                continue
            files.append(candidate)
    return files, findings


def check_document(path: Path, name: str, label: str, root: Path) -> tuple[list[str], str]:
    text, error = read_text(path)
    if error:
        return [error], ""
    failures: list[str] = []
    if not has_frontmatter(text):
        return [f"missing frontmatter block in {path.relative_to(root)}"], ""
    if frontmatter_field(text, "name") != name:
        failures.append(f"name mismatch in {path.relative_to(root)}")
    description = frontmatter_field(text, "description")
    if not description:
        failures.append(f"missing description in {label} of {name}")
    if "TODO" in text:
        failures.append(f"TODO remains in {path.relative_to(root)}")
    return failures, description


def check_bridge(root: Path, row: dict[str, str], description: str) -> list[str]:
    name = row["skill"]
    bridge = root / BRIDGE_ROOT / name / "SKILL.md"
    if not bridge.is_file():
        return [f"missing {bridge.relative_to(root)}"]
    failures, bridge_description = check_document(bridge, name, "bridge", root)
    if description and bridge_description != description:
        failures.append(f"description mismatch between canonical and bridge for {name}")
    text, error = read_text(bridge)
    if not error:
        target = f"../../../{row['root']}/{name}/SKILL.md"
        if target not in text:
            failures.append(f"bridge for {name} must point at {target}")
    return failures


def check_canonical(root: Path, row: dict[str, str]) -> list[str]:
    name = row["skill"]
    skill_dir = root / row["root"] / name
    canonical = skill_dir / "SKILL.md"
    metadata = skill_dir / "agents" / "openai.yaml"
    failures = [f"missing {p.relative_to(root)}" for p in (canonical, metadata) if not p.is_file()]
    if failures:
        return failures

    document_failures, description = check_document(canonical, name, "canonical", root)
    failures.extend(document_failures)
    # Bytes, not text: metadata in a legacy encoding must fail the ASCII
    # contract instead of crashing the checker.
    if not metadata.read_bytes().isascii():
        failures.append(f"non-ASCII UI metadata in {metadata.relative_to(root)}")
    if row["bridge"] == "required":
        failures.extend(check_bridge(root, row, description))
    return failures


def check_vendored(root: Path, row: dict[str, str]) -> list[str]:
    name = row["skill"]
    skill_dir = root / row["root"] / name
    payload = root / row["payload_manifest"]
    if not payload.is_file():
        return [f"missing payload manifest {row['payload_manifest']}"]
    text, error = read_text(payload)
    if error:
        return [error]

    failures: list[str] = []
    listed: set[Path] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        expected, separator, relative = line.partition("  ")
        if not separator or not relative.strip():
            failures.append(f"{row['payload_manifest']}:{number} expects 'sha256  path'")
            continue
        relative = relative.strip()
        if unsafe_relative(relative):
            failures.append(f"{row['payload_manifest']}:{number} unsafe path '{relative}'")
            continue
        target = skill_dir / relative
        listed.add(target)
        if target.is_symlink() or not target.is_file():
            failures.append(f"missing vendored file {relative} in {name}")
            continue
        if sha256(target) != expected:
            failures.append(f"vendored payload changed: {relative} in {name}")

    present, symlink_findings = iter_files(skill_dir)
    failures.extend(f"{finding} ({name})" for finding in symlink_findings)
    for candidate in sorted(present):
        if candidate not in listed:
            failures.append(f"untracked file in vendored skill {name}: {candidate.relative_to(skill_dir)}")
    if row["bridge"] == "required":
        failures.extend(check_bridge(root, row, ""))
    return failures


def capability_skill_roots(root: Path) -> tuple[set[str], list[str]]:
    """Skill roots implied by config/capabilities.tsv, so the two agree.

    An unreadable capability manifest is a finding: silently returning nothing
    would drop capability skills out of the coverage check.
    """
    path = root / CAPABILITIES
    roots: set[str] = set()
    if not path.is_file():
        return roots, [f"missing {CAPABILITIES}: capability skills cannot be covered"]
    text, error = read_text(path)
    if error:
        return roots, [error]
    for row in csv.DictReader(io.StringIO(text), delimiter="\t"):
        source = (row.get("source") or "").strip()
        marker = f"/.{CANONICAL_ROOT}/"
        if marker in source:
            prefix = source.split(marker)[0]
            roots.add(f"templates/new-project/{prefix}/.{CANONICAL_ROOT}")
    return roots, []


def check_coverage(root: Path, rows: list[dict[str, str]]) -> list[str]:
    declared = {(row["root"], row["skill"]) for row in rows}
    failures: list[str] = []

    capability_roots, capability_failures = capability_skill_roots(root)
    failures.extend(capability_failures)
    roots = {row["root"] for row in rows} | {f".{CANONICAL_ROOT}"} | capability_roots
    for skill_root in sorted(roots):
        directory = root / skill_root
        if not directory.is_dir():
            failures.append(f"declared skill root is missing: {skill_root}")
            continue
        for candidate in sorted(directory.iterdir()):
            if candidate.is_dir() and (skill_root, candidate.name) not in declared:
                failures.append(f"skill is not declared in {MANIFEST}: {skill_root}/{candidate.name}")

    bridges = {row["skill"] for row in rows if row["bridge"] == "required"}
    bridge_directory = root / BRIDGE_ROOT
    if bridge_directory.is_dir():
        for candidate in sorted(bridge_directory.iterdir()):
            if candidate.is_dir() and candidate.name not in bridges:
                failures.append(f"Claude bridge without a declared owner: {BRIDGE_ROOT}/{candidate.name}")
    return failures


def check_all(root: Path) -> list[str]:
    rows = read_manifest(root)
    failures: list[str] = []
    for row in rows:
        skill_dir = root / row["root"] / row["skill"]
        if not skill_dir.is_dir():
            failures.append(f"missing skill directory {row['root']}/{row['skill']}")
            continue
        if row["class"] == "canonical":
            failures.extend(check_canonical(root, row))
        else:
            failures.extend(check_vendored(root, row))
    failures.extend(check_coverage(root, rows))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check declared agent skills.")
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        failures = check_all(root)
    except ManifestError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        print(f"{len(failures)} skill check(s) failed.", file=sys.stderr)
        return 1
    print("All declared skills passed their checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
