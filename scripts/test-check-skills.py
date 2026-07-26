#!/usr/bin/env python3
"""Tests for scripts/check_skills.py.

Each test builds a throwaway repository, so a failure here means the checker
itself regressed, not that this repository drifted.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_skills.py"
spec = importlib.util.spec_from_file_location("check_skills", SCRIPT)
assert spec and spec.loader
check_skills = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_skills)

HEADER = "skill\tclass\troot\tbridge\tpayload_manifest\n"
failures: list[str] = []


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def canonical_skill(root: Path, name: str, *, bridge: bool = True, description: str = "Does a thing.") -> None:
    write(root / ".agents/skills" / name / "SKILL.md", f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n")
    write(root / ".agents/skills" / name / "agents/openai.yaml", 'interface:\n  display_name: "Thing"\n')
    if bridge:
        write(
            root / ".claude/skills" / name / "SKILL.md",
            f"---\nname: {name}\ndescription: {description}\n---\n\nRead ../../../.agents/skills/{name}/SKILL.md\n",
        )


def vendored_skill(root: Path, name: str, files: dict[str, str], *, listed: dict[str, str] | None = None) -> None:
    skill_dir = root / ".agents/skills" / name
    for relative, content in files.items():
        write(skill_dir / relative, content)
    entries = listed if listed is not None else files
    lines = []
    for relative, content in entries.items():
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        lines.append(f"{digest}  {relative}")
    write(skill_dir / "PAYLOAD.sha256", "\n".join(lines) + "\n")


def manifest(root: Path, rows: list[str]) -> None:
    write(root / "config/skills.tsv", HEADER + "".join(row + "\n" for row in rows))


def case(name: str, build, expect: str | None) -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        build(root)
        try:
            found = check_skills.check_all(root)
        except check_skills.ManifestError as error:
            found = [str(error)]
        if expect is None:
            if found:
                failures.append(f"{name}: expected no findings, got {found}")
        elif not any(expect in item for item in found):
            failures.append(f"{name}: expected a finding containing '{expect}', got {found}")


def build_ok(root: Path) -> None:
    canonical_skill(root, "alpha")
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n", "docs/one.md": "one\n"})
    manifest(root, [
        "alpha\tcanonical\t.agents/skills\trequired\t-",
        "vendored\tvendored\t.agents/skills\tnone\tPAYLOAD.sha256",
    ])


def build_missing_bridge(root: Path) -> None:
    canonical_skill(root, "alpha", bridge=False)
    manifest(root, ["alpha\tcanonical\t.agents/skills\trequired\t-"])


def build_bridge_description_drift(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(
        root / ".claude/skills/alpha/SKILL.md",
        "---\nname: alpha\ndescription: Different.\n---\n\nRead ../../../.agents/skills/alpha/SKILL.md\n",
    )
    manifest(root, ["alpha\tcanonical\t.agents/skills\trequired\t-"])


def build_non_ascii_metadata(root: Path) -> None:
    canonical_skill(root, "alpha")
    (root / ".agents/skills/alpha/agents/openai.yaml").write_bytes(b'interface:\n  display_name: "\xcd\xe0\xf1"\n')
    manifest(root, ["alpha\tcanonical\t.agents/skills\trequired\t-"])


def build_vendored_changed(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    (root / ".agents/skills/vendored/SKILL.md").write_text("locally edited\n", encoding="utf-8")
    manifest(root, ["vendored\tvendored\t.agents/skills\tnone\tPAYLOAD.sha256"])


def build_vendored_untracked(root: Path) -> None:
    vendored_skill(
        root,
        "vendored",
        {"SKILL.md": "upstream body\n", "extra.md": "sneaked in\n"},
        listed={"SKILL.md": "upstream body\n"},
    )
    manifest(root, ["vendored\tvendored\t.agents/skills\tnone\tPAYLOAD.sha256"])


def build_vendored_missing_file(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    manifest_path = root / ".agents/skills/vendored/PAYLOAD.sha256"
    digest = hashlib.sha256(b"gone\n").hexdigest()
    manifest_path.write_text(manifest_path.read_text(encoding="utf-8") + f"{digest}  docs/gone.md\n", encoding="utf-8")
    manifest(root, ["vendored\tvendored\t.agents/skills\tnone\tPAYLOAD.sha256"])


def build_vendored_without_manifest_column(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    manifest(root, ["vendored\tvendored\t.agents/skills\tnone\t-"])


def build_unknown_class(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, ["alpha\tmystery\t.agents/skills\trequired\t-"])


def build_duplicate(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [
        "alpha\tcanonical\t.agents/skills\trequired\t-",
        "alpha\tcanonical\t.agents/skills\trequired\t-",
    ])


def build_missing_directory(root: Path) -> None:
    manifest(root, ["ghost\tcanonical\t.agents/skills\trequired\t-"])


case("healthy repository", build_ok, None)
case("missing Claude bridge", build_missing_bridge, "missing .claude/skills/alpha/SKILL.md")
case("bridge description drift", build_bridge_description_drift, "description mismatch")
case("non-ASCII UI metadata", build_non_ascii_metadata, "non-ASCII UI metadata")
case("vendored payload edited", build_vendored_changed, "vendored payload changed")
case("untracked file in vendored subtree", build_vendored_untracked, "untracked file")
case("vendored file missing", build_vendored_missing_file, "missing vendored file")
case("vendored row without payload manifest", build_vendored_without_manifest_column, "needs a payload manifest")
case("unknown class", build_unknown_class, "unknown class")
case("duplicate manifest row", build_duplicate, "duplicate skill")
case("declared skill absent", build_missing_directory, "missing skill directory")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} check_skills test(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All check_skills tests passed.")
