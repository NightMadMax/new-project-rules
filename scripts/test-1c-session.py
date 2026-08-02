#!/usr/bin/env python3
"""The session lock has to refuse, and refuse for a nameable reason.

Every case here is a rule that previously existed only as a sentence in a skill:
what a skill does with a sentence depends on the session reading it, which is
the difference between a rule and a check.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("one_c_session", SCRIPTS / "one_c_session.py")
assert spec and spec.loader
session = importlib.util.module_from_spec(spec)
sys.modules["one_c_session"] = session
spec.loader.exec_module(session)

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def refuses(action, expected: str, message: str) -> None:
    try:
        action()
    except session.SessionError as error:
        note(expected in str(error), f"{message}: unexpected reason: {error}")
        return
    failures.append(message)


def base(**overrides) -> dict:
    row = {
        "project_id": "erp", "environment_id": "dev", "server_port": "6003",
        "application_kind": "managed", "is_production": "false",
    }
    row.update(overrides)
    return row


DEV = base()
PROD = base(environment_id="prod", server_port="6004", is_production="true")
REGISTRY = [DEV, PROD]

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)

    # --- nothing confirmed yet ---------------------------------------------
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "no session lock",
            "a live-base operation without a lock must be refused")

    # --- a lock is evidence, not a claim -----------------------------------
    refuses(lambda: session.acquire(root, DEV, confirmed_by=""), "proved the identity",
            "a lock without the call that proved the identity must be refused")

    # --- production is never implied ---------------------------------------
    refuses(lambda: session.acquire(root, PROD, confirmed_by="get_metadata: ERP prod", switch_confirmed="get_write_switch: off"),
            "production", "production must not be selectable without a named confirmation")
    lock = session.acquire(root, PROD, confirmed_by="get_metadata: ERP prod", switch_confirmed="get_write_switch: off", production_confirmed=True)
    note(lock["production_confirmed"] is True, "the confirmation must be recorded, not just accepted")
    session.invalidate(root)

    # --- the ordinary path --------------------------------------------------
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_confirmed="get_write_switch: off")
    held = session.require(root, REGISTRY, system="nt")
    note(held["project_id"] == "erp", f"a confirmed base must be usable: {held}")
    note(session.require(root, REGISTRY, system="nt", identity="erp/dev")["environment_id"] == "dev",
         "asking for the base that is locked must succeed")

    # --- another base is not this one ---------------------------------------
    refuses(lambda: session.require(root, REGISTRY, system="nt", identity="erp/prod"), "holds erp/dev",
            "an operation naming another base must be refused")

    # --- writing is a separate confirmation ---------------------------------
    refuses(lambda: session.require(root, REGISTRY, system="nt", write=True), "analysis mode",
            "a write under an analysis lock must be refused")

    # --- the port moved under the lock --------------------------------------
    moved = [base(server_port="6007"), PROD]
    refuses(lambda: session.require(root, moved, system="nt"), "changed its port",
            "a base re-registered on another port must invalidate the confirmation")

    # --- the base left the registry -----------------------------------------
    refuses(lambda: session.require(root, [PROD], system="nt"), "no longer in the registry",
            "a lock on a base that is gone must not be honoured")

    # --- a lock that nobody has spoken to since -----------------------------
    stale = time.time() - session.LOCK_TTL_SECONDS - 60
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_confirmed="get_write_switch: off", now=stale)
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "expired",
            "a lock older than a working session must be re-confirmed")

    # --- selecting again drops the previous confirmation ---------------------
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_confirmed="get_write_switch: off")
    session.invalidate(root)
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "no session lock",
            "invalidation must leave nothing behind to fall back on")

    # --- an approved write needs a backup that was actually checked ----------
    refuses(lambda: session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_confirmed="get_write_switch: off",
                                    write_mode="approved-write"),
            "backup", "an approved write without a checked backup must be refused")

    # --- and it is never taken on production, confirmed or not ---------------
    refuses(lambda: session.acquire(root, PROD, confirmed_by="get_metadata: ERP prod", switch_confirmed="get_write_switch: off",
                                    production_confirmed=True, write_mode="approved-write",
                                    backup_confirmed="erp-prod-2026-07-31.dt"),
            "production", "an approved write on production must be refused outright")

    # --- the ordinary approved write ----------------------------------------
    lock = session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                           switch_confirmed="get_write_switch: on",
                           write_mode="approved-write",
                           backup_confirmed="erp-dev-2026-07-31.dt, проверена восстановлением")
    note("erp-dev-2026-07-31.dt" in lock["backup_confirmed"],
         "the backup that was checked must be recorded, not merely asserted")
    note(session.require(root, REGISTRY, system="nt", write=True)["write_mode"] == "approved-write",
         "an approved write must be allowed on a non-production base with a backup")

    # --- the second barrier: a lock file edited by hand ----------------------
    # `acquire` refuses production outright, so this is the only way to reach
    # the check inside `require` — and that check is the one that catches a lock
    # written by an older version or edited on disk.
    forged = json.loads(session.lock_path(root).read_bytes().decode("utf-8"))
    forged["is_production"] = "true"
    session.lock_path(root).write_bytes(json.dumps(forged).encode("utf-8"))
    refuses(lambda: session.require(root, [base(is_production="true")], write=True, system="nt"), "production",
            "writing to production must be refused by the lock check as well")

    # --- the managed write switch (№240) ------------------------------------
    #
    # An ordinary application carries its mode in the artifact: a read-only build
    # cannot write, and the hash tells the builds apart. A managed base has one
    # processor and a switch in the Toolkit UI, so the mode is a runtime fact and
    # the only honest way to know it is to ask.
    refuses(lambda: session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev"),
            "write switch",
            "a managed base must not be locked without reading the switch")
    refuses(lambda: session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                                    switch_confirmed="переключатель проверен"),
            "which state was read",
            "a confirmation that names no state is a confirmation of nothing")
    refuses(lambda: session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                                    switch_confirmed="get_write_switch: on"),
            "needs it off",
            "analysis on a base whose switch is on is not analysis")
    refuses(lambda: session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                                    switch_confirmed="get_write_switch: off",
                                    write_mode="approved-write",
                                    backup_confirmed="erp-dev-2026-07-31.dt"),
            "needs it on",
            "an approved write on a base whose switch is off cannot write")

    # An ordinary base has the barrier in the build, so it needs no switch read.
    ordinary = base(application_kind="ordinary")
    session.acquire(root, ordinary, confirmed_by="get_metadata: ERP dev")
    note(session.require(root, [ordinary], system="nt")["application_kind"] == "ordinary",
         "an ordinary base is authorised by the build it runs, not by a switch")

    # A lock that lost its switch read authorises nothing, analysis included:
    # that is exactly the state the criterion is about.
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                    switch_confirmed="get_write_switch: off")
    stripped = json.loads(session.lock_path(root).read_bytes().decode("utf-8"))
    stripped.pop("switch_confirmed")
    session.lock_path(root).write_bytes(json.dumps(stripped).encode("utf-8"))
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "no read of the write switch",
            "a managed lock without the switch read must not authorise even analysis")

    # A lock whose recorded state disagrees with its mode is stale, not usable.
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                    switch_confirmed="get_write_switch: off")
    flipped = json.loads(session.lock_path(root).read_bytes().decode("utf-8"))
    flipped["switch_confirmed"] = "get_write_switch: on"
    session.lock_path(root).write_bytes(json.dumps(flipped).encode("utf-8"))
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "while the lock is in",
            "a switch read that contradicts the lock mode must be refused")

    # --- a lock written before the rule existed is not grandfathered ---------
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_confirmed="get_write_switch: on", write_mode="approved-write",
                    backup_confirmed="erp-dev-2026-07-31.dt")
    without_backup = json.loads(session.lock_path(root).read_bytes().decode("utf-8"))
    without_backup.pop("backup_confirmed")
    session.lock_path(root).write_bytes(json.dumps(without_backup).encode("utf-8"))
    refuses(lambda: session.require(root, REGISTRY, system="nt", write=True), "backup",
            "an old lock carrying no backup evidence must not authorise a write")

    # --- the runtime half is Windows, the repository half is not -------------
    # Half of criterion 18 used to have no executor at all: the rule that live
    # base operations are blocked elsewhere was a sentence in a plan.
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_confirmed="get_write_switch: off")
    refuses(lambda: session.require(root, REGISTRY, system="posix"), "только на Windows",
            "a live-base operation must be refused off Windows")
    note(session.require(root, REGISTRY, system="nt")["project_id"] == "erp",
         "the same lock must work on Windows")
    # And the refusal is about the runtime alone: the lock itself is a file in
    # the repository, and taking it is how a review on macOS prepares the work.
    lock = session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_confirmed="get_write_switch: off")
    note(lock["project_id"] == "erp", "taking a lock must not depend on the platform")

    # --- an unreadable lock is not a lock ------------------------------------
    session.lock_path(root).write_bytes(b"{not json")
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "no session lock",
            "a damaged lock must not be treated as a confirmation")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} session check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("Session lock checks passed.")
