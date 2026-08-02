#!/usr/bin/env python3
"""Tests for scripts/check_skills.py.

Each test builds a throwaway repository, so a failure here means the checker
itself regressed, not that this repository drifted. Fixtures are written as
bytes: text mode would translate newlines on Windows and make recorded hashes
disagree with the files they describe.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import os
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_skills.py"
spec = importlib.util.spec_from_file_location("check_skills", SCRIPT)
assert spec and spec.loader
check_skills = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_skills)

HEADER = "skill\tclass\troot\tbridge\tpayload_manifest\n"
CANONICAL_ROOT = ".agents/skills"
failures: list[str] = []


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def canonical_skill(
    root: Path,
    name: str,
    *,
    bridge: bool = True,
    description: str = "Does a thing.",
    body: str = "",
    bridge_target: str | None = None,
) -> None:
    write(
        root / CANONICAL_ROOT / name / "SKILL.md",
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n{body}",
    )
    write(root / CANONICAL_ROOT / name / "agents/openai.yaml", 'interface:\n  display_name: "Thing"\n')
    if bridge:
        target = bridge_target if bridge_target is not None else f"../../../{CANONICAL_ROOT}/{name}/SKILL.md"
        write(
            root / ".claude/skills" / name / "SKILL.md",
            f"---\nname: {name}\ndescription: {description}\n---\n\nRead {target}\n",
        )


def vendored_skill(root: Path, name: str, files: dict[str, str], *, listed: dict[str, str] | None = None) -> None:
    skill_dir = root / CANONICAL_ROOT / name
    for relative, content in files.items():
        write(skill_dir / relative, content)
    entries = listed if listed is not None else files
    lines = [f"{hashlib.sha256(c.encode('utf-8')).hexdigest()}  {r}" for r, c in entries.items()]
    write(root / "config/skills-payload" / f"{name}.sha256", "\n".join(lines) + "\n")


CAPABILITIES_HEADER = "capability\tsource\tdestination\troot_purpose\tdocs_section\tdocs_label\tpayload_class\n"


def manifest(root: Path, rows: list[str]) -> None:
    write(root / "config/skills.tsv", HEADER + "".join(row + "\n" for row in rows))
    # Coverage reads the capability manifest; fixtures need it unless a test
    # deliberately removes it.
    capabilities = root / "config/capabilities.tsv"
    if not capabilities.is_file():
        write(capabilities, CAPABILITIES_HEADER)


def canonical_row(name: str, bridge: str = "required") -> str:
    return f"{name}\tcanonical\t{CANONICAL_ROOT}\t{bridge}\t-"


def vendored_row(name: str, bridge: str = "none") -> str:
    return f"{name}\tvendored\t{CANONICAL_ROOT}\t{bridge}\tconfig/skills-payload/{name}.sha256"


def case(name: str, build, expect: str | None) -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        try:
            build(root)
        except OSError as error:  # symlink creation may be unavailable
            print(f"SKIP: {name} ({error})")
            return
        try:
            found = check_skills.check_all(root)
        except check_skills.ManifestError as error:
            found = [str(error)]
        if expect is None:
            if found:
                failures.append(f"{name}: expected no findings, got {found}")
        elif not any(expect in item for item in found):
            failures.append(f"{name}: expected a finding containing '{expect}', got {found}")


# --- healthy baseline ------------------------------------------------------

def build_ok(root: Path) -> None:
    canonical_skill(root, "alpha")
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n", "docs/one.md": "one\n"})
    manifest(root, [canonical_row("alpha"), vendored_row("vendored")])


# --- references the skill never opens --------------------------------------

def build_orphan_reference(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(root / CANONICAL_ROOT / "alpha/references/models.md", "# Models\n")
    manifest(root, [canonical_row("alpha")])


def build_linked_reference(root: Path) -> None:
    canonical_skill(root, "alpha", body="\nПодробности — `references/models.md`.\n")
    write(root / CANONICAL_ROOT / "alpha/references/models.md", "# Models\n")
    manifest(root, [canonical_row("alpha")])


case("reference nobody links to", build_orphan_reference, "reference nobody links to")
case("reference the skill points at", build_linked_reference, None)


# --- canonical contract ----------------------------------------------------

def build_missing_bridge(root: Path) -> None:
    canonical_skill(root, "alpha", bridge=False)
    manifest(root, [canonical_row("alpha")])


def build_missing_metadata(root: Path) -> None:
    canonical_skill(root, "alpha")
    (root / CANONICAL_ROOT / "alpha/agents/openai.yaml").unlink()
    manifest(root, [canonical_row("alpha")])


def build_name_mismatch(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(root / CANONICAL_ROOT / "alpha/SKILL.md", "---\nname: beta\ndescription: Does a thing.\n---\n")
    manifest(root, [canonical_row("alpha")])


def build_bridge_name_mismatch(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(
        root / ".claude/skills/alpha/SKILL.md",
        f"---\nname: beta\ndescription: Does a thing.\n---\n\nRead ../../../{CANONICAL_ROOT}/alpha/SKILL.md\n",
    )
    manifest(root, [canonical_row("alpha")])


def build_empty_description(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(root / CANONICAL_ROOT / "alpha/SKILL.md", "---\nname: alpha\n---\n\n# alpha\n")
    manifest(root, [canonical_row("alpha")])


def build_bridge_description_drift(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(
        root / ".claude/skills/alpha/SKILL.md",
        f"---\nname: alpha\ndescription: Different.\n---\n\nRead ../../../{CANONICAL_ROOT}/alpha/SKILL.md\n",
    )
    manifest(root, [canonical_row("alpha")])


def build_todo_in_canonical(root: Path) -> None:
    canonical_skill(root, "alpha", body="\n[TODO: finish me]\n")
    manifest(root, [canonical_row("alpha")])


def build_todo_in_bridge(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(
        root / ".claude/skills/alpha/SKILL.md",
        f"---\nname: alpha\ndescription: Does a thing.\n---\n\n[TODO] Read ../../../{CANONICAL_ROOT}/alpha/SKILL.md\n",
    )
    manifest(root, [canonical_row("alpha")])


def build_bridge_wrong_target(root: Path) -> None:
    canonical_skill(root, "alpha", bridge_target="../../../elsewhere/alpha/SKILL.md")
    manifest(root, [canonical_row("alpha")])


def build_non_ascii_metadata(root: Path) -> None:
    canonical_skill(root, "alpha")
    (root / CANONICAL_ROOT / "alpha/agents/openai.yaml").write_bytes(b'interface:\n  display_name: "\xcd\xe0\xf1"\n')
    manifest(root, [canonical_row("alpha")])


def build_non_utf8_skill(root: Path) -> None:
    canonical_skill(root, "alpha")
    (root / CANONICAL_ROOT / "alpha/SKILL.md").write_bytes(b"---\nname: alpha\ndescription: \xcd\xe0\xf1\n---\n")
    manifest(root, [canonical_row("alpha")])


def build_frontmatter_only(root: Path) -> None:
    canonical_skill(root, "alpha")
    # Fields in the body must not stand in for a missing frontmatter block.
    write(root / CANONICAL_ROOT / "alpha/SKILL.md", "# alpha\n\nname: alpha\ndescription: Does a thing.\n")
    manifest(root, [canonical_row("alpha")])


# --- vendored contract -----------------------------------------------------

def build_vendored_changed(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    write(root / CANONICAL_ROOT / "vendored/SKILL.md", "locally edited\n")
    manifest(root, [vendored_row("vendored")])


def build_vendored_untracked(root: Path) -> None:
    vendored_skill(
        root,
        "vendored",
        {"SKILL.md": "upstream body\n", "extra.md": "sneaked in\n"},
        listed={"SKILL.md": "upstream body\n"},
    )
    manifest(root, [vendored_row("vendored")])


def build_vendored_missing_file(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    payload = root / "config/skills-payload/vendored.sha256"
    digest = hashlib.sha256(b"gone\n").hexdigest()
    write(payload, payload.read_bytes().decode("utf-8") + f"{digest}  docs/gone.md\n")
    manifest(root, [vendored_row("vendored")])


def build_vendored_escaping_path(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    payload = root / "config/skills-payload/vendored.sha256"
    digest = hashlib.sha256(b"secret\n").hexdigest()
    write(payload, payload.read_bytes().decode("utf-8") + f"{digest}  ../../../outside.md\n")
    manifest(root, [vendored_row("vendored")])


def build_vendored_absolute_path(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    payload = root / "config/skills-payload/vendored.sha256"
    digest = hashlib.sha256(b"secret\n").hexdigest()
    write(payload, payload.read_bytes().decode("utf-8") + f"{digest}  /etc/hosts\n")
    manifest(root, [vendored_row("vendored")])


def build_vendored_symlink(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    os.symlink(root / CANONICAL_ROOT / "vendored/SKILL.md", root / CANONICAL_ROOT / "vendored/sneaky.md")
    manifest(root, [vendored_row("vendored")])


def build_vendored_broken_line(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    write(root / "config/skills-payload/vendored.sha256", "not-a-manifest-line\n")
    manifest(root, [vendored_row("vendored")])


def build_vendored_missing_manifest_file(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    (root / "config/skills-payload/vendored.sha256").unlink()
    manifest(root, [vendored_row("vendored")])


# --- manifest contract -----------------------------------------------------

def build_vendored_without_manifest_column(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    manifest(root, [f"vendored\tvendored\t{CANONICAL_ROOT}\tnone\t-"])


def build_canonical_with_payload(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [f"alpha\tcanonical\t{CANONICAL_ROOT}\trequired\tconfig/skills-payload/alpha.sha256"])


def build_unknown_class(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [f"alpha\tmystery\t{CANONICAL_ROOT}\trequired\t-"])


def build_unknown_bridge(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [f"alpha\tcanonical\t{CANONICAL_ROOT}\tmaybe\t-"])


def build_unsafe_root(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, ["alpha\tcanonical\t../outside\trequired\t-"])


def build_bad_header(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(root / "config/skills.tsv", "skill\tclass\troot\n" + f"alpha\tcanonical\t{CANONICAL_ROOT}\n")
    manifest_path = root / "config/skills.tsv"
    assert manifest_path.is_file()


def build_short_row(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(root / "config/skills.tsv", HEADER + f"alpha\tcanonical\t{CANONICAL_ROOT}\n")


def build_duplicate(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [canonical_row("alpha"), canonical_row("alpha")])


def build_empty_manifest(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [])


def build_missing_directory(root: Path) -> None:
    write(root / CANONICAL_ROOT / ".keep", "")
    manifest(root, [canonical_row("ghost")])


def build_blank_line_ignored(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(root / "config/skills.tsv", HEADER + canonical_row("alpha") + "\n\n")
    write(root / "config/capabilities.tsv", CAPABILITIES_HEADER)


# --- coverage --------------------------------------------------------------

def build_undeclared_skill(root: Path) -> None:
    canonical_skill(root, "alpha")
    canonical_skill(root, "ghost", description="Undeclared.")
    manifest(root, [canonical_row("alpha")])


def build_orphan_bridge(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(root / ".claude/skills/orphan/SKILL.md", "---\nname: orphan\ndescription: No owner.\n---\n")
    manifest(root, [canonical_row("alpha")])


def build_capability_skill_undeclared(root: Path) -> None:
    canonical_skill(root, "alpha")
    capability_root = "templates/new-project/capabilities/demo/.agents/skills"
    write(root / capability_root / "demo-skill/SKILL.md", "---\nname: demo-skill\ndescription: Demo.\n---\n")
    write(root / capability_root / "demo-skill/agents/openai.yaml", 'interface:\n  display_name: "Demo"\n')
    manifest(root, [canonical_row("alpha")])
    write(
        root / "config/capabilities.tsv",
        CAPABILITIES_HEADER
        + "demo\tcapabilities/demo/.agents/skills/demo-skill/SKILL.md\t.agents/skills/demo-skill/SKILL.md\t-\t-\t-\ttemplate\n",
    )


case("healthy repository", build_ok, None)
case("missing Claude bridge", build_missing_bridge, "missing .claude/skills/alpha/SKILL.md")
case("missing Codex metadata", build_missing_metadata, "openai.yaml")
case("canonical name mismatch", build_name_mismatch, "name mismatch")
case("bridge name mismatch", build_bridge_name_mismatch, "name mismatch")
case("empty description", build_empty_description, "missing description")
case("bridge description drift", build_bridge_description_drift, "description mismatch")
case("TODO in canonical", build_todo_in_canonical, "TODO remains")
case("TODO in bridge", build_todo_in_bridge, "TODO remains")
case("bridge points elsewhere", build_bridge_wrong_target, "must point at")
case("non-ASCII UI metadata", build_non_ascii_metadata, "non-ASCII UI metadata")
case("non-UTF-8 SKILL.md", build_non_utf8_skill, "not valid UTF-8")
case("fields only in body", build_frontmatter_only, "missing frontmatter block")
case("vendored payload edited", build_vendored_changed, "vendored payload changed")
case("untracked file in vendored subtree", build_vendored_untracked, "untracked file")
case("vendored file missing", build_vendored_missing_file, "missing vendored file")
case("payload path escapes subtree", build_vendored_escaping_path, "unsafe path")
case("payload path is absolute", build_vendored_absolute_path, "unsafe path")
case("symlink inside vendored subtree", build_vendored_symlink, "symlinked file")
case("malformed payload line", build_vendored_broken_line, "expects 'sha256  path'")
case("payload manifest missing", build_vendored_missing_manifest_file, "missing payload manifest")
case("vendored row without payload manifest", build_vendored_without_manifest_column, "needs a payload manifest")
case("canonical row with payload manifest", build_canonical_with_payload, "must not declare a payload manifest")
case("unknown class", build_unknown_class, "unknown class")
case("unknown bridge value", build_unknown_bridge, "unknown bridge")
case("unsafe root", build_unsafe_root, "unsafe root")
case("bad header", build_bad_header, "header must be")
case("row with too few columns", build_short_row, "expects 5 columns")
case("duplicate manifest row", build_duplicate, "duplicate skill")
case("manifest without skills", build_empty_manifest, "declares no skills")
case("declared skill absent", build_missing_directory, "missing skill directory")
case("blank lines are ignored", build_blank_line_ignored, None)
case("undeclared skill directory", build_undeclared_skill, "not declared in")
case("bridge without owner", build_orphan_bridge, "bridge without a declared owner")
case("capability skill not declared", build_capability_skill_undeclared, "not declared in")


# --- cases added after the verification review ----------------------------

def build_payload_backslash_path(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    payload = root / "config/skills-payload/vendored.sha256"
    digest = hashlib.sha256(b"x\n").hexdigest()
    write(payload, payload.read_bytes().decode("utf-8") + f"{digest}  docs\\one.md\n")
    manifest(root, [vendored_row("vendored")])


def build_payload_colon_path(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    payload = root / "config/skills-payload/vendored.sha256"
    digest = hashlib.sha256(b"x\n").hexdigest()
    write(payload, payload.read_bytes().decode("utf-8") + f"{digest}  C:/Windows/win.ini\n")
    manifest(root, [vendored_row("vendored")])


def build_vendored_symlinked_directory(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    write(root / "outside/secret.md", "secret\n")
    os.symlink(root / "outside", root / CANONICAL_ROOT / "vendored/leak")
    manifest(root, [vendored_row("vendored")])


def build_symlink_listed_in_payload(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    write(root / "outside.md", "upstream body\n")
    os.symlink(root / "outside.md", root / CANONICAL_ROOT / "vendored/link.md")
    payload = root / "config/skills-payload/vendored.sha256"
    digest = hashlib.sha256(b"upstream body\n").hexdigest()
    write(payload, payload.read_bytes().decode("utf-8") + f"{digest}  link.md\n")
    manifest(root, [vendored_row("vendored")])


def build_quoted_frontmatter(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(
        root / CANONICAL_ROOT / "alpha/SKILL.md",
        '---\nname: "alpha"\ndescription: "Does a thing."\n---\n\n# alpha\n',
    )
    manifest(root, [canonical_row("alpha")])


def build_field_after_frontmatter(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(
        root / CANONICAL_ROOT / "alpha/SKILL.md",
        "---\nname: alpha\n---\n\ndescription: Does a thing.\n",
    )
    manifest(root, [canonical_row("alpha")])


def build_missing_frontmatter(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(root / CANONICAL_ROOT / "alpha/SKILL.md", "\n---\nname: alpha\ndescription: Does a thing.\n---\n")
    manifest(root, [canonical_row("alpha")])


def build_non_utf8_payload(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    (root / "config/skills-payload/vendored.sha256").write_bytes(b"\xcd\xe0\xf1  SKILL.md\n")
    manifest(root, [vendored_row("vendored")])


def build_non_utf8_manifest(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [canonical_row("alpha")])
    (root / "config/skills.tsv").write_bytes(b"skill\tclass\troot\tbridge\tpayload_manifest\n\xcd\xe0\xf1\n")


def build_missing_manifest(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [canonical_row("alpha")])
    (root / "config/skills.tsv").unlink()


def build_missing_capabilities(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [canonical_row("alpha")])
    (root / "config/capabilities.tsv").unlink()


def build_unsafe_skill_name(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [f"../escape\tcanonical\t{CANONICAL_ROOT}\trequired\t-"])


def build_two_skills_one_bridge(root: Path) -> None:
    canonical_skill(root, "alpha")
    other_root = "templates/new-project/capabilities/demo/.agents/skills"
    write(root / other_root / "alpha/SKILL.md", "---\nname: alpha\ndescription: Does a thing.\n---\n")
    write(root / other_root / "alpha/agents/openai.yaml", 'interface:\n  display_name: "Thing"\n')
    manifest(root, [canonical_row("alpha"), f"alpha\tcanonical\t{other_root}\trequired\t-"])


def build_missing_skill_root(root: Path) -> None:
    canonical_skill(root, "alpha")
    manifest(root, [canonical_row("alpha"), f"beta\tcanonical\ttemplates/absent/skills\tnone\t-"])


def build_vendored_bridge_missing(root: Path) -> None:
    vendored_skill(root, "vendored", {"SKILL.md": "upstream body\n"})
    manifest(root, [vendored_row("vendored", bridge="required")])


def build_tab_only_row(root: Path) -> None:
    canonical_skill(root, "alpha")
    write(root / "config/skills.tsv", HEADER + canonical_row("alpha") + "\n\t\t\t\t\n")
    write(root / "config/capabilities.tsv", CAPABILITIES_HEADER)


case("payload path with backslashes", build_payload_backslash_path, "unsafe path")
case("payload path with a drive letter", build_payload_colon_path, "unsafe path")
case("symlinked directory in vendored subtree", build_vendored_symlinked_directory, "symlinked directory")
case("symlink listed as payload file", build_symlink_listed_in_payload, "missing vendored file")
case("quoted frontmatter values", build_quoted_frontmatter, None)
case("description after the frontmatter block", build_field_after_frontmatter, "missing description")
case("frontmatter not at the top", build_missing_frontmatter, "missing frontmatter block")
case("non-UTF-8 payload manifest", build_non_utf8_payload, "not valid UTF-8")
case("non-UTF-8 skills manifest", build_non_utf8_manifest, "not valid UTF-8")
case("skills manifest missing", build_missing_manifest, "missing manifest")
case("capability manifest missing", build_missing_capabilities, "capability skills cannot be covered")
case("unsafe skill name", build_unsafe_skill_name, "unsafe skill name")
case("two skills claim one bridge", build_two_skills_one_bridge, "claim the bridge")
case("declared root does not exist", build_missing_skill_root, "declared skill root is missing")
case("vendored skill without its bridge", build_vendored_bridge_missing, "missing .claude/skills/vendored/SKILL.md")
case("row of empty fields is ignored", build_tab_only_row, None)


# Findings must read the same on every platform: Windows CI compared them
# against forward-slash paths and failed on backslashes.
with tempfile.TemporaryDirectory() as raw:
    separators = Path(raw)
    build_missing_bridge(separators)
    canonical_skill(separators, "beta", bridge=False)
    write(separators / CANONICAL_ROOT / "gamma/notes.md", "stray\n")
    reported = check_skills.check_all(separators)
    if not reported:
        failures.append("path separators: fixture must produce findings")
    if any("\\" in item for item in reported):
        failures.append(f"path separators: findings must use forward slashes, got {reported}")

# The entry point itself: both wrappers call main(), so its contract is tested.
with tempfile.TemporaryDirectory() as raw:
    healthy = Path(raw)
    build_ok(healthy)
    with contextlib.redirect_stdout(io.StringIO()):
        healthy_code = check_skills.main(["--root", str(healthy)])
    if healthy_code != 0:
        failures.append("main(): healthy repository must exit 0")
with tempfile.TemporaryDirectory() as raw:
    broken = Path(raw)
    build_vendored_changed(broken)
    with contextlib.redirect_stderr(io.StringIO()):
        broken_code = check_skills.main(["--root", str(broken)])
    if broken_code != 1:
        failures.append("main(): findings must exit 1")
with tempfile.TemporaryDirectory() as raw:
    malformed = Path(raw)
    build_unknown_class(malformed)
    with contextlib.redirect_stderr(io.StringIO()):
        malformed_code = check_skills.main(["--root", str(malformed)])
    if malformed_code != 1:
        failures.append("main(): a malformed manifest must exit 1")

# A skill must not name a flag its script does not have. Eight review findings
# had this shape — `--include-memory`, `--mode install`, a note command with no
# executor. A promise the code cannot keep is worse than a missing feature,
# because the reader plans around it.
repository = Path(__file__).resolve().parent.parent
PHANTOM_FLAGS = ("--include-memory", "--mode install")
skill_files = sorted(repository.glob(".agents/skills/*/SKILL.md")) + sorted(
    repository.glob("templates/new-project/capabilities/*/.agents/skills/*/SKILL.md"))
for skill_path in skill_files:
    if "upstream" in skill_path.parts:
        continue  # vendored text is upstream's to shape, not ours
    body = skill_path.read_text(encoding="utf-8")
    for flag in PHANTOM_FLAGS:
        if flag in body:
            failures.append(
                f"{skill_path.relative_to(repository).as_posix()} names {flag}, "
                "which no script implements")

# A test nobody documented is a test nobody runs on purpose. test-standard-metrics
# existed and ran in CI while being absent from both TESTING.md and INDEX.md, so
# the pairing is asserted rather than remembered.
testing = (repository / "docs/quality/TESTING.md").read_text(encoding="utf-8")
index = (repository / "INDEX.md").read_text(encoding="utf-8")
for candidate in sorted((repository / "scripts").glob("test-*.py")):
    name = candidate.name
    if name not in testing:
        failures.append(f"{name} is not documented in docs/quality/TESTING.md")
    if name not in index:
        failures.append(f"{name} is not listed in INDEX.md")

# A capability skill that names a script of the standard must say where that
# script lives: it is in the new-project-rules checkout, not in the created
# project, and the project does not record the path (№215).
CHECKOUT_CAVEAT = "new-project-rules"
for skill_path in sorted(
        repository.glob("templates/new-project/capabilities/*/.agents/skills/*/SKILL.md")):
    if "upstream" in skill_path.parts:
        continue
    body = skill_path.read_text(encoding="utf-8")
    names_script = any(
        marker in body for marker in ("python3 scripts/", "python .\\scripts", "`scripts/"))
    if names_script and CHECKOUT_CAVEAT not in body:
        failures.append(
            f"{skill_path.relative_to(repository).as_posix()} names a script of the standard "
            "without saying it lives in the new-project-rules checkout")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} check_skills test(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All check_skills tests passed.")
