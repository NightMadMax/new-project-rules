"""The XML detour: what has to be true before and after a conversion.

The canon in Git is the EDT tree (decision 1.21). Part of the tooling only
speaks the configurator's XML export, so the tree is converted for those tools
and converted back as a separate, explicit step.

Four properties make that detour safe, and each is a rule here rather than a
habit:

* **The export cannot reach the repository.** It is written to the system
  temporary directory and handed to tools as an absolute path, so no ignore
  rule has to be correct for the working tree to stay clean.
* **Everything is owned.** State, exports and staging are keyed by repository
  *and* base, and every temporary directory carries a marker saying whose it is.
  Cleaning up after an interrupted run must never touch a directory that belongs
  to another project — or to another base of this one.
* **The conversion is deterministic.** The same tree must produce the same
  bytes. "Close enough" is a stop, not a result: without this, the diff of the
  return step stops meaning anything. The check costs a second conversion, which
  is why it can be turned off deliberately and never silently.
* **The return is never silent.** Coming back to the canon shows what would
  change and waits, applies exactly what it showed, and refuses outright if the
  canon moved while the export was out.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

PREFIX = "new-project-rules-1c-"
MARKER = ".owner.json"
LOCK_NAME = "conversion.lock"
FINGERPRINT_NAME = "canon.sha256"
# How long a lock survives its owner. A conversion is a foreground operation:
# past this the session that took the lock is gone, and blocking a base until
# someone deletes a file by hand would be worse than reclaiming it.
LOCK_TTL_SECONDS = 12 * 3600
DIFF_CONTEXT_LINES = 3
DIFF_MAX_LINES = 400


class SourceError(Exception):
    """The conversion cannot start, or its result cannot be trusted."""


def fingerprint(tree: Path) -> str:
    """Identity of a source tree: paths, lengths and bytes, in a fixed order.

    Paths are part of the digest, or a rename would look like no change at all;
    lengths are, or the contents of neighbouring files would run together. The
    order is sorted because filesystems return files in their own order.
    """
    digest = hashlib.sha256()
    for path in sorted(p for p in tree.rglob("*") if p.is_file() and not p.is_symlink()):
        relative = path.relative_to(tree).as_posix()
        body = path.read_bytes()
        digest.update(f"{relative}:{len(body)}\n".encode("utf-8"))
        digest.update(body)
    return digest.hexdigest()


def check_no_symlinks(tree: Path, label: str) -> None:
    """A symlink is carried into the canon but cannot be measured or shown.

    The fingerprint and the diff work on file contents, so a symlink whose
    target changed would look like no change at all — and the return step would
    apply it without ever showing it. Refusing is the only honest option: a
    silent carry breaks the promise that nothing lands unseen.
    """
    found = [path for path in tree.rglob("*") if path.is_symlink()]
    if found:
        shown = ", ".join(path.relative_to(tree).as_posix() for path in found[:3])
        raise SourceError(f"{label} holds symbolic links ({shown}); the conversion cannot carry them")


def state_key(root: Path, base: str) -> str:
    """One state per repository *and* base: a project has several infobases."""
    return hashlib.sha256(f"{root.resolve()}\n{base}".encode("utf-8")).hexdigest()[:16]


def state_directory(root: Path, base: str) -> Path:
    return Path(tempfile.gettempdir()) / f"{PREFIX}state-{state_key(root, base)}"


def outside(directory: Path, root: Path) -> bool:
    try:
        directory.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    return False


def check_source(root: Path, source: Path) -> None:
    """The canon must be a directory strictly inside the repository.

    ``folder`` comes from the registry, and the return step replaces whatever it
    points at: ``.`` or ``../elsewhere`` would put the repository itself, or
    something outside it, under a replacement.
    """
    resolved, base = source.resolve(), root.resolve()
    if resolved == base or outside(resolved, base):
        raise SourceError(f"The source tree {source} must be a directory inside {root}")
    if not resolved.is_dir():
        raise SourceError(f"Source tree not found: {source}")
    check_no_symlinks(resolved, "The canon")


def make_owned(kind: str, key: str) -> Path:
    """A temporary directory that says whose it is — from the outside.

    The marker is a sibling file, not a file inside: the export is handed to a
    tool whole, and a stray file in it would be part of what the tool sees and
    part of what the fingerprint measures.
    """
    directory = Path(tempfile.mkdtemp(prefix=f"{PREFIX}{kind}-"))
    marker_path(directory).write_text(json.dumps({"key": key, "kind": kind}), encoding="utf-8")
    return directory


def marker_path(directory: Path) -> Path:
    return directory.with_name(directory.name + MARKER)


def owner_of(directory: Path) -> str:
    marker = marker_path(directory)
    if not marker.is_file():
        return ""
    try:
        return str(json.loads(marker.read_text(encoding="utf-8")).get("key", ""))
    except (OSError, ValueError):
        return ""


def discard(directory: Path) -> None:
    """Remove a temporary directory, and only then forget who owned it.

    Dropping the marker on a directory that refused to go away would make it
    invisible to every later sweep — gigabytes of export nobody can find.
    """
    shutil.rmtree(directory, ignore_errors=True)
    if not directory.exists():
        marker_path(directory).unlink(missing_ok=True)


def sweep(key: str, keep: Path | None = None) -> list[Path]:
    """Remove what a previous run of *this* base left behind, and nothing else."""
    removed = []
    for kind in ("export", "probe", "import", "backup"):
        for candidate in Path(tempfile.gettempdir()).glob(f"{PREFIX}{kind}-*"):
            if candidate.name.endswith(MARKER):
                # A marker whose directory is gone: the directory was removed by
                # a crash or by the system, and nothing else will collect it.
                if not candidate.with_name(candidate.name[: -len(MARKER)]).exists():
                    candidate.unlink(missing_ok=True)
                continue
            if not candidate.is_dir() or (keep is not None and candidate == keep):
                continue
            if owner_of(candidate) == key:
                discard(candidate)
                removed.append(candidate)
    return removed


def acquire_lock(state: Path) -> Path:
    """One conversion per base at a time.

    Ownership is a session, not a process: the CLI exits between the export and
    the return, so a lock tied to a live pid would be free the moment it was
    taken. It is released explicitly, or it expires — checking liveness by pid
    is not portable, and on Windows the usual trick terminates the process it
    was asked about.
    """
    state.mkdir(parents=True, exist_ok=True)
    lock = state / LOCK_NAME
    for attempt in (1, 2):
        try:
            handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if attempt == 2:
                raise SourceError(f"Another conversion took {lock} first") from None
            # Age comes from the file itself, not from what is written inside:
            # between creating the lock and writing its body there is a moment
            # when it is empty, and an empty file must not read as expired. A
            # clock that moved cannot make a fresh lock look old either.
            try:
                age = time.time() - lock.stat().st_mtime
            except OSError:
                age = 0.0
            if age < LOCK_TTL_SECONDS:
                raise SourceError(
                    f"Another conversion of this base holds {lock} "
                    f"(taken {int(max(age, 0))}s ago); finish it or release it"
                ) from None
            # Exactly one process can rename a given file away, so exactly one
            # reclaims an expired lock; the other finds the winner's lock.
            expired = lock.with_name(f"{lock.name}.expired-{os.getpid()}")
            try:
                os.replace(lock, expired)
            except OSError:
                raise SourceError(f"Another conversion took {lock} first") from None
            expired.unlink(missing_ok=True)
            continue
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"at": time.time(), "pid": os.getpid()}))
        return lock
    raise SourceError(f"Another conversion took {lock} first")


def export(root: Path, base: str, source: Path, source_format: str, convert=None,
           check_determinism: bool = True) -> dict:
    """Produce the XML the tool needs, or explain why nothing was produced.

    ``convert`` is the seam: the real converter is a CLI, and a project that
    does not have it gets a SKIP rather than a failure — the same contract
    diagnostics use, because a missing tool is not a broken project.
    """
    if source_format == "designer-xml":
        return {"action": "skip", "reason": "канон уже в XML, конвертация не нужна", "export": None}
    if source_format != "edt":
        raise SourceError(f"Unknown source_format '{source_format}'")
    check_source(root, source)
    if convert is None:
        return {"action": "skip", "reason": "конвертер EDT не найден", "export": None}

    key = state_key(root, base)
    lock = acquire_lock(state_directory(root, base))
    sweep(key)

    destination = make_owned("export", key)
    if not outside(destination, root):
        discard(destination)
        lock.unlink(missing_ok=True)
        raise SourceError(f"The temporary directory {destination} is inside the repository")
    try:
        convert(source, destination)
        produced = fingerprint(destination)
        if check_determinism:
            # A second conversion doubles the time and the disk this costs. It
            # buys the only thing that makes the diff of the return step
            # meaningful, so it is on by default and off only on request.
            probe = make_owned("probe", key)
            try:
                convert(source, probe)
                if fingerprint(probe) != produced:
                    raise SourceError(
                        "The conversion is not deterministic; the same tree produced different bytes"
                    )
            finally:
                discard(probe)
    except BaseException:
        discard(destination)
        lock.unlink(missing_ok=True)
        raise

    state = state_directory(root, base)
    (state / FINGERPRINT_NAME).write_text(fingerprint(source), encoding="utf-8")
    return {
        "action": "export",
        "reason": "" if check_determinism else "детерминизм не проверялся по явному запросу",
        "export": destination,
        "canon": fingerprint(source),
        "xml": produced,
    }


def release(root: Path, base: str) -> None:
    """Nothing survives an operation: no export, no staging, no lock, no state."""
    sweep(state_key(root, base))
    shutil.rmtree(state_directory(root, base), ignore_errors=True)


def import_back(root: Path, base: str, source: Path, export_dir: Path, convert_back=None) -> dict:
    """Return to the canon: refuse on a moved canon, never apply silently."""
    check_source(root, source)
    state = state_directory(root, base)
    recorded = state / FINGERPRINT_NAME
    if not recorded.is_file():
        raise SourceError("There is no export to return from")
    if not export_dir.is_dir():
        # Without this an empty conversion would read as "everything deleted"
        # and the canon would be wiped by an apply.
        raise SourceError(f"The export {export_dir} is gone; redo it")
    if recorded.read_text(encoding="utf-8").strip() != fingerprint(source):
        raise SourceError(
            "The canon changed while the export was out; discard the export or redo it — "
            "returning now would overwrite work done meanwhile"
        )
    if convert_back is None:
        return {"action": "skip", "reason": "конвертер EDT не найден", "diff": ""}

    staging = make_owned("import", state_key(root, base))
    try:
        convert_back(export_dir, staging)
        if fingerprint(staging) == fingerprint(source):
            discard(staging)
            return {"action": "unchanged", "reason": "инструмент не изменил дерево", "diff": ""}
        # The caller shows this and asks; applying is a separate step that takes
        # this very staging directory, so what is accepted is what was shown.
        return {"action": "review", "reason": "", "diff": diff(source, staging), "staging": staging}
    except BaseException:
        discard(staging)
        raise


def readable(path: Path) -> list[str] | None:
    """Text if it is text. A configuration on support is not always UTF-8."""
    try:
        body = path.read_bytes()
    except OSError:
        return None
    for encoding in ("utf-8", "cp1251"):
        try:
            return body.decode(encoding).splitlines()
        except UnicodeDecodeError:
            continue
    return None


def diff(canon: Path, candidate: Path) -> str:
    """What the round trip would change: the files, and inside them the lines."""
    def listing(tree: Path) -> dict[str, str]:
        return {
            path.relative_to(tree).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in tree.rglob("*") if path.is_file() and not path.is_symlink()
        }

    before, after = listing(canon), listing(candidate)
    lines: list[str] = []
    details: list[str] = []
    for name in sorted(set(before) | set(after)):
        if name not in before:
            lines.append(f"+ {name}")
        elif name not in after:
            lines.append(f"- {name}")
        elif before[name] != after[name]:
            lines.append(f"M {name}")
            old, new = readable(canon / name), readable(candidate / name)
            if old is None or new is None:
                details.append(f"--- {name}\n(двоичный файл, содержимое не показывается)")
                continue
            body = list(difflib.unified_diff(old, new, f"a/{name}", f"b/{name}",
                                             n=DIFF_CONTEXT_LINES, lineterm=""))
            details.extend(body)
    body = lines + ([""] + details if details else [])
    if len(body) > DIFF_MAX_LINES:
        hidden = len(body) - DIFF_MAX_LINES
        body = body[:DIFF_MAX_LINES] + [f"… ещё {hidden} строк(и) не показаны"]
    return "\n".join(body)


def accept(root: Path, source: Path, staging: Path) -> None:
    """Apply a reviewed round trip by renaming, not by deleting first.

    The canon is the project's work. It is moved aside, the new tree takes its
    place, and only then is the old one removed — so a failure at any point
    leaves a complete tree where the canon belongs.
    """
    check_source(root, source)
    if not staging.is_dir():
        raise SourceError(f"Nothing to accept: {staging} does not exist")

    check_no_symlinks(staging, "The staged tree")
    # Staged next to the canon so the swap is a rename: across filesystems a
    # rename is not available, and a copy is not atomic. The names carry this
    # run's marker, so nothing a person left in the repository is removed.
    stamp = f"{os.getpid()}-{int(time.time())}"
    incoming = source.with_name(f".{source.name}.incoming-{stamp}")
    previous = source.with_name(f".{source.name}.previous-{stamp}")
    for leftover in source.parent.glob(f".{source.name}.previous-*"):
        # A crash between the two renames leaves the old canon aside; it is
        # ours by name and by pattern, and nothing else will collect it.
        shutil.rmtree(leftover, ignore_errors=True)
    for leftover in source.parent.glob(f".{source.name}.incoming-*"):
        shutil.rmtree(leftover, ignore_errors=True)
    shutil.copytree(staging, incoming, symlinks=False)

    os.replace(source, previous)
    try:
        os.replace(incoming, source)
    except BaseException:
        os.replace(previous, source)
        shutil.rmtree(incoming, ignore_errors=True)
        raise
    shutil.rmtree(previous, ignore_errors=True)
    discard(staging)


def cli_converter(command: list[str], source_option: str, target_option: str):
    """The real converter: an external CLI, given absolute paths.

    The option names belong to the command, not to us: the EDT CLI is not the
    only converter a project may have, and guessing its flags would produce a
    route that looks configured and fails on first use.
    """
    import subprocess

    if not command:
        raise SourceError("The converter command is empty")

    def run(source: Path, destination: Path) -> None:
        try:
            result = subprocess.run(
                [*command, source_option, str(source.resolve()), target_option, str(destination.resolve())],
                capture_output=True, text=True,
            )
        except OSError as error:
            # A command that cannot be started is the most likely case while the
            # real converter's command line is still unknown (defect 166).
            raise SourceError(f"The converter '{command[0]}' cannot be started: {error}") from error
        if result.returncode != 0:
            raise SourceError(f"The converter failed: {result.stderr.strip()[:300]}")
    return run
