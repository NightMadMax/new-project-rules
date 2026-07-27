"""The XML detour: what has to be true before and after a conversion.

The canon in Git is the EDT tree (decision 1.21). Part of the tooling only
speaks the configurator's XML export, so the tree is converted for those tools
and converted back as a separate, explicit step.

Three properties make that detour safe, and each is a rule here rather than a
habit:

* **The export cannot reach the repository.** It is written to the system
  temporary directory and handed to tools as an absolute path, so no ignore
  rule has to be correct for the working tree to stay clean. A leftover from an
  interrupted run is removed by the next one.
* **The conversion is deterministic.** The same tree must produce the same
  bytes. "Close enough" is a stop, not a result: without this, the diff of the
  return step stops meaning anything.
* **The return is never silent.** Coming back to the canon shows the diff and
  waits, and it refuses outright if the canon moved while the export was out —
  otherwise it would quietly overwrite work done meanwhile.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

TEMP_PREFIX = "new-project-rules-1c-"
LOCK_NAME = "conversion.lock"
FINGERPRINT_NAME = "canon.sha256"


class SourceError(Exception):
    """The conversion cannot start, or its result cannot be trusted."""


def fingerprint(tree: Path) -> str:
    """Identity of a source tree: paths and bytes, in a fixed order.

    Paths are part of the digest, or a rename between two files with swapped
    contents would look like no change at all.
    """
    digest = hashlib.sha256()
    for path in sorted(p for p in tree.rglob("*") if p.is_file() and not p.is_symlink()):
        relative = path.relative_to(tree).as_posix()
        body = path.read_bytes()
        digest.update(f"{relative}:{len(body)}\n".encode("utf-8"))
        digest.update(body)
    return digest.hexdigest()


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True
    return True


def acquire_lock(directory: Path) -> Path:
    """One conversion per base at a time.

    Two conversions of one tree would race over the same export and hand a
    half-written directory to a tool. A lock left by a process that no longer
    exists is reclaimed: otherwise a crash would block the base until someone
    deletes a file by hand.
    """
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / LOCK_NAME
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        owner = lock.read_text(encoding="utf-8").strip()
        if owner.isdigit() and alive(int(owner)):
            raise SourceError(f"Another conversion holds {lock} (pid {owner})") from None
        lock.unlink(missing_ok=True)
        try:
            handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise SourceError(f"Another conversion took {lock} first") from None
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    return lock


def state_directory(root: Path) -> Path:
    """Where the lock and the recorded fingerprint live: outside the repository.

    Keyed by the repository path so two checkouts do not share a lock, and
    stable across runs so an interrupted run can be noticed by the next one.
    """
    key = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"{TEMP_PREFIX}state-{key}"


def outside(directory: Path, root: Path) -> bool:
    try:
        directory.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    return False


def export(root: Path, source: Path, source_format: str, convert=None) -> dict:
    """Produce the XML the tool needs, or explain why nothing was produced.

    ``convert`` is the seam: the real converter is the CLI shipped with EDT, and
    a project that does not have it gets a SKIP rather than a failure — the same
    contract diagnostics use, because a missing tool is not a broken project.
    """
    if source_format == "designer-xml":
        return {"action": "skip", "reason": "канон уже в XML, конвертация не нужна", "export": None}
    if source_format != "edt":
        raise SourceError(f"Unknown source_format '{source_format}'")
    if not source.is_dir():
        raise SourceError(f"Source tree not found: {source}")
    if convert is None:
        return {"action": "skip", "reason": "конвертер EDT не найден", "export": None}

    state = state_directory(root)
    lock = acquire_lock(state)
    # A directory left by an interrupted run: removing it is the point of
    # keeping the state directory stable across runs.
    for stale in Path(tempfile.gettempdir()).glob(f"{TEMP_PREFIX}export-*"):
        if stale.is_dir() and not (stale / LOCK_NAME).exists():
            shutil.rmtree(stale, ignore_errors=True)

    destination = Path(tempfile.mkdtemp(prefix=f"{TEMP_PREFIX}export-"))
    if not outside(destination, root):
        shutil.rmtree(destination, ignore_errors=True)
        lock.unlink(missing_ok=True)
        raise SourceError(f"The temporary directory {destination} is inside the repository")
    try:
        convert(source, destination)
        produced = fingerprint(destination)
        # Determinism is checked, not assumed: without it the diff of the
        # return step would mix real changes with converter noise.
        probe = Path(tempfile.mkdtemp(prefix=f"{TEMP_PREFIX}export-"))
        try:
            convert(source, probe)
            if fingerprint(probe) != produced:
                raise SourceError("The conversion is not deterministic; the same tree produced different bytes")
        finally:
            shutil.rmtree(probe, ignore_errors=True)
    except BaseException:
        shutil.rmtree(destination, ignore_errors=True)
        lock.unlink(missing_ok=True)
        raise

    (state / FINGERPRINT_NAME).write_text(fingerprint(source), encoding="utf-8")
    return {
        "action": "export",
        "reason": "",
        "export": destination,
        "canon": fingerprint(source),
        "xml": produced,
    }


def release(root: Path, destination: Path | None) -> None:
    """Nothing survives an operation: not the export, not the lock."""
    if destination is not None:
        shutil.rmtree(destination, ignore_errors=True)
    (state_directory(root) / LOCK_NAME).unlink(missing_ok=True)


def import_back(root: Path, source: Path, export_dir: Path, convert_back=None) -> dict:
    """Return to the canon: refuse on a moved canon, never apply silently."""
    state = state_directory(root)
    recorded = state / FINGERPRINT_NAME
    if not recorded.is_file():
        raise SourceError("There is no export to return from")
    if recorded.read_text(encoding="utf-8").strip() != fingerprint(source):
        raise SourceError(
            "The canon changed while the export was out; discard the export or redo it — "
            "returning now would overwrite work done meanwhile"
        )
    if convert_back is None:
        return {"action": "skip", "reason": "конвертер EDT не найден", "diff": ""}

    staging = Path(tempfile.mkdtemp(prefix=f"{TEMP_PREFIX}import-"))
    try:
        convert_back(export_dir, staging)
        if fingerprint(staging) == fingerprint(source):
            return {"action": "unchanged", "reason": "инструмент не изменил дерево", "diff": ""}
        # The caller shows this and asks; applying is a separate call, because
        # a silent round trip is exactly what decision 1.21 forbids.
        return {"action": "review", "reason": "", "diff": diff(source, staging), "staging": staging}
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def diff(canon: Path, candidate: Path) -> str:
    """What the round trip would change, by file: added, removed, changed."""
    def listing(tree: Path) -> dict[str, str]:
        return {
            path.relative_to(tree).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in tree.rglob("*") if path.is_file() and not path.is_symlink()
        }

    before, after = listing(canon), listing(candidate)
    lines = []
    for name in sorted(set(before) | set(after)):
        if name not in before:
            lines.append(f"+ {name}")
        elif name not in after:
            lines.append(f"- {name}")
        elif before[name] != after[name]:
            lines.append(f"M {name}")
    return "\n".join(lines)


def accept(source: Path, staging: Path) -> None:
    """Apply a reviewed round trip: replace the canon with what was shown."""
    if not staging.is_dir():
        raise SourceError(f"Nothing to accept: {staging} does not exist")
    backup = Path(tempfile.mkdtemp(prefix=f"{TEMP_PREFIX}backup-"))
    kept = backup / "canon"
    shutil.copytree(source, kept, symlinks=True)
    try:
        shutil.rmtree(source)
        shutil.copytree(staging, source, symlinks=True)
    except BaseException:
        # The canon is the project's work; a failed replacement must not eat it.
        shutil.rmtree(source, ignore_errors=True)
        shutil.copytree(kept, source, symlinks=True)
        raise
    finally:
        shutil.rmtree(backup, ignore_errors=True)
        shutil.rmtree(staging, ignore_errors=True)


def cli_converter(command: list[str]):
    """The real converter: the CLI shipped with EDT, given absolute paths."""
    def run(source: Path, destination: Path) -> None:
        result = subprocess.run(
            [*command, "--source", str(source.resolve()), "--target", str(destination.resolve())],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise SourceError(f"The converter failed: {result.stderr.strip()[:300]}")
    return run
