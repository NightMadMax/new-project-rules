#!/usr/bin/env python3
"""Tests for scripts/capability_artifacts.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("capability_artifacts", SCRIPTS / "capability_artifacts.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
# Dataclasses resolve annotations through sys.modules, so register before exec.
sys.modules["capability_artifacts"] = module
spec.loader.exec_module(module)

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def release(
    root: Path,
    files: dict[str, bytes],
    payload_class: str = "verbatim",
    policy: str = "managed",
) -> list[tuple[str, Path, str, str]]:
    source_root = root / "release"
    artifacts = []
    for target, content in files.items():
        source = source_root / target
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(content)
        artifacts.append((target, source, payload_class, policy))
    return artifacts


def ledger_of(project: Path) -> dict:
    path = project / module.LEDGER_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"artifacts": []}


def scenario(name: str):
    def decorate(function):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            project = root / "project"
            project.mkdir()
            try:
                function(root, project)
            except AssertionError as error:
                failures.append(f"{name}: {error}")
            except Exception as error:  # noqa: BLE001 - a crash is a failure too
                failures.append(f"{name}: unexpected {type(error).__name__}: {error}")
        return function
    return decorate


@scenario("clean install")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"config/a.json": b"one\n", "tools/bin.epf": b"\xff\xfe\x00"})
    plan = module.build_plan(project, "1c", artifacts)
    note(plan.status == "ready", f"expected ready, got {plan.status}")
    module.apply_plan(project, plan)
    note((project / "config/a.json").read_bytes() == b"one\n", "content was not delivered")
    note((project / "tools/bin.epf").read_bytes() == b"\xff\xfe\x00", "binary content was rewritten")
    entries = ledger_of(project)["artifacts"]
    note(len(entries) == 2, f"ledger must record both artifacts, got {entries}")
    note(all(entry["owner"] == "capability:1c" for entry in entries), "owner is wrong")

    repeat = module.build_plan(project, "1c", artifacts)
    note(repeat.status == "up_to_date", f"second plan must be a no-op, got {repeat.status}")


@scenario("update and removal")
def _(root: Path, project: Path) -> None:
    first = release(root, {"config/a.json": b"one\n", "config/gone.json": b"bye\n"})
    module.apply_plan(project, module.build_plan(project, "1c", first))

    second_root = root / "next"
    second = release(second_root, {"config/a.json": b"two\n"})
    plan = module.build_plan(project, "1c", second)
    actions = {operation.target: operation.action for operation in plan.operations}
    note(actions.get("config/a.json") == "update", f"expected update, got {actions}")
    note(actions.get("config/gone.json") == "remove", f"expected removal, got {actions}")
    module.apply_plan(project, plan)
    note((project / "config/a.json").read_bytes() == b"two\n", "update did not land")
    note(not (project / "config/gone.json").exists(), "removed artifact is still there")
    note(len(ledger_of(project)["artifacts"]) == 1, "ledger still lists the removed artifact")


@scenario("drift blocks")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"config/a.json": b"one\n"})
    module.apply_plan(project, module.build_plan(project, "1c", artifacts))
    (project / "config/a.json").write_bytes(b"user edit\n")

    next_release = release(root / "next", {"config/a.json": b"two\n"})
    plan = module.build_plan(project, "1c", next_release)
    note(plan.status == "conflict", f"drift must be a conflict, got {plan.status}")
    note(any("changed after installation" in item for item in plan.conflicts), f"unclear conflict: {plan.conflicts}")
    try:
        module.apply_plan(project, plan)
        failures.append("drift blocks: apply must refuse a conflicting plan")
    except module.CapabilityArtifactsError:
        pass
    note((project / "config/a.json").read_bytes() == b"user edit\n", "the user's edit was overwritten")


@scenario("deletion of a managed artifact is a conflict")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"config/a.json": b"one\n"})
    module.apply_plan(project, module.build_plan(project, "1c", artifacts))
    (project / "config/a.json").unlink()
    plan = module.build_plan(project, "1c", artifacts)
    note(plan.status == "conflict", f"deletion must be a conflict, got {plan.status}")


@scenario("foreign file is not adopted")
def _(root: Path, project: Path) -> None:
    (project / "config").mkdir()
    (project / "config/a.json").write_bytes(b"someone else\n")
    artifacts = release(root, {"config/a.json": b"one\n"})
    plan = module.build_plan(project, "1c", artifacts)
    note(plan.status == "conflict", f"foreign file must be a conflict, got {plan.status}")
    note((project / "config/a.json").read_bytes() == b"someone else\n", "foreign file was touched")


@scenario("seed is created once and then owned by the user")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"USER-RULES.md": b"# rules\n"}, payload_class="template", policy="seed")
    plan = module.build_plan(project, "1c", artifacts)
    note(plan.operations[0].policy == "seed", "policy must come from the manifest")
    module.apply_plan(project, plan)
    (project / "USER-RULES.md").write_bytes(b"# my own rules\n")

    changed = release(root / "next", {"USER-RULES.md": b"# rules v2\n"}, payload_class="template", policy="seed")
    repeat = module.build_plan(project, "1c", changed)
    note(repeat.status == "up_to_date", f"a seed must not be updated, got {repeat.status}")
    module.apply_plan(project, repeat)
    note((project / "USER-RULES.md").read_bytes() == b"# my own rules\n", "seed was overwritten")
    entry = ledger_of(project)["artifacts"][0]
    note(entry["policy"] == "seed" and entry["hash"] is None, f"seed entry is wrong: {entry}")


@scenario("a seed is never removed")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"memory.md": b"# memory\n"}, payload_class="template", policy="seed")
    module.apply_plan(project, module.build_plan(project, "1c", artifacts))
    plan = module.build_plan(project, "1c", [])
    note(plan.status in ("ready", "up_to_date"), f"dropping a seed must not be a conflict, got {plan.status}")
    note(all(operation.action != "remove" for operation in plan.operations), "a seed was scheduled for removal")
    module.apply_plan(project, plan)
    note((project / "memory.md").exists(), "seed was removed")
    entries = ledger_of(project)["artifacts"]
    note([entry["target"] for entry in entries] == ["memory.md"], f"seed left the ledger: {entries}")


@scenario("failure in the middle rolls the whole chain back")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"config/a.json": b"one\n", "config/b.json": b"two\n"})
    module.apply_plan(project, module.build_plan(project, "1c", artifacts))
    before = {path.name: path.read_bytes() for path in (project / "config").iterdir()}

    next_release = release(root / "next", {"config/a.json": b"one-new\n", "config/b.json": b"two-new\n"})
    plan = module.build_plan(project, "1c", next_release)
    # The second source disappears between planning and applying.
    dict(zip([item[0] for item in next_release], [item[1] for item in next_release]))["config/b.json"].unlink()
    try:
        module.apply_plan(project, plan)
        failures.append("rollback: apply must fail when a source disappears")
    except module.CapabilityArtifactsError:
        pass
    after = {path.name: path.read_bytes() for path in (project / "config").iterdir() if not path.name.startswith(".")}
    note(after == before, f"project was left half-updated: {after}")


@scenario("a failed rename restores what already landed")
def _(root: Path, project: Path) -> None:
    first = release(root, {"a.txt": b"one\n", "b.txt": b"two\n"})
    module.apply_plan(project, module.build_plan(project, "1c", first))
    before = {path.name: path.read_bytes() for path in project.iterdir()
              if path.is_file() and not path.name.startswith(".")}

    second = release(root / "next", {"a.txt": b"one-new\n", "b.txt": b"two-new\n"})
    plan = module.build_plan(project, "1c", second)

    real_replace = module.os.replace

    def flaky(source, target, *args, **kwargs):
        # Fail when the second payload is moved into place, after the first
        # one has already landed.
        if str(source).endswith(".b.txt.capability-artifacts"):
            raise OSError("simulated failure during rename")
        return real_replace(source, target, *args, **kwargs)

    module.os.replace = flaky
    try:
        module.apply_plan(project, plan)
        failures.append("rename rollback: apply must fail")
    except module.CapabilityArtifactsError:
        pass
    finally:
        module.os.replace = real_replace

    after = {path.name: path.read_bytes() for path in project.iterdir()
             if path.is_file() and not path.name.startswith(".")}
    note(after == before, f"a failed rename left the project half-updated: {after}")
    leftovers = [path.name for path in project.iterdir() if path.name.startswith(".") and "capability-artifacts" in path.name]
    note(not leftovers, f"temporary files were left behind: {leftovers}")


@scenario("a template rendered by bootstrap is recorded, not recreated")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"JIRA.md": b"# <PROJECT_NAME>\n"}, payload_class="template")
    plan = module.build_plan(project, "1c", artifacts)
    note(plan.status == "conflict", f"a missing rendered template must be a conflict, got {plan.status}")

    (project / "JIRA.md").write_bytes(b"# demo\n")
    plan = module.build_plan(project, "1c", artifacts)
    note(plan.operations[0].action == "adopt", f"a rendered template must be adopted, got {plan.operations[0].action}")
    module.apply_plan(project, plan)
    note((project / "JIRA.md").read_bytes() == b"# demo\n", "the rendered file was overwritten")

    changed = release(root / "next", {"JIRA.md": b"# <PROJECT_NAME> v2\n"}, payload_class="template")
    note(module.build_plan(project, "1c", changed).status == "up_to_date", "a rendered template must not be updated")


@scenario("declared duplicates and missing sources stop planning")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"a.txt": b"one\n"})
    try:
        module.build_plan(project, "1c", artifacts + artifacts)
        failures.append("duplicate target was accepted")
    except module.CapabilityArtifactsError:
        pass

    artifacts[0][1].unlink()
    try:
        module.build_plan(project, "1c", artifacts)
        failures.append("missing source was accepted")
    except module.CapabilityArtifactsError:
        pass


@scenario("an unknown payload class stops planning")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"a.txt": b"one\n"}, payload_class="mystery")
    try:
        module.build_plan(project, "1c", artifacts)
        failures.append("unknown payload class was accepted")
    except module.CapabilityArtifactsError:
        pass


@scenario("an unknown policy stops planning")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"a.txt": b"one\n"}, policy="mystery")
    try:
        module.build_plan(project, "1c", artifacts)
        failures.append("unknown policy was accepted")
    except module.CapabilityArtifactsError:
        pass


@scenario("a change between planning and applying is refused")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"a.txt": b"one\n"})
    module.apply_plan(project, module.build_plan(project, "1c", artifacts))
    next_release = release(root / "next", {"a.txt": b"two\n"})
    plan = module.build_plan(project, "1c", next_release)
    (project / "a.txt").write_bytes(b"user edit after planning\n")
    try:
        module.apply_plan(project, plan)
        failures.append("stale plan: apply must refuse")
    except module.CapabilityArtifactsError:
        pass
    note((project / "a.txt").read_bytes() == b"user edit after planning\n", "a late edit was overwritten")


@scenario("a corrupted staged copy stops the apply")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"a.txt": b"one\n"})
    plan = module.build_plan(project, "1c", artifacts)
    real_copy = module.shutil.copyfile

    def wrong_copy(source, target, *args, **kwargs):
        Path(target).write_bytes(b"corrupted\n")

    module.shutil.copyfile = wrong_copy
    try:
        module.apply_plan(project, plan)
        failures.append("staged check: apply must refuse a copy that does not match")
    except module.CapabilityArtifactsError:
        pass
    finally:
        module.shutil.copyfile = real_copy
    note(not (project / "a.txt").exists(), "a corrupted copy was left in place")


@scenario("removal is refused when the file changed")
def _(root: Path, project: Path) -> None:
    first = release(root, {"a.txt": b"one\n", "gone.txt": b"bye\n"})
    module.apply_plan(project, module.build_plan(project, "1c", first))
    (project / "gone.txt").write_bytes(b"user made it theirs\n")
    second = release(root / "next", {"a.txt": b"one\n"})
    plan = module.build_plan(project, "1c", second)
    note(plan.status == "conflict", f"changed file must not be removed, got {plan.status}")
    note((project / "gone.txt").exists(), "the changed file was removed")


@scenario("a ledger that would be invalid stops before files move")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"a.txt": b"one\n"})
    plan = module.build_plan(project, "1c", artifacts)
    broken = module.Plan(plan.capability, plan.status, tuple(
        module.Operation(
            operation.target, operation.action, operation.policy, "mystery",
            operation.owner, operation.source, operation.desired_hash,
            operation.installed_hash, operation.detail,
        ) for operation in plan.operations
    ))
    try:
        module.apply_plan(project, broken)
        failures.append("invalid ledger: apply must refuse")
    except module.CapabilityArtifactsError:
        pass
    note(not (project / "a.txt").exists(), "files moved before the ledger was validated")


@scenario("a target inside .git is rejected")
def _(root: Path, project: Path) -> None:
    source = root / "release" / "hook"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"#!/bin/sh\n")
    try:
        module.build_plan(project, "1c", [(".git/hooks/pre-commit", source, "verbatim", "managed")])
        failures.append("a target inside .git was accepted")
    except module.CapabilityArtifactsError:
        pass


@scenario("other owners are preserved")
def _(root: Path, project: Path) -> None:
    (project / module.LEDGER_NAME).write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{
            "target": "docs/other.md", "owner": "standard", "policy": "managed",
            "payload_class": "template", "hash": "sha256:" + "0" * 64,
        }],
    }), encoding="utf-8")
    artifacts = release(root, {"config/a.json": b"one\n"})
    module.apply_plan(project, module.build_plan(project, "1c", artifacts))
    owners = {entry["owner"] for entry in ledger_of(project)["artifacts"]}
    note(owners == {"standard", "capability:1c"}, f"another owner was dropped: {owners}")


@scenario("unsafe target is rejected")
def _(root: Path, project: Path) -> None:
    source = root / "release" / "escape"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"x")
    for target in ("../escape.md", "/etc/hosts", "config/../../escape.md"):
        try:
            module.build_plan(project, "1c", [(target, source, "verbatim", "managed")])
            failures.append(f"unsafe target accepted: {target}")
        except module.CapabilityArtifactsError:
            pass


@scenario("an invalid ledger stops planning")
def _(root: Path, project: Path) -> None:
    (project / module.LEDGER_NAME).write_text('{"schema_version": 99, "artifacts": []}', encoding="utf-8")
    artifacts = release(root, {"config/a.json": b"one\n"})
    try:
        module.build_plan(project, "1c", artifacts)
        failures.append("invalid ledger: planning must stop")
    except module.CapabilityArtifactsError:
        pass


@scenario("capability added to an existing project")
def _(root: Path, project: Path) -> None:
    # A seed template used to be refused here, so a capability could only ever
    # be chosen while creating the project (№223). The values are read from the
    # project, not invented: name and schema from its own metadata, date today.
    (project / ".project-standard.json").write_bytes(
        json.dumps({"project_name": "demo", "schema_version": 5}).encode("utf-8"))
    artifacts = release(root, {"USER-RULES.md": "# Правила <PROJECT_NAME>\n".encode("utf-8")},
                        payload_class="template", policy="seed")
    plan = module.build_plan(project, "1c", artifacts)
    note(plan.status == "ready", f"a seed template must be creatable: {plan.status}, {plan.conflicts}")
    module.apply_plan(project, plan)
    body = (project / "USER-RULES.md").read_text(encoding="utf-8")
    note("demo" in body and "<PROJECT_NAME>" not in body, f"the seed was not rendered: {body!r}")


@scenario("a project that does not state its schema refuses rather than guesses")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"AGENTS.md": b"schema=<SCHEMA_VERSION>\n"},
                        payload_class="template", policy="seed")
    plan = module.build_plan(project, "1c", artifacts)
    note(plan.status != "ready", "a missing value must not be written as a guess")
    note(any("SCHEMA_VERSION" in item for item in plan.conflicts),
         f"the conflict must name the value it lacks: {plan.conflicts}")


# --- the record travels with the files (№242) -------------------------------


@scenario("project records ride in the same transaction as the artifacts")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"docs/GUIDE.md": b"guide\n"})
    plan = module.build_plan(project, "1c", artifacts)
    plan = module.with_documents(plan, [("INDEX.md", b"# Index\n\n| a | b |\n")])
    note(plan.status == "ready", f"documents must be work to do: {plan.status}")
    note("record: 1" in plan.summary(), f"the summary must count records: {plan.summary()}")
    module.apply_plan(project, plan)
    note((project / "INDEX.md").read_bytes() == b"# Index\n\n| a | b |\n", "the record was not written")
    note((project / "docs/GUIDE.md").is_file(), "the artifact was not written")
    # The project owns these files, so the capability must not claim them.
    targets = {entry["target"] for entry in ledger_of(project)["artifacts"]}
    note("INDEX.md" not in targets, f"a project record must not enter the ledger: {targets}")


@scenario("a record with nothing to deliver is still an install")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"docs/GUIDE.md": b"guide\n"})
    module.apply_plan(project, module.build_plan(project, "1c", artifacts))
    plan = module.build_plan(project, "1c", artifacts)
    note(plan.status == "up_to_date", f"a second run must be a no-op: {plan.status}")
    plan = module.with_documents(plan, [(".project-standard.json", b"{}\n")])
    note(plan.status == "ready",
         "a capability whose files are in place and whose record is not is not up to date")


@scenario("a project record edited after planning stops the apply")
def _(root: Path, project: Path) -> None:
    # These bodies are built *from* the current file — one line added to an
    # index — so applying an old plan silently discards whatever the user wrote
    # in between. Capability files stop the transaction on exactly this; the
    # records they ride with did not.
    artifacts = release(root, {"docs/GUIDE.md": b"guide\n"})
    (project / "INDEX.md").write_bytes(b"# Index\n\n| a | b |\n")
    plan = module.build_plan(project, "1c", artifacts)
    plan = module.with_documents(plan, [("INDEX.md", b"# Index\n\n| a | b |\n| new | row |\n")], project)
    (project / "INDEX.md").write_bytes(b"# Index\n\n| a | b |\n| the user wrote this |\n")
    try:
        module.apply_plan(project, plan)
        failures.append("a record edited between plan and apply must not be overwritten")
    except module.CapabilityArtifactsError as error:
        note("changed after planning" in str(error), f"the refusal must say why: {error}")
    note(b"the user wrote this" in (project / "INDEX.md").read_bytes(),
         "the edit must survive the refused apply")
    note(not (project / "docs/GUIDE.md").exists(),
         "a refused apply must leave no artifacts behind")


@scenario("adopting a file that changed after planning is refused")
def _(root: Path, project: Path) -> None:
    # Adopt records the release hash for a file bootstrap already delivered.
    # Without a precondition it recorded that hash for whatever the file had
    # become in between — a state the project was never in.
    artifacts = release(root, {"docs/GUIDE.md": b"guide\n"})
    (project / "docs").mkdir(parents=True, exist_ok=True)
    (project / "docs/GUIDE.md").write_bytes(b"guide\n")
    plan = module.build_plan(project, "1c", artifacts)
    note(any(operation.action == "adopt" for operation in plan.operations),
         f"matching bytes must plan as adopt: {[o.action for o in plan.operations]}")
    (project / "docs/GUIDE.md").write_bytes(b"edited by the user\n")
    try:
        module.apply_plan(project, plan)
        failures.append("adopting a file that changed after planning must be refused")
    except module.CapabilityArtifactsError as error:
        note("changed after planning" in str(error), f"the refusal must say why: {error}")


@scenario("a document that is also an artifact is refused")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"INDEX.md": b"owned\n"})
    plan = module.build_plan(project, "1c", artifacts)
    try:
        module.with_documents(plan, [("INDEX.md", b"other\n")])
        failures.append("one file cannot be both owned and recorded")
    except module.CapabilityArtifactsError:
        pass


@scenario("a failing record rolls the artifacts back with it")
def _(root: Path, project: Path) -> None:
    artifacts = release(root, {"docs/GUIDE.md": b"guide\n"})
    plan = module.build_plan(project, "1c", artifacts)
    # A file where the record expects a directory: the write fails, and the
    # question is whether the files that already landed come back out.
    (project / "notes").write_bytes(b"not a directory\n")
    plan = module.with_documents(plan, [("notes/INDEX.md", b"# Index\n")])
    try:
        module.apply_plan(project, plan)
        failures.append("a record that cannot be written must fail the install")
    except module.CapabilityArtifactsError:
        pass
    note(not (project / "docs/GUIDE.md").exists(),
         "the artifacts stayed behind after the record failed")
    note(not (project / module.LEDGER_NAME).exists(),
         "the ledger recorded an install that was rolled back")


# --- what the install writes into files it does not own ---------------------

install_spec = importlib.util.spec_from_file_location("capability_install", SCRIPTS / "capability_install.py")
assert install_spec and install_spec.loader
install = importlib.util.module_from_spec(install_spec)
sys.modules["capability_install"] = install
install_spec.loader.exec_module(install)

ROW = {"destination": "docs/ops/A.md", "root_purpose": "-", "docs_section": "Ops", "docs_label": "A"}
ROOT_ROW = {"destination": "A.md", "root_purpose": "Назначение", "docs_section": "-", "docs_label": "-"}

note(install.docs_index_document("# Docs\n\n## Ops\n\n- [[docs/ops/A|A]]\n", [ROW]) is None,
     "an entry that is already there must not be added twice")
note(install.index_document("# Index\n\n| [[A|A.md]] | x |\n", [ROOT_ROW]) is None,
     "a root document already linked must not be listed twice")

into_section = install.docs_index_document("# Docs\n\n## Ops\n\n- [[docs/ops/B|B]]\n\n## Other\n\n- [[c|c]]\n", [ROW])
note(into_section.count("## Ops") == 1, f"a second heading must not be created: {into_section!r}")
note(into_section.index("docs/ops/A") < into_section.index("## Other"),
     f"the entry must land inside its own section: {into_section!r}")

new_section = install.docs_index_document("# Docs\n\n## Other\n\n- [[c|c]]\n", [ROW])
note("## Ops" in new_section and new_section.endswith("\n"),
     f"a missing section must be created: {new_section!r}")

# These files belong to the project. A project created on Windows holds CRLF,
# and adding one line is not a reason to re-end every other one.
crlf = install.docs_index_document("# Docs\r\n\r\n## Ops\r\n\r\n- [[docs/ops/B|B]]\r\n", [ROW])
note("\n" not in crlf.replace("\r\n", ""), f"CRLF must survive an inserted entry: {crlf!r}")
crlf_index = install.index_document("# Index\r\n\r\n| a | b |\r\n", [ROOT_ROW])
note("\n" not in crlf_index.replace("\r\n", ""), f"CRLF must survive an appended row: {crlf_index!r}")

# Presence was tested with the bare prefix `[[<link>`, so every link counted as
# present once a longer one starting with it was there. `DEFECTS_ARCHIVE` hid
# `DEFECTS` from both the installer and the validator, which asked the same
# wrong question — the entry was never added and never reported missing.
prefixed = install.docs_index_document(
    "# Docs\n\n## Ops\n\n- [[docs/ops/A_ARCHIVE|Архив]]\n", [ROW])
note(prefixed is not None and "[[docs/ops/A|A]]" in prefixed,
     f"a longer link must not hide a shorter one: {prefixed!r}")
prefixed_index = install.index_document("# Index\n\n| [[A_ARCHIVE|x]] | y |\n", [ROOT_ROW])
note(prefixed_index is not None and "[[A|A.md]]" in prefixed_index,
     f"a longer root link must not hide a shorter one: {prefixed_index!r}")

# A file mixing endings must keep each line as it was: rejoining with one
# chosen ending turned a single CRLF line into a whole-file rewrite.
mixed = install.docs_index_document("# Docs\r\n\n## Ops\n\n- [[docs/ops/B|B]]\n", [ROW])
note(mixed.startswith("# Docs\r\n\n## Ops\n"),
     f"lines that were not touched must keep their endings: {mixed!r}")
# splitlines() also treats a form feed as a break and drops it on rejoin.
form_feed = install.docs_index_document(
    "# Docs\n\n## Ops\n\n- [[docs/ops/B|B]]\n\x0cbreak\n", [ROW])
note("\x0c" in form_feed, f"a form feed must survive an inserted entry: {form_feed!r}")

note(install.docs_index_document(
        "# Docs\n\n## Ops\n\n- [[docs/ops/A_ARCHIVE|Архив]]\n- [[docs/ops/A|A]]\n", [ROW]) is None,
     "adding the same entry twice must still be a no-op")

# A declined stack is a decision the user already made; the install reports it
# instead of overruling it.
try:
    install.practices_document({"preferences": {"global": "ask", "sections": {"1c": "optout"}}}, "1c")
    failures.append("a declined practice stack must block the install")
except install.InstallError:
    pass
connected = install.practices_document({"preferences": {"global": "ask", "sections": {}}}, "1c")
note(connected is not None and b'"1c": "ask"' in connected,
     f"a missing stack must be connected as 'ask': {connected!r}")


if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} capability artifacts test(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All capability artifacts tests passed.")
