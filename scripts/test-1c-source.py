#!/usr/bin/env python3
"""The XML detour: the export must not reach the repository, and the return must not be silent."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import one_c_source as source_module  # noqa: E402

failures: list[str] = []
TEMP = Path(tempfile.gettempdir())
# What was already there. A test that studies leftovers must not become their
# source: everything this run creates is removed at the end, and nothing else.
BEFORE = {path.name for path in TEMP.glob("new-project-rules-1c-*")}


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def make_tree(directory: Path, files: dict[str, str]) -> Path:
    for name, body in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body.encode("utf-8"))
    return directory


def fake_convert(source: Path, destination: Path) -> None:
    """A converter that is deterministic, like the real one must be."""
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        target = destination / (path.relative_to(source).as_posix() + ".xml")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"<xml>" + path.read_bytes() + b"</xml>")


def fake_convert_back(export: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(p for p in export.rglob("*") if p.is_file()):
        target = destination / path.relative_to(export).as_posix()[: -len(".xml")]
        target.parent.mkdir(parents=True, exist_ok=True)
        body = path.read_bytes()
        target.write_bytes(body[len(b"<xml>"):-len(b"</xml>")])


def drifting_convert(source: Path, destination: Path) -> None:
    """A converter whose output depends on something other than its input."""
    fake_convert(source, destination)
    (destination / "stamp").write_bytes(os.urandom(8))


BASE = "erp/dev"
CANON = {"src/Configuration.mdo": "configuration", "src/Catalogs/Товары.mdo": "каталог"}


def canon_project(directory: Path) -> tuple[Path, Path]:
    root = directory / "project"
    tree = root / "configurations/erp"
    tree.mkdir(parents=True)
    make_tree(tree, CANON)
    return root, tree


def cleanup(root: Path) -> None:
    source_module.release(root, BASE)
    shutil.rmtree(source_module.state_directory(root, BASE), ignore_errors=True)


# --- what an export is and where it lives ------------------------------------

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    result = source_module.export(root, BASE, tree, "edt", fake_convert)
    export_dir = result["export"]
    note(result["action"] == "export", f"an EDT tree must be converted: {result}")
    # Never inside the repository: no ignore rule has to be right for the
    # working tree to stay clean.
    note(source_module.outside(export_dir, root), f"the export must live outside the repository: {export_dir}")
    note(export_dir.is_absolute(), "tools are given an absolute path")
    note(any(path.name.endswith(".xml") for path in export_dir.rglob("*")), "the export must hold the XML")

    # Determinism is the reason the diff of the return step means anything.
    again = source_module.fingerprint(export_dir)
    source_module.release(root, BASE)
    note(not export_dir.exists(), "the export must not survive the operation")
    note(not (source_module.state_directory(root, BASE) / source_module.LOCK_NAME).exists(),
         "the lock must not survive the operation")

    second = source_module.export(root, BASE, tree, "edt", fake_convert)
    note(source_module.fingerprint(second["export"]) == again, "the same tree must produce the same bytes")
    source_module.release(root, BASE)
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    try:
        source_module.export(root, BASE, tree, "edt", drifting_convert)
        failures.append("a non-deterministic conversion must stop the operation")
    except source_module.SourceError:
        pass
    key = source_module.state_key(root, BASE)
    leftovers = [path for path in Path(tempfile.gettempdir()).glob(f"{source_module.PREFIX}*-*")
                 if path.is_dir() and source_module.owner_of(path) == key]
    note(not leftovers, f"a failed conversion must leave nothing behind: {leftovers}")
    note(not (source_module.state_directory(root, BASE) / source_module.LOCK_NAME).exists(),
         "a failed conversion must release the lock")
    cleanup(root)

# --- when there is nothing to convert ----------------------------------------

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    skipped = source_module.export(root, BASE, tree, "designer-xml", fake_convert)
    note(skipped["action"] == "skip", "an XML canon needs no conversion")
    note(skipped["export"] is None, "a skipped conversion produces no directory")

    # A missing converter is a SKIP, like a missing CLI in diagnostics: the
    # project is not broken, this route is merely unavailable.
    absent = source_module.export(root, BASE, tree, "edt", None)
    note(absent["action"] == "skip" and "конвертер" in absent["reason"],
         f"a missing converter must be a SKIP: {absent}")

    try:
        source_module.export(root, BASE, tree, "designer", fake_convert)
        failures.append("an unknown source_format must be refused")
    except source_module.SourceError:
        pass
    cleanup(root)

# --- one conversion at a time ------------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    first = source_module.export(root, BASE, tree, "edt", fake_convert)
    try:
        source_module.export(root, BASE, tree, "edt", fake_convert)
        failures.append("two conversions of one tree must not run at once")
    except source_module.SourceError:
        pass
    source_module.release(root, BASE)

    # A lock older than a working session must not block the base until someone
    # deletes a file by hand; an unreadable one must not either.
    state = source_module.state_directory(root, BASE)
    state.mkdir(parents=True, exist_ok=True)
    lock = state / source_module.LOCK_NAME
    stale = time.time() - source_module.LOCK_TTL_SECONDS - 60
    lock.write_text(json.dumps({"at": stale}), encoding="utf-8")
    os.utime(lock, (stale, stale))
    reclaimed = source_module.export(root, BASE, tree, "edt", fake_convert)
    note(reclaimed["action"] == "export", "an expired lock must be reclaimed")
    source_module.release(root, BASE)

    # Age comes from the file, not from what is written in it: an empty lock is
    # what a competing process sees for a moment after O_EXCL succeeds.
    state.mkdir(parents=True, exist_ok=True)
    lock.write_bytes(b"")
    try:
        source_module.export(root, BASE, tree, "edt", fake_convert)
        failures.append("a fresh but empty lock must block a second conversion")
    except source_module.SourceError:
        pass
    os.utime(lock, (stale, stale))
    recovered = source_module.export(root, BASE, tree, "edt", fake_convert)
    note(recovered["action"] == "export", "an old empty lock must not block the base forever")
    source_module.release(root, BASE)

    # A fresh lock does block: that is the point of holding one.
    state.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"at": time.time()}), encoding="utf-8")
    try:
        source_module.export(root, BASE, tree, "edt", fake_convert)
        failures.append("a fresh lock must block a second conversion")
    except source_module.SourceError:
        pass
    source_module.release(root, BASE)
    cleanup(root)

# --- an export belongs to one project and one base ---------------------------

with tempfile.TemporaryDirectory() as raw:
    first_root, first_tree = canon_project(Path(raw) / "one")
    second_root, second_tree = canon_project(Path(raw) / "two")
    mine = source_module.export(first_root, BASE, first_tree, "edt", fake_convert)
    other = source_module.export(second_root, BASE, second_tree, "edt", fake_convert)
    note(mine["export"].is_dir(), "another project's conversion must not remove this export")

    # Two bases of one project are two conversions, with two states.
    second_base = source_module.export(first_root, "zup/dev", first_tree, "edt", fake_convert)
    note(mine["export"].is_dir(), "another base of the same project must not remove this export")
    note(second_base["export"] != mine["export"], "each base gets its own export")

    source_module.release(first_root, "zup/dev")
    note(mine["export"].is_dir(), "releasing one base must not touch another")
    note(other["export"].is_dir(), "releasing one project must not touch another")
    source_module.release(first_root, BASE)
    note(not mine["export"].exists(), "releasing must remove this base's export")
    note(other["export"].is_dir(), "releasing must leave the other project alone")
    source_module.release(second_root, BASE)
    note(not other["export"].exists(), "releasing must remove the other project's export too")
    for path in (first_root, second_root):
        cleanup(path)

# --- the return to the canon -------------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    result = source_module.export(root, BASE, tree, "edt", fake_convert)
    export_dir = result["export"]

    untouched = source_module.import_back(root, BASE, tree, export_dir, fake_convert_back)
    note(untouched["action"] == "unchanged", f"a tool that changed nothing produces no diff: {untouched}")

    # The tool edited the XML: the return has to be shown before it is applied.
    changed = next(export_dir.rglob("*Configuration.mdo.xml"))
    changed.write_bytes(b"<xml>configuration v2</xml>")
    (export_dir / "src/Catalogs/Склады.mdo.xml").write_bytes(b"<xml>new</xml>")
    review = source_module.import_back(root, BASE, tree, export_dir, fake_convert_back)
    note(review["action"] == "review", f"a changed tree must be reviewed: {review}")
    note("M src/Configuration.mdo" in review["diff"], f"the diff must name the changed file: {review['diff']}")
    note("+ src/Catalogs/Склады.mdo" in review["diff"], f"the diff must name the added file: {review['diff']}")
    # Naming a file is not showing a change: the review has to say what moved
    # inside it, or a person is asked to approve a list of names.
    note("-configuration" in review["diff"] and "+configuration v2" in review["diff"],
         f"the diff must show the lines that change: {review['diff']}")
    note((tree / "src/Configuration.mdo").read_bytes() == b"configuration",
         "reviewing must not touch the canon")

    source_module.accept(root, tree, review["staging"])
    note((tree / "src/Configuration.mdo").read_bytes() == b"configuration v2", "accepting must apply the review")
    note((tree / "src/Catalogs/Склады.mdo").is_file(), "accepting must apply added files")
    # The old canon is moved aside during the swap; leaving it there would put
    # a second copy of the configuration next to the first.
    aside = list(tree.parent.glob(".*.previous")) + list(tree.parent.glob(".*.incoming"))
    note(not aside, f"accepting must leave nothing beside the canon: {aside}")
    note(not review["staging"].exists(), "accepting must consume the staging")
    source_module.release(root, BASE)
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # The canon moved while the export was out: returning would overwrite work.
    root, tree = canon_project(Path(raw))
    result = source_module.export(root, BASE, tree, "edt", fake_convert)
    (tree / "src/Configuration.mdo").write_bytes(b"edited by hand")
    try:
        source_module.import_back(root, BASE, tree, result["export"], fake_convert_back)
        failures.append("a moved canon must refuse the return")
    except source_module.SourceError:
        pass
    note((tree / "src/Configuration.mdo").read_bytes() == b"edited by hand", "the refusal must keep the canon")
    source_module.release(root, BASE)
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # An export that disappeared is a mistake, not "everything was deleted": a
    # forgiving converter would produce an empty staging and an apply would
    # wipe the canon.
    root, tree = canon_project(Path(raw))
    result = source_module.export(root, BASE, tree, "edt", fake_convert)
    shutil.rmtree(result["export"])
    try:
        source_module.import_back(root, BASE, tree, result["export"], fake_convert_back)
        failures.append("a vanished export must be refused")
    except source_module.SourceError:
        pass
    note((tree / "src/Configuration.mdo").is_file(), "the refusal must keep the canon")
    source_module.release(root, BASE)
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # Returning without an export is a mistake, not an empty diff.
    root, tree = canon_project(Path(raw))
    try:
        source_module.import_back(root, BASE, tree, Path(raw) / "nothing", fake_convert_back)
        failures.append("a return without an export must be refused")
    except source_module.SourceError:
        pass
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # A failed replacement must not eat the project's work: the canon is moved
    # aside and only removed once the new tree is in place.
    root, tree = canon_project(Path(raw))
    staging = Path(raw) / "staging"
    make_tree(staging, {"src/Configuration.mdo": "replacement"})
    original = os.replace
    failed = {"once": False}

    def failing_replace(from_path, to_path, *arguments, **keywords):
        if Path(to_path) == tree and not failed["once"]:
            failed["once"] = True
            raise OSError("injected failure")
        return original(from_path, to_path, *arguments, **keywords)

    os.replace = failing_replace
    try:
        source_module.accept(root, tree, staging)
        failures.append("a failed replacement must not report success")
    except OSError:
        pass
    finally:
        os.replace = original
    note(failed["once"], "the injected failure must have happened")
    note((tree / "src/Configuration.mdo").read_bytes() == b"configuration",
         "a failed replacement must restore the canon")
    note((tree / "src/Catalogs/Товары.mdo").is_file(), "a failed replacement must restore every file")
    note(not list(tree.parent.glob(".*.incoming")), "a failed replacement must not leave a staging tree")
    note(not list(tree.parent.glob(".*.previous")), "a failed replacement must not leave the old canon aside")
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # The registry decides which folder is replaced, so a folder that is the
    # repository itself — or outside it — must be refused before anything moves.
    root, tree = canon_project(Path(raw))
    staging = Path(raw) / "staging"
    make_tree(staging, {"a.mdo": "replacement"})
    for name, folder in (("the repository itself", root), ("outside the repository", Path(raw) / "elsewhere")):
        try:
            source_module.accept(root, folder, staging)
            failures.append(f"{name} must not be replaced")
        except source_module.SourceError:
            pass
        try:
            source_module.export(root, BASE, folder, "edt", fake_convert)
            failures.append(f"{name} must not be exported")
        except source_module.SourceError:
            pass
    note((root / "configurations/erp/src/Configuration.mdo").is_file(), "the refusals must change nothing")
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # Reclaiming an expired lock is a rename, so exactly one process wins it.
    # If the rename does not happen, nobody may proceed as if it had.
    root, tree = canon_project(Path(raw))
    state = source_module.state_directory(root, BASE)
    state.mkdir(parents=True, exist_ok=True)
    lock = state / source_module.LOCK_NAME
    stale = time.time() - source_module.LOCK_TTL_SECONDS - 60
    lock.write_text(json.dumps({"at": stale}), encoding="utf-8")
    os.utime(lock, (stale, stale))
    original_replace = os.replace
    os.replace = lambda *arguments, **keywords: (_ for _ in ()).throw(FileNotFoundError("lost the race"))
    try:
        source_module.export(root, BASE, tree, "edt", fake_convert)
        failures.append("losing the race for an expired lock must not proceed")
    except source_module.SourceError:
        pass
    finally:
        os.replace = original_replace
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # The export must never be inside the repository, whatever the system says
    # its temporary directory is.
    root, tree = canon_project(Path(raw))
    inside = root / "tmp"
    inside.mkdir()
    original_mkdtemp = tempfile.mkdtemp
    tempfile.mkdtemp = lambda *arguments, **keywords: str(Path(original_mkdtemp(dir=str(inside))))
    try:
        source_module.export(root, BASE, tree, "edt", fake_convert)
        failures.append("an export inside the repository must be refused")
    except source_module.SourceError:
        pass
    finally:
        tempfile.mkdtemp = original_mkdtemp
    cleanup(root)

# --- what cannot be carried across quietly -----------------------------------

with tempfile.TemporaryDirectory() as raw:
    # A symlink is copied into the canon but neither measured nor shown, so a
    # changed target would land without ever appearing in a review.
    root, tree = canon_project(Path(raw))
    (tree / "src/link.mdo").symlink_to(tree / "src/Configuration.mdo")
    try:
        source_module.export(root, BASE, tree, "edt", fake_convert)
        failures.append("a symlink in the canon must be refused")
    except source_module.SourceError:
        pass
    (tree / "src/link.mdo").unlink()

    result = source_module.export(root, BASE, tree, "edt", fake_convert)
    staging = Path(raw) / "staging"
    make_tree(staging, {"src/Configuration.mdo": "replacement"})
    (staging / "src/link.mdo").symlink_to(staging / "src/Configuration.mdo")
    try:
        source_module.accept(root, tree, staging)
        failures.append("a symlink in the staged tree must be refused")
    except source_module.SourceError:
        pass
    note((tree / "src/Configuration.mdo").read_bytes() == b"configuration", "the refusal must keep the canon")
    source_module.release(root, BASE)
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # A report has to fit on a screen: a tree where everything changed would
    # otherwise print one line per file before any limit applied.
    root, tree = canon_project(Path(raw))
    make_tree(tree, {f"src/many/{number}.mdo": str(number) for number in range(source_module.DIFF_MAX_LINES * 2)})
    result = source_module.export(root, BASE, tree, "edt", fake_convert)
    for path in list((result["export"] / "src/many").rglob("*.xml")):
        path.unlink()
    review = source_module.import_back(root, BASE, tree, result["export"], fake_convert_back)
    printed = review["diff"].splitlines()
    note(len(printed) <= source_module.DIFF_MAX_LINES + 1, f"the report must be bounded: {len(printed)} lines")
    note("не показаны" in printed[-1], f"a truncated report must say so: {printed[-1]}")
    shutil.rmtree(review["staging"], ignore_errors=True)
    source_module.release(root, BASE)
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # A configuration on support is not always UTF-8, and a binary file has no
    # lines to show: neither may crash the review.
    root, tree = canon_project(Path(raw))
    (tree / "src/legacy.mdo").write_bytes("комментарий".encode("cp1251"))
    (tree / "src/form.bin").write_bytes(bytes(range(256)))
    result = source_module.export(root, BASE, tree, "edt", fake_convert)
    (result["export"] / "src/legacy.mdo.xml").write_bytes(
        b"<xml>" + "другой комментарий".encode("cp1251") + b"</xml>")
    (result["export"] / "src/form.bin.xml").write_bytes(b"<xml>" + bytes(range(255, -1, -1)) + b"</xml>")
    review = source_module.import_back(root, BASE, tree, result["export"], fake_convert_back)
    note("M src/legacy.mdo" in review["diff"], "a cp1251 file must be named")
    note("другой" in review["diff"], f"a cp1251 file must show its lines: {review['diff'][:200]}")
    note("двоичный файл" in review["diff"], "a binary file must say why it shows no lines")
    shutil.rmtree(review["staging"], ignore_errors=True)
    source_module.release(root, BASE)
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # Nothing of ours may outlive a release: not the export, not the staging,
    # not the state, not the marker of a directory that is already gone.
    root, tree = canon_project(Path(raw))
    result = source_module.export(root, BASE, tree, "edt", fake_convert)
    review = source_module.import_back(root, BASE, tree, result["export"], fake_convert_back)
    shutil.rmtree(result["export"])  # as a crash or a system cleaner would
    source_module.release(root, BASE)
    key = source_module.state_key(root, BASE)
    left = [path for path in Path(tempfile.gettempdir()).glob(f"{source_module.PREFIX}*")
            if source_module.owner_of(path) == key or path.name.endswith(key)
            or (path.name.endswith(source_module.MARKER) and key in path.read_text(encoding="utf-8"))]
    note(not left, f"a release must leave nothing of this base behind: {left}")
    note(not source_module.state_directory(root, BASE).exists(), "a release must remove the state directory")
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # A directory that refused to go away must keep its owner, or no later
    # sweep will ever find it.
    root, tree = canon_project(Path(raw))
    result = source_module.export(root, BASE, tree, "edt", fake_convert)
    export_dir = result["export"]
    original_rmtree = shutil.rmtree
    shutil.rmtree = lambda *arguments, **keywords: None
    try:
        source_module.discard(export_dir)
    finally:
        shutil.rmtree = original_rmtree
    note(source_module.owner_of(export_dir) == source_module.state_key(root, BASE),
         "a directory that survived removal must keep its owner")
    source_module.release(root, BASE)
    note(not export_dir.exists(), "the next sweep must collect it")
    cleanup(root)

# --- what the fingerprint has to notice --------------------------------------

with tempfile.TemporaryDirectory() as raw:
    # Two files with swapped contents: the same bytes, a different tree. A
    # fingerprint that ignored paths would call this "no change" and the return
    # step would silently accept a rename.
    first = make_tree(Path(raw) / "first", {"a.mdo": "one", "b.mdo": "two"})
    second = make_tree(Path(raw) / "second", {"a.mdo": "two", "b.mdo": "one"})
    note(source_module.fingerprint(first) != source_module.fingerprint(second),
         "a swap between two files must change the fingerprint")
    third = make_tree(Path(raw) / "third", {"a.mdo": "one", "b.mdo": "two"})
    note(source_module.fingerprint(first) == source_module.fingerprint(third),
         "the same tree must have the same fingerprint")
    # The order the filesystem hands files back differs between machines, so
    # the digest must not depend on it.
    shuffled = make_tree(Path(raw) / "shuffled", {"a.mdo": "one", "b.mdo": "two", "c/d.mdo": "three"})
    straight = source_module.fingerprint(shuffled)
    original_rglob = Path.rglob
    Path.rglob = lambda self, pattern: reversed(list(original_rglob(self, pattern)))
    try:
        note(source_module.fingerprint(shuffled) == straight,
             "the fingerprint must not depend on the order the filesystem returns")
    finally:
        Path.rglob = original_rglob

    # A rename with the same content is a change: the path is part of what a
    # tree is, not decoration around the bytes.
    named = make_tree(Path(raw) / "named", {"Catalogs/Товары.mdo": "one"})
    renamed = make_tree(Path(raw) / "renamed", {"Catalogs/Склады.mdo": "one"})
    note(source_module.fingerprint(named) != source_module.fingerprint(renamed),
         "a rename must change the fingerprint")

    # A name and the content next to it must not run together: without a
    # length these two trees feed the digest the same characters.
    left = make_tree(Path(raw) / "left", {"a": "x", "ab": ""})
    right = make_tree(Path(raw) / "right", {"a": "xa", "b": ""})
    note(source_module.fingerprint(left) != source_module.fingerprint(right),
         "a name and the content beside it must not run together")

# --- the real converter runs a real command ----------------------------------

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    helper = Path(raw) / "converter.py"
    helper.write_bytes(
        "import sys, pathlib\n"
        "target = pathlib.Path(sys.argv[sys.argv.index('--target') + 1])\n"
        "source = pathlib.Path(sys.argv[sys.argv.index('--source') + 1])\n"
        "target.mkdir(parents=True, exist_ok=True)\n"
        "for path in sorted(p for p in source.rglob('*') if p.is_file()):\n"
        "    out = target / (path.relative_to(source).as_posix() + '.xml')\n"
        "    out.parent.mkdir(parents=True, exist_ok=True)\n"
        "    out.write_bytes(path.read_bytes())\n".encode("utf-8")
    )
    result = source_module.export(root, BASE, tree, "edt", source_module.cli_converter([sys.executable, str(helper)], "--source", "--target"))
    note(result["action"] == "export", f"the CLI converter must produce an export: {result}")
    source_module.release(root, BASE)

    failing = Path(raw) / "broken.py"
    failing.write_bytes(b"import sys\nsys.exit(3)\n")
    try:
        source_module.export(root, BASE, tree, "edt", source_module.cli_converter([sys.executable, str(failing)], "--source", "--target"))
        failures.append("a converter that fails must stop the operation")
    except source_module.SourceError:
        pass
    cleanup(root)

# --- the CLI drives the same contract ----------------------------------------

CLI = SCRIPTS / "export-1c-source.py"
REGISTRY_HEADER = (
    "project_id\tenvironment_id\tfolder\tconfiguration\tplatform_version\tcompatibility_mode\t"
    "application_kind\tsupport_mode\tsource_format\tedt_workspace\tedt_profile\tserver_port\t"
    "is_production\tmcp_enabled\towner"
)


def cli_project(directory: Path, source_format: str = "edt") -> tuple[Path, Path, str]:
    root, tree = canon_project(directory)
    (root / "config").mkdir(parents=True, exist_ok=True)
    row = ("erp\tdev\tconfigurations/erp\tERP 2\t8.3.27.2025\t8.3.27\tmanaged\ton-support\t"
           f"{source_format}\terp-ws\t-\t6003\tfalse\ttrue\tteam")
    (root / "config/1c-projects.tsv").write_bytes((REGISTRY_HEADER + "\n" + row + "\n").encode("utf-8"))
    helper = directory / "converter.py"
    helper.write_bytes(
        "import sys, pathlib\n"
        "target = pathlib.Path(sys.argv[sys.argv.index('--target') + 1])\n"
        "source = pathlib.Path(sys.argv[sys.argv.index('--source') + 1])\n"
        "target.mkdir(parents=True, exist_ok=True)\n"
        "for path in sorted(p for p in source.rglob('*') if p.is_file()):\n"
        "    out = target / (path.relative_to(source).as_posix() + '.xml')\n"
        "    out.parent.mkdir(parents=True, exist_ok=True)\n"
        "    out.write_bytes(path.read_bytes())\n".encode("utf-8")
    )
    back = directory / "converter-back.py"
    back.write_bytes(
        "import sys, pathlib\n"
        "target = pathlib.Path(sys.argv[sys.argv.index('--target') + 1])\n"
        "source = pathlib.Path(sys.argv[sys.argv.index('--source') + 1])\n"
        "target.mkdir(parents=True, exist_ok=True)\n"
        "for path in sorted(p for p in source.rglob('*') if p.is_file()):\n"
        "    out = target / path.relative_to(source).as_posix()[:-len('.xml')]\n"
        "    out.parent.mkdir(parents=True, exist_ok=True)\n"
        "    out.write_bytes(path.read_bytes())\n".encode("utf-8")
    )
    return root, tree, f"{sys.executable} {helper}", f"{sys.executable} {back}"


def run_cli(root: Path, *arguments: str, converter: str = "", back: str = "") -> subprocess.CompletedProcess:
    # The child is told the console is cp1252 — the Windows default — and the
    # tool is expected to write UTF-8 anyway, so the reader decodes UTF-8. With
    # the platform default here the parent would fail on the tool's own output.
    return subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "--base", "erp/dev",
         "--converter", converter, "--converter-back", back, *arguments],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )


with tempfile.TemporaryDirectory() as raw:
    root, tree, command, back = cli_project(Path(raw))

    unknown = run_cli(root, converter=command)
    note(unknown.returncode == 0 and "EXPORT" in unknown.stdout, f"the CLI must export: {unknown.stdout}{unknown.stderr}")
    exported = Path(unknown.stdout.split("]", 1)[1].strip())
    note(exported.is_dir() and source_module.outside(exported, root), "the CLI export must live outside the project")

    untouched = run_cli(root, "--import", converter=command, back=back)
    note("UNCHANGED" in untouched.stdout, f"an untouched export returns nothing: {untouched.stdout}")

    (exported / "src/Configuration.mdo.xml").write_bytes(b"configuration v2")
    review = run_cli(root, "--import", converter=command, back=back)
    note(review.returncode == 1, "a review that was not applied must be a non-zero exit")
    note("M src/Configuration.mdo" in review.stdout.splitlines(), f"the CLI must show the diff: {review.stdout}")
    note((tree / "src/Configuration.mdo").read_bytes() == b"configuration", "showing must not apply")

    # Applying takes the staging that was shown, not a fresh conversion: between
    # the two commands the export could have changed, and then the person would
    # have approved something else.
    (exported / "src/Configuration.mdo.xml").write_bytes(b"configuration v3")
    applied = run_cli(root, "--apply", converter=command, back=back)
    note(applied.returncode == 0 and "APPLIED" in applied.stdout, f"--apply must apply: {applied.stdout}")
    note((tree / "src/Configuration.mdo").read_bytes() == b"configuration v2",
         "the canon must hold what was shown, not what changed afterwards")

    # The conversation between --import and --apply is exactly the window in
    # which a person edits the canon by hand.
    run_cli(root, "--release", converter=command)
    fresh = run_cli(root, converter=command, back=back)
    note("EXPORT" in fresh.stdout, f"the second export must succeed: {fresh.stdout}{fresh.stderr}")
    fresh_export = Path(fresh.stdout.split("]", 1)[1].strip())
    (fresh_export / "src/Configuration.mdo.xml").write_bytes(b"configuration v4")
    shown = run_cli(root, "--import", converter=command, back=back)
    note(shown.returncode == 1, f"the review must await approval: {shown.stdout}{shown.stderr}")
    (tree / "src/Configuration.mdo").write_bytes(b"edited by hand")
    late = run_cli(root, "--apply", converter=command, back=back)
    note(late.returncode == 2, f"applying onto a moved canon must be an error: {late.stdout}{late.stderr}")
    note((tree / "src/Configuration.mdo").read_bytes() == b"edited by hand", "the refusal must keep the canon")
    run_cli(root, "--release", converter=command)

    released = run_cli(root, "--release", converter=command)
    note(released.returncode == 0, f"--release must succeed: {released.stderr}")
    note(not exported.exists(), "--release must remove the export")
    key = source_module.state_key(root, "erp/dev")
    left = [path for path in Path(tempfile.gettempdir()).glob(f"{source_module.PREFIX}*-*")
            if path.is_dir() and source_module.owner_of(path) == key]
    note(not left, f"--release must leave no staging behind: {left}")

    orphan_apply = run_cli(root, "--apply", converter=command, back=back)
    note(orphan_apply.returncode == 2, "applying without a review must be an error")
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    root, tree, command, back = cli_project(Path(raw), "designer-xml")
    skipped = run_cli(root, converter=command)
    note(skipped.returncode == 0 and "SKIP" in skipped.stdout, f"an XML canon must be skipped: {skipped.stdout}")

    absent = run_cli(root)
    note(absent.returncode == 0 and "SKIP" in absent.stdout, f"a missing converter must be a SKIP: {absent.stdout}")
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    root, tree, command, back = cli_project(Path(raw))
    unknown = subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "--base", "zup/prod", "--converter", command],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    note(unknown.returncode == 2, "an unknown base must be an error")
    note("zup/prod" in unknown.stderr and "erp/dev" in unknown.stderr,
         f"the error must name the known bases: {unknown.stderr}")

    orphan = run_cli(root, "--import", converter=command, back=back)
    note(orphan.returncode == 2, "a return without an export must be an error")

    # While the real converter's command line is unknown, "cannot be started"
    # is the likeliest outcome: it must be a message with the error code of an
    # error, not a stack trace and not the code that means "awaiting approval".
    missing = run_cli(root, converter="/no/such/edt-cli convert")
    note(missing.returncode == 2, f"an unstartable converter must be an error: {missing.returncode}")
    note("Traceback" not in missing.stderr, f"an unstartable converter must not print a stack: {missing.stderr}")
    blank = run_cli(root, converter="   ")
    note(blank.returncode == 2 and "Traceback" not in blank.stderr,
         f"a blank converter command must be an error: {blank.returncode} {blank.stderr[:200]}")

    broken = source_module.state_directory(root, "erp/dev") / "export.json"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text("не json", encoding="utf-8")
    unreadable = run_cli(root, "--import", converter=command, back=back)
    note(unreadable.returncode == 2 and "Traceback" not in unreadable.stderr,
         f"an unreadable record must be a message: {unreadable.stderr[:200]}")
    # And releasing must be the way out of it: it may not need the record it is
    # there to clean up.
    recovered = run_cli(root, "--release", converter=command)
    note(recovered.returncode == 0, f"--release must work on a broken record: {recovered.stderr[:200]}")
    note(not broken.exists(), "--release must remove the broken record")

    # The determinism check costs a second conversion: switching it off has to
    # be asked for and has to be said out loud.
    counted = run_cli(root, converter=command)
    note("EXPORT" in counted.stdout and "WARN" not in counted.stdout,
         f"the default export says nothing unusual: {counted.stdout}")
    run_cli(root, "--release", converter=command)
    cheap = run_cli(root, "--skip-determinism-check", converter=command)
    note("WARN" in cheap.stdout and "детерминизм" in cheap.stdout,
         f"skipping the check must be stated: {cheap.stdout}")
    run_cli(root, "--release", converter=command)

    # A path with a space is the usual case on Windows, not an edge case.
    spaced = Path(raw) / "Program Files"
    spaced.mkdir()
    moved = spaced / "converter.py"
    moved.write_bytes((Path(command.split(" ", 1)[1])).read_bytes())
    for style, quoted_command in (
        ("двойные кавычки", f'"{sys.executable}" "{moved}"'),
        ("одинарные кавычки", f"'{sys.executable}' '{moved}'"),
    ):
        quoted = run_cli(root, converter=quoted_command)
        note(quoted.returncode == 0 and "EXPORT" in quoted.stdout,
             f"a converter path with a space must work ({style}): {quoted.stdout}{quoted.stderr}")
        run_cli(root, "--release", converter=command)
    cleanup(root)

for path in TEMP.glob("new-project-rules-1c-*"):
    if path.name in BEFORE:
        continue
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} source format check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All 1C source format checks passed.")
