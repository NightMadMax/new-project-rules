#!/usr/bin/env python3
"""The XML detour: the export must not reach the repository, and the return must not be silent."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import one_c_source as source_module  # noqa: E402

failures: list[str] = []


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


CANON = {"src/Configuration.mdo": "configuration", "src/Catalogs/Товары.mdo": "каталог"}


def canon_project(directory: Path) -> tuple[Path, Path]:
    root = directory / "project"
    tree = root / "configurations/erp"
    tree.mkdir(parents=True)
    make_tree(tree, CANON)
    return root, tree


def cleanup(root: Path) -> None:
    source_module.release(root, None)
    shutil.rmtree(source_module.state_directory(root), ignore_errors=True)


# --- what an export is and where it lives ------------------------------------

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    result = source_module.export(root, tree, "edt", fake_convert)
    export_dir = result["export"]
    note(result["action"] == "export", f"an EDT tree must be converted: {result}")
    # Never inside the repository: no ignore rule has to be right for the
    # working tree to stay clean.
    note(source_module.outside(export_dir, root), f"the export must live outside the repository: {export_dir}")
    note(export_dir.is_absolute(), "tools are given an absolute path")
    note(any(path.name.endswith(".xml") for path in export_dir.rglob("*")), "the export must hold the XML")

    # Determinism is the reason the diff of the return step means anything.
    again = source_module.fingerprint(export_dir)
    source_module.release(root, export_dir)
    note(not export_dir.exists(), "the export must not survive the operation")
    note(not (source_module.state_directory(root) / source_module.LOCK_NAME).exists(),
         "the lock must not survive the operation")

    second = source_module.export(root, tree, "edt", fake_convert)
    note(source_module.fingerprint(second["export"]) == again, "the same tree must produce the same bytes")
    source_module.release(root, second["export"])
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    try:
        source_module.export(root, tree, "edt", drifting_convert)
        failures.append("a non-deterministic conversion must stop the operation")
    except source_module.SourceError:
        pass
    leftovers = list(Path(tempfile.gettempdir()).glob(f"{source_module.TEMP_PREFIX}export-*"))
    note(not leftovers, f"a failed conversion must leave nothing behind: {leftovers}")
    note(not (source_module.state_directory(root) / source_module.LOCK_NAME).exists(),
         "a failed conversion must release the lock")
    cleanup(root)

# --- when there is nothing to convert ----------------------------------------

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    skipped = source_module.export(root, tree, "designer-xml", fake_convert)
    note(skipped["action"] == "skip", "an XML canon needs no conversion")
    note(skipped["export"] is None, "a skipped conversion produces no directory")

    # A missing converter is a SKIP, like a missing CLI in diagnostics: the
    # project is not broken, this route is merely unavailable.
    absent = source_module.export(root, tree, "edt", None)
    note(absent["action"] == "skip" and "конвертер" in absent["reason"],
         f"a missing converter must be a SKIP: {absent}")

    try:
        source_module.export(root, tree, "designer", fake_convert)
        failures.append("an unknown source_format must be refused")
    except source_module.SourceError:
        pass
    cleanup(root)

# --- one conversion at a time ------------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    first = source_module.export(root, tree, "edt", fake_convert)
    try:
        source_module.export(root, tree, "edt", fake_convert)
        failures.append("two conversions of one tree must not run at once")
    except source_module.SourceError:
        pass
    source_module.release(root, first["export"])

    # A lock left by a process that no longer exists must not block the base
    # until someone deletes a file by hand.
    state = source_module.state_directory(root)
    state.mkdir(parents=True, exist_ok=True)
    (state / source_module.LOCK_NAME).write_text("999999999", encoding="utf-8")
    reclaimed = source_module.export(root, tree, "edt", fake_convert)
    note(reclaimed["action"] == "export", "a stale lock must be reclaimed")
    source_module.release(root, reclaimed["export"])
    cleanup(root)

# --- the return to the canon -------------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    root, tree = canon_project(Path(raw))
    result = source_module.export(root, tree, "edt", fake_convert)
    export_dir = result["export"]

    untouched = source_module.import_back(root, tree, export_dir, fake_convert_back)
    note(untouched["action"] == "unchanged", f"a tool that changed nothing produces no diff: {untouched}")

    # The tool edited the XML: the return has to be shown before it is applied.
    changed = next(export_dir.rglob("*Configuration.mdo.xml"))
    changed.write_bytes(b"<xml>configuration v2</xml>")
    (export_dir / "src/Catalogs/Склады.mdo.xml").write_bytes(b"<xml>new</xml>")
    review = source_module.import_back(root, tree, export_dir, fake_convert_back)
    note(review["action"] == "review", f"a changed tree must be reviewed: {review}")
    note("M src/Configuration.mdo" in review["diff"], f"the diff must name the changed file: {review['diff']}")
    note("+ src/Catalogs/Склады.mdo" in review["diff"], f"the diff must name the added file: {review['diff']}")
    note((tree / "src/Configuration.mdo").read_bytes() == b"configuration",
         "reviewing must not touch the canon")

    source_module.accept(tree, review["staging"])
    note((tree / "src/Configuration.mdo").read_bytes() == b"configuration v2", "accepting must apply the review")
    note((tree / "src/Catalogs/Склады.mdo").is_file(), "accepting must apply added files")
    source_module.release(root, export_dir)
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # The canon moved while the export was out: returning would overwrite work.
    root, tree = canon_project(Path(raw))
    result = source_module.export(root, tree, "edt", fake_convert)
    (tree / "src/Configuration.mdo").write_bytes(b"edited by hand")
    try:
        source_module.import_back(root, tree, result["export"], fake_convert_back)
        failures.append("a moved canon must refuse the return")
    except source_module.SourceError:
        pass
    note((tree / "src/Configuration.mdo").read_bytes() == b"edited by hand", "the refusal must keep the canon")
    source_module.release(root, result["export"])
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # Returning without an export is a mistake, not an empty diff.
    root, tree = canon_project(Path(raw))
    try:
        source_module.import_back(root, tree, Path(raw) / "nothing", fake_convert_back)
        failures.append("a return without an export must be refused")
    except source_module.SourceError:
        pass
    cleanup(root)

with tempfile.TemporaryDirectory() as raw:
    # A failed replacement must not eat the project's work.
    root, tree = canon_project(Path(raw))
    staging = Path(raw) / "staging"
    make_tree(staging, {"src/Configuration.mdo": "replacement"})
    original = shutil.copytree
    # Fail the write into the canon exactly once: copytree recurses into
    # subdirectories through itself, so counting calls would hit the backup
    # phase instead and prove nothing.
    failed = {"once": False}

    def failing_copytree(from_path, to_path, *arguments, **keywords):
        if Path(to_path) == tree and not failed["once"]:
            failed["once"] = True
            raise OSError("injected failure")
        return original(from_path, to_path, *arguments, **keywords)

    shutil.copytree = failing_copytree
    try:
        source_module.accept(tree, staging)
        failures.append("a failed replacement must not report success")
    except OSError:
        pass
    finally:
        shutil.copytree = original
    note((tree / "src/Configuration.mdo").read_bytes() == b"configuration",
         "a failed replacement must restore the canon")
    note((tree / "src/Catalogs/Товары.mdo").is_file(), "a failed replacement must restore every file")
    note(failed["once"], "the injected failure must have happened")
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
    result = source_module.export(root, tree, "edt", source_module.cli_converter([sys.executable, str(helper)]))
    note(result["action"] == "export", f"the CLI converter must produce an export: {result}")
    source_module.release(root, result["export"])

    failing = Path(raw) / "broken.py"
    failing.write_bytes(b"import sys\nsys.exit(3)\n")
    try:
        source_module.export(root, tree, "edt", source_module.cli_converter([sys.executable, str(failing)]))
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
    return subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "--base", "erp/dev",
         "--converter", converter, "--converter-back", back, *arguments],
        capture_output=True, text=True, env={**os.environ, "PYTHONIOENCODING": "cp1252"},
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

    applied = run_cli(root, "--import", "--apply", converter=command, back=back)
    note(applied.returncode == 0 and "APPLIED" in applied.stdout, f"--apply must apply: {applied.stdout}")
    note((tree / "src/Configuration.mdo").read_bytes() == b"configuration v2", "the canon must hold the review")

    released = run_cli(root, "--release", converter=command)
    note(released.returncode == 0, f"--release must succeed: {released.stderr}")
    note(not exported.exists(), "--release must remove the export")
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
        capture_output=True, text=True,
    )
    note(unknown.returncode == 2, "an unknown base must be an error")
    note("zup/prod" in unknown.stderr and "erp/dev" in unknown.stderr,
         f"the error must name the known bases: {unknown.stderr}")

    orphan = run_cli(root, "--import", converter=command, back=back)
    note(orphan.returncode == 2, "a return without an export must be an error")
    cleanup(root)

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} source format check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All 1C source format checks passed.")
