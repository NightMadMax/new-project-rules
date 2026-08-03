#!/usr/bin/env python3
"""The session lock: which infobase this session is allowed to touch.

Until now the rule lived in the text of a skill, and a rule with no executor is
a rule the next session may or may not follow. This is the executor.

The lock is not a memory of a past answer. A port does not say which base sits
behind it — a runtime client can be restarted against another one while the
configured port stays the same — so the lock records what proved the identity,
and anything that could have changed the answer invalidates it: a connection
error, a new selection, a restarted client, a port that no longer matches the
registry.

Production is never implied. A production base needs a confirmation given in
the current conversation, and the lock records that it was given.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import one_c_release_guard as release_guard  # noqa: E402

REGISTRY = "config/1c-projects.tsv"

STATE_DIRECTORY = ".1c-state"
LOCK_NAME = "session-lock.json"
# A working session, not a working day: a lock older than this describes a
# runtime nobody has spoken to since, and re-confirming costs one call.
LOCK_TTL_SECONDS = 12 * 60 * 60
REQUIRED_FIELDS = ("project_id", "environment_id", "server_port", "application_kind",
                   "is_production", "confirmed_by", "write_mode", "created_at")
WRITE_MODES = ("analysis", "approved-write")
# The two things a managed base needs, kept apart on purpose. The state is the
# fact and it is stated, not parsed; the confirmation is the evidence — the call
# and what it answered — and it stays free text.
#
# They used to be one free-text field, read by looking for the words `on` and
# `off` in it. "I did not turn it on" was therefore read as the switch being on
# and opened an approved write, while "the switch on the panel reads off" was
# refused because `on` is a preposition. The shortest string that passed was
# the bare word — which carries no evidence of any call at all, the opposite of
# what the field was for (№254).
SWITCH_OFF = "off"
SWITCH_ON = "on"
SWITCH_STATES = (SWITCH_OFF, SWITCH_ON)


class SessionError(Exception):
    """The session may not touch a live infobase yet, and this says why."""


def state_directory(root: Path) -> Path:
    return root / STATE_DIRECTORY


def lock_path(root: Path) -> Path:
    return state_directory(root) / LOCK_NAME


def read_lock(root: Path) -> dict | None:
    path = lock_path(root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        # An unreadable lock is not a lock: it cannot say what was confirmed.
        return None
    if not isinstance(data, dict) or any(field not in data for field in REQUIRED_FIELDS):
        return None
    return data


def identity_of(row: dict) -> str:
    return f"{row['project_id']}/{row['environment_id']}"


def is_production(row: dict) -> bool:
    """Whether the row says production — and a refusal to guess when it does not.

    Every guard used to compare the raw cell to the literal `"true"`. The
    registry is a TSV a person edits in a spreadsheet, and `True` came back from
    one: the comparison failed, the row read as non-production, and an approved
    write was granted on a production base. A value outside the enum is the one
    case where "no" is the dangerous answer, so it is refused instead. The enum
    check in the validator is a separate run and cannot stand in for this one.
    """
    value = (row.get("is_production") or "").strip().lower()
    if value in ("true", "yes", "1"):
        return True
    if value in ("false", "no", "0", ""):
        return False
    raise SessionError(
        f"is_production is '{row.get('is_production')}', which is neither true nor false: "
        "a base whose production status cannot be read is treated as unsafe, not as safe")


def is_managed(row: dict) -> bool:
    """Whether the row says managed application, read the same forgiving way.

    `Managed` from a spreadsheet skipped the write-switch evidence entirely,
    which is the whole barrier a managed base has.
    """
    value = (row.get("application_kind") or "").strip().lower()
    if value in ("managed", "ordinary"):
        return value == "managed"
    raise SessionError(
        f"application_kind is '{row.get('application_kind')}', which is neither 'managed' nor "
        "'ordinary': the barrier a base has depends on it, so it is not guessed")


def switch_state(state: str) -> bool | None:
    """True for `on`, False for `off`, None for anything else.

    Anything else includes a sentence about the switch: a state is one of two
    words, and a lock that has to infer which one it was given is a lock that
    can infer wrongly.
    """
    value = state.strip().lower()
    return {SWITCH_ON: True, SWITCH_OFF: False}.get(value)


def acquire(root: Path, row: dict, *, confirmed_by: str, write_mode: str = "analysis",
            production_confirmed: bool = False, backup_confirmed: str = "",
            switch_read: str = "", switch_confirmed: str = "",
            now: float | None = None) -> dict:
    """Record a base whose identity has just been proved by a call.

    `confirmed_by` is what proved it — the call and what it answered. An empty
    value would make the lock a claim rather than evidence.

    An approved write needs two more things, and neither of them is implied.
    `backup_confirmed` is what proved a backup exists — its name and when it was
    taken — because "there is a backup somewhere" is exactly the belief that
    turns a mistaken write into a lost day. And production is refused outright:
    a confirmation may select a production base for reading, never for writing.

    A managed application has no barrier in the artifact. On an ordinary one the
    mode is the build that runs: a read-only build cannot write, and the hash
    tells the builds apart. A managed base has one processor and a switch in the
    Toolkit UI, so the mode is a runtime fact, and the only honest way to know it
    is to ask. `switch_read` is the answer — `on` or `off`, stated — and
    `switch_confirmed` is the call that produced it. Deriving either from a file
    would be a guess about state that changes without touching any file.
    """
    if not confirmed_by:
        raise SessionError("a lock needs the call that proved the identity, not a claim")
    if write_mode not in WRITE_MODES:
        raise SessionError(f"unknown write mode '{write_mode}'; expected one of {', '.join(WRITE_MODES)}")
    if write_mode == "approved-write":
        if is_production(row):
            raise SessionError(
                f"{identity_of(row)} is production: an approved write is not taken on it "
                "at all, and no confirmation makes it one"
            )
        if not backup_confirmed:
            raise SessionError(
                "an approved write needs the backup that was checked — which copy and when; "
                "'there is a backup' is a belief, not a precondition"
            )
    if is_managed(row):
        if not switch_confirmed:
            raise SessionError(
                "a managed base has no read-only build to stand behind: the write switch lives "
                "in the Toolkit UI, so the lock needs the call that read its state and what it "
                "answered — for analysis that the switch is off, for an approved write that it is on"
            )
        state = switch_state(switch_read)
        if state is None:
            raise SessionError(
                f"the switch state must be exactly '{SWITCH_OFF}' or '{SWITCH_ON}', not "
                f"'{switch_read}': a state that has to be read out of a sentence can be read wrong"
            )
        if state != (write_mode == "approved-write"):
            wanted = "on" if write_mode == "approved-write" else "off"
            raise SessionError(
                f"the switch was read as {'on' if state else 'off'}, but {write_mode} needs it {wanted}: "
                "the mode is what the base is in, not what the lock would like it to be"
            )
    if is_production(row) and not production_confirmed:
        raise SessionError(
            f"{identity_of(row)} is production: it is never selected implicitly, "
            "the user has to name the base, the environment and the reason in this conversation"
        )
    lock = {
        "project_id": row["project_id"],
        "environment_id": row["environment_id"],
        "server_port": row.get("server_port", ""),
        "application_kind": row.get("application_kind", ""),
        "is_production": "true" if is_production(row) else "false",
        "confirmed_by": confirmed_by,
        "write_mode": write_mode,
        "production_confirmed": bool(production_confirmed),
        "backup_confirmed": backup_confirmed,
        "switch_read": switch_read.strip().lower(),
        "switch_confirmed": switch_confirmed,
        "created_at": now if now is not None else time.time(),
    }
    directory = state_directory(root)
    directory.mkdir(parents=True, exist_ok=True)
    # The pid keeps two processes in one checkout from staging over each other:
    # a fixed name meant the loser of the race replaced the winner's lock.
    temporary = directory / f".{LOCK_NAME}.{os.getpid()}.tmp"
    temporary.write_bytes((json.dumps(lock, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    os.replace(temporary, lock_path(root))
    return lock


def invalidate(root: Path) -> None:
    """Selecting again, a connection error and a restarted client all land here."""
    lock_path(root).unlink(missing_ok=True)


def require(root: Path, rows: list[dict], *, identity: str | None = None,
            write: bool = False, now: float | None = None,
            system: str | None = None) -> dict:
    """The lock this operation may act on, or a refusal that says what to do.

    `rows` is the registry: the lock is checked against it rather than trusted,
    because a base can be re-registered on another port between two calls.

    A lock authorises an operation on a live infobase, and those run on Windows
    only. Everything else about the project — bootstrap, Git, documentation,
    review, validators — works anywhere, so the refusal is here, at the one
    place that stands in front of the runtime, rather than in a rule that says
    the whole capability is Windows-only.
    """
    if (system if system is not None else os.name) != "nt":
        raise SessionError(
            "операции с живой базой 1С выполняются только на Windows; "
            "репозиторий, документация и проверки доступны на любой ОС"
        )
    lock = read_lock(root)
    if lock is None:
        raise SessionError("no session lock: run select-1c-project and confirm the base by a call")

    moment = now if now is not None else time.time()
    try:
        created_at = float(lock.get("created_at", 0))
    except (TypeError, ValueError):
        # A lock whose timestamp cannot be read cannot be shown to be fresh,
        # and a traceback is not the answer to a hand-edited file.
        raise SessionError("the session lock has an unreadable created_at; confirm the base again")
    if moment - created_at > LOCK_TTL_SECONDS:
        raise SessionError("the session lock has expired; confirm the base again")

    locked = f"{lock['project_id']}/{lock['environment_id']}"
    if identity is not None and identity != locked:
        raise SessionError(f"the session lock holds {locked}, not {identity}: select the base you mean")

    row = next((item for item in rows if identity_of(item) == locked), None)
    if row is None:
        raise SessionError(f"{locked} is no longer in the registry; the lock cannot be honoured")
    if row.get("server_port", "") != lock.get("server_port", ""):
        raise SessionError(
            f"{locked} changed its port since it was confirmed "
            f"({lock.get('server_port') or 'none'} → {row.get('server_port') or 'none'}); confirm it again"
        )

    # A managed base carries its mode in the runtime, so a lock without the read
    # switch state authorises nothing — not even analysis, whose whole claim is
    # that writing is impossible. A lock written before this rule existed has no
    # such evidence, and being old is not a reason to skip a precondition.
    if is_managed(row):
        state = switch_state(lock.get("switch_read", ""))
        if state is None or not lock.get("switch_confirmed"):
            raise SessionError(
                "the lock carries no read of the write switch, and a managed base has no "
                "read-only build to fall back on; take the lock again naming the call and its answer"
            )
        if state != (lock.get("write_mode") == "approved-write"):
            raise SessionError(
                f"the switch was read as {'on' if state else 'off'} while the lock is in "
                f"{lock.get('write_mode')} mode; confirm the base again"
            )

    if write:
        if lock.get("write_mode") != "approved-write":
            raise SessionError(
                "this operation writes, and the lock was taken in analysis mode; "
                "an approved write is a separate confirmation, not an assumption"
            )
        if is_production(lock):
            raise SessionError("writing to production is refused here regardless of the lock")
        # A lock written before this rule existed carries no backup evidence, and
        # an old lock is not a reason to skip the precondition.
        if not lock.get("backup_confirmed"):
            raise SessionError(
                "the lock carries no checked backup; take the lock again naming the copy and its date"
            )
    return lock


# --- entry point ------------------------------------------------------------
#
# Without one, this module was a rule with no executor twice over: the skills
# described the lock, the module implemented it, and nothing connected the two
# (№243). A skill can now run `acquire` and `require`, and a refusal is an exit
# code rather than a paragraph the next session may or may not read.


def registry_rows(root: Path) -> list[dict[str, str]]:
    path = root / REGISTRY
    if not path.is_file():
        raise SessionError(f"{REGISTRY} is missing: there is no registry to check the lock against")
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise SessionError(f"Cannot read {REGISTRY}: {exc}") from exc
    reader = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    rows = []
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            continue
        rows.append({key: (value or "") for key, value in row.items()})
    return rows


def find_row(rows: list[dict[str, str]], identity: str) -> dict[str, str]:
    for row in rows:
        if identity_of(row) == identity:
            return row
    known = ", ".join(identity_of(row) for row in rows) or "—"
    raise SessionError(f"{identity} is not in the registry; known bases: {known}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="project root")
    sub = parser.add_subparsers(dest="command", required=True)

    take = sub.add_parser("acquire", help="record a base whose identity a call has just proved")
    take.add_argument("--base", required=True, help="project_id/environment_id")
    take.add_argument("--confirmed-by", required=True,
                      help="the call that proved the identity and what it answered")
    take.add_argument("--write-mode", choices=WRITE_MODES, default="analysis")
    take.add_argument("--production-confirmed", action="store_true")
    take.add_argument("--backup-confirmed", default="",
                      help="which copy was checked and when; required for an approved write")
    take.add_argument("--switch-read", choices=SWITCH_STATES, default="",
                      help="state of the Toolkit write switch, for a managed base")
    take.add_argument("--switch-confirmed", default="",
                      help="the call that read the switch and what it answered")

    check = sub.add_parser("require", help="the lock this operation may act on, or a refusal")
    check.add_argument("--base", default=None, help="the base the operation means to touch")
    check.add_argument("--write", action="store_true", help="the operation writes")

    sub.add_parser("release", help="drop the lock: a new selection, an error, a restarted client")
    sub.add_parser("show", help="print the current lock without judging it")
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        # Before anything touches the lock: these scripts decide whether a live
        # infobase may be written, and being a different release of the standard
        # than the project installed is not a detail to report afterwards.
        release_guard.require_matching_release(root, SCRIPTS.parent)
        if args.command == "acquire":
            row = find_row(registry_rows(root), args.base)
            lock = acquire(
                root, row, confirmed_by=args.confirmed_by, write_mode=args.write_mode,
                production_confirmed=args.production_confirmed,
                backup_confirmed=args.backup_confirmed,
                switch_read=args.switch_read, switch_confirmed=args.switch_confirmed,
            )
            print(f"Locked {identity_of(lock)} in {lock['write_mode']} mode.")
            return 0
        if args.command == "require":
            lock = require(root, registry_rows(root), identity=args.base, write=args.write)
            print(f"{identity_of(lock)} — {lock['write_mode']}, confirmed by: {lock['confirmed_by']}")
            return 0
        if args.command == "release":
            invalidate(root)
            print("Lock released.")
            return 0
        lock = read_lock(root)
        if lock is None:
            print("No session lock.")
            return 1
        print(json.dumps(lock, ensure_ascii=False, indent=2))
        return 0
    except (SessionError, release_guard.ReleaseMismatch) as error:
        print(f"[REFUSED] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
