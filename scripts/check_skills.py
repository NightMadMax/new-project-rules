#!/usr/bin/env python3
"""Check agent skills declared in config/skills.tsv.

Two classes of skill are checked differently, because they are owned differently:

* ``canonical`` — authored in this repository. The canonical ``SKILL.md``, its
  Codex discovery metadata and (when declared) the Claude bridge must agree.
* ``vendored`` — copied byte for byte from an upstream source. Its inside is not
  ours to shape, so the check is a payload manifest: every listed file matches
  its recorded hash and nothing extra hides in the subtree. Discovery metadata
  and bridges live outside such a subtree and are not required within it.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

MANIFEST = Path("config/skills.tsv")
HEADER = ("skill", "class", "root", "bridge", "payload_manifest")
CLASSES = ("canonical", "vendored")
BRIDGE_VALUES = ("required", "none")
BRIDGE_ROOT = Path(".claude/skills")


class ManifestError(Exception):
    """The manifest itself is malformed; checking cannot start."""


def read_manifest(root: Path) -> list[dict[str, str]]:
    path = root / MANIFEST
    if not path.is_file():
        raise ManifestError(f"missing manifest {MANIFEST}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ManifestError(f"empty manifest {MANIFEST}")
    header = tuple(lines[0].split("\t"))
    if header != HEADER:
        raise ManifestError(f"{MANIFEST} header must be {chr(9).join(HEADER)}")
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != len(HEADER):
            raise ManifestError(f"{MANIFEST}:{number} expects {len(HEADER)} columns")
        row = dict(zip(HEADER, fields))
        if row["class"] not in CLASSES:
            raise ManifestError(f"{MANIFEST}:{number} unknown class '{row['class']}'")
        if row["bridge"] not in BRIDGE_VALUES:
            raise ManifestError(f"{MANIFEST}:{number} unknown bridge '{row['bridge']}'")
        if row["class"] == "vendored" and row["payload_manifest"] == "-":
            raise ManifestError(f"{MANIFEST}:{number} vendored skill needs a payload manifest")
        key = (row["root"], row["skill"])
        if key in seen:
            raise ManifestError(f"{MANIFEST}:{number} duplicate skill '{row['skill']}'")
        seen.add(key)
        rows.append(row)
    return rows


def first_field(text: str, field: str) -> str:
    prefix = f"{field}: "
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def check_canonical(root: Path, row: dict[str, str]) -> list[str]:
    name = row["skill"]
    skill_dir = root / row["root"] / name
    canonical = skill_dir / "SKILL.md"
    metadata = skill_dir / "agents" / "openai.yaml"
    failures: list[str] = []

    for required in (canonical, metadata):
        if not required.is_file():
            failures.append(f"missing {required.relative_to(root)}")
    if failures:
        return failures

    text = canonical.read_text(encoding="utf-8")
    if first_field(text, "name") != name:
        failures.append(f"name mismatch in {canonical.relative_to(root)}")
    description = first_field(text, "description")
    if not description:
        failures.append(f"missing description in {canonical.relative_to(root)}")
    if "TODO" in text:
        failures.append(f"TODO remains in {canonical.relative_to(root)}")
    # Read bytes: metadata that is not valid UTF-8 must fail the ASCII check,
    # not crash the checker.
    if not metadata.read_bytes().isascii():
        failures.append(f"non-ASCII UI metadata in {metadata.relative_to(root)}")

    if row["bridge"] == "required":
        bridge = root / BRIDGE_ROOT / name / "SKILL.md"
        if not bridge.is_file():
            return failures + [f"missing {bridge.relative_to(root)}"]
        bridge_text = bridge.read_text(encoding="utf-8")
        if first_field(bridge_text, "name") != name:
            failures.append(f"name mismatch in {bridge.relative_to(root)}")
        if first_field(bridge_text, "description") != description:
            failures.append(f"description mismatch between canonical and bridge for {name}")
        if "TODO" in bridge_text:
            failures.append(f"TODO remains in {bridge.relative_to(root)}")
        target = f"../../../{row['root']}/{name}/SKILL.md"
        if target not in bridge_text:
            failures.append(f"bridge for {name} must point at {target}")
    return failures


def check_vendored(root: Path, row: dict[str, str]) -> list[str]:
    name = row["skill"]
    skill_dir = root / row["root"] / name
    payload = skill_dir / row["payload_manifest"]
    if not payload.is_file():
        return [f"missing payload manifest {payload.relative_to(root)}"]

    failures: list[str] = []
    listed: set[Path] = set()
    for number, line in enumerate(payload.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            expected, relative = line.split("  ", 1)
        except ValueError:
            failures.append(f"{payload.relative_to(root)}:{number} expects 'sha256  path'")
            continue
        target = skill_dir / relative
        listed.add(target.resolve())
        if not target.is_file():
            failures.append(f"missing vendored file {relative} in {name}")
            continue
        if sha256(target) != expected:
            failures.append(f"vendored payload changed: {relative} in {name}")

    listed.add(payload.resolve())
    for present in sorted(skill_dir.rglob("*")):
        if present.is_file() and present.resolve() not in listed:
            failures.append(f"untracked file in vendored skill {name}: {present.relative_to(skill_dir)}")
    return failures


def check_all(root: Path) -> list[str]:
    failures: list[str] = []
    for row in read_manifest(root):
        skill_dir = root / row["root"] / row["skill"]
        if not skill_dir.is_dir():
            failures.append(f"missing skill directory {skill_dir.relative_to(root)}")
            continue
        if row["class"] == "canonical":
            failures.extend(check_canonical(root, row))
        else:
            failures.extend(check_vendored(root, row))
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
