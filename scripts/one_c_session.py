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

import json
import os
import time
from pathlib import Path

STATE_DIRECTORY = ".1c-state"
LOCK_NAME = "session-lock.json"
# A working session, not a working day: a lock older than this describes a
# runtime nobody has spoken to since, and re-confirming costs one call.
LOCK_TTL_SECONDS = 12 * 60 * 60
REQUIRED_FIELDS = ("project_id", "environment_id", "server_port", "application_kind",
                   "is_production", "confirmed_by", "write_mode", "created_at")
WRITE_MODES = ("analysis", "approved-write")


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


def acquire(root: Path, row: dict, *, confirmed_by: str, write_mode: str = "analysis",
            production_confirmed: bool = False, now: float | None = None) -> dict:
    """Record a base whose identity has just been proved by a call.

    `confirmed_by` is what proved it — the call and what it answered. An empty
    value would make the lock a claim rather than evidence.
    """
    if not confirmed_by:
        raise SessionError("a lock needs the call that proved the identity, not a claim")
    if write_mode not in WRITE_MODES:
        raise SessionError(f"unknown write mode '{write_mode}'; expected one of {', '.join(WRITE_MODES)}")
    if row.get("is_production") == "true" and not production_confirmed:
        raise SessionError(
            f"{identity_of(row)} is production: it is never selected implicitly, "
            "the user has to name the base, the environment and the reason in this conversation"
        )
    lock = {
        "project_id": row["project_id"],
        "environment_id": row["environment_id"],
        "server_port": row.get("server_port", ""),
        "application_kind": row.get("application_kind", ""),
        "is_production": row.get("is_production", "false"),
        "confirmed_by": confirmed_by,
        "write_mode": write_mode,
        "production_confirmed": bool(production_confirmed),
        "created_at": now if now is not None else time.time(),
    }
    directory = state_directory(root)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f"{LOCK_NAME}.tmp"
    temporary.write_bytes((json.dumps(lock, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    os.replace(temporary, lock_path(root))
    return lock


def invalidate(root: Path) -> None:
    """Selecting again, a connection error and a restarted client all land here."""
    lock_path(root).unlink(missing_ok=True)


def require(root: Path, rows: list[dict], *, identity: str | None = None,
            write: bool = False, now: float | None = None) -> dict:
    """The lock this operation may act on, or a refusal that says what to do.

    `rows` is the registry: the lock is checked against it rather than trusted,
    because a base can be re-registered on another port between two calls.
    """
    lock = read_lock(root)
    if lock is None:
        raise SessionError("no session lock: run select-1c-project and confirm the base by a call")

    moment = now if now is not None else time.time()
    if moment - float(lock.get("created_at", 0)) > LOCK_TTL_SECONDS:
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

    if write:
        if lock.get("write_mode") != "approved-write":
            raise SessionError(
                "this operation writes, and the lock was taken in analysis mode; "
                "an approved write is a separate confirmation, not an assumption"
            )
        if lock.get("is_production") == "true":
            raise SessionError("writing to production is refused here regardless of the lock")
    return lock
