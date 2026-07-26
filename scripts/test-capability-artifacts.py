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


if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} capability artifacts test(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All capability artifacts tests passed.")
