#!/usr/bin/env python3
"""The session lock has to refuse, and refuse for a nameable reason.

Every case here is a rule that previously existed only as a sentence in a skill:
what a skill does with a sentence depends on the session reading it, which is
the difference between a rule and a check.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
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

# --- the registry is a spreadsheet, and the guards read it literally ---------
# Every barrier compared the raw cell to the lowercase literal. `True` and
# `Managed` — what a spreadsheet writes back — matched neither, so a production
# base read as non-production and a managed base skipped the switch evidence
# that is its only barrier. The result was an approved write on production with
# no switch ever asked. The validator does check the enum, but it is a separate
# run, and a guard that depends on someone having made that run is not a guard.
for spelling in ("True", "TRUE", " true "):
    refuses(
        lambda spelling=spelling: session.acquire(
            root_ignored := Path("."), base(is_production=spelling, application_kind="ordinary"),
            confirmed_by="probe", write_mode="approved-write", backup_confirmed="copy 2026-08-03"),
        "is production",
        f"is_production={spelling!r} must still refuse an approved write")
for spelling in ("Managed", "MANAGED", " managed "):
    refuses(
        lambda spelling=spelling: session.acquire(
            Path("."), base(application_kind=spelling), confirmed_by="probe"),
        "switch",
        f"application_kind={spelling!r} must still demand the switch evidence")
# A value outside the enum is the one case where reading it as "no" is the
# dangerous answer, so it is refused rather than defaulted.
refuses(lambda: session.acquire(Path("."), base(is_production="maybe",
                                                application_kind="ordinary"),
                                confirmed_by="probe"),
        "neither true nor false", "an unreadable is_production must be refused")
refuses(lambda: session.acquire(Path("."), base(application_kind="клиент"),
                                confirmed_by="probe"),
        "neither 'managed' nor 'ordinary'",
        "an unreadable application_kind must be refused")

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)

    # --- nothing confirmed yet ---------------------------------------------
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "no session lock",
            "a live-base operation without a lock must be refused")

    # --- a lock is evidence, not a claim -----------------------------------
    refuses(lambda: session.acquire(root, DEV, confirmed_by=""), "proved the identity",
            "a lock without the call that proved the identity must be refused")

    # --- production is never implied ---------------------------------------
    refuses(lambda: session.acquire(root, PROD, confirmed_by="get_metadata: ERP prod", switch_read="off", switch_confirmed="get_write_switch: off"),
            "production", "production must not be selectable without a named confirmation")
    lock = session.acquire(root, PROD, confirmed_by="get_metadata: ERP prod", switch_read="off", switch_confirmed="get_write_switch: off", production_confirmed=True)
    note(lock["production_confirmed"] is True, "the confirmation must be recorded, not just accepted")
    session.invalidate(root)

    # --- the ordinary path --------------------------------------------------
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_read="off", switch_confirmed="get_write_switch: off")
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
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_read="off", switch_confirmed="get_write_switch: off", now=stale)
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "expired",
            "a lock older than a working session must be re-confirmed")

    # --- selecting again drops the previous confirmation ---------------------
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_read="off", switch_confirmed="get_write_switch: off")
    session.invalidate(root)
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "no session lock",
            "invalidation must leave nothing behind to fall back on")

    # --- an approved write needs a backup that was actually checked ----------
    refuses(lambda: session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_read="off", switch_confirmed="get_write_switch: off",
                                    write_mode="approved-write"),
            "backup", "an approved write without a checked backup must be refused")

    # --- and it is never taken on production, confirmed or not ---------------
    refuses(lambda: session.acquire(root, PROD, confirmed_by="get_metadata: ERP prod", switch_read="off", switch_confirmed="get_write_switch: off",
                                    production_confirmed=True, write_mode="approved-write",
                                    backup_confirmed="erp-prod-2026-07-31.dt"),
            "production", "an approved write on production must be refused outright")

    # --- the ordinary approved write ----------------------------------------
    lock = session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                           switch_read="on", switch_confirmed="get_write_switch: on",
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
            "must be exactly",
            "evidence of a call is not a statement of the state it read")
    # The state is stated, never parsed out of the evidence. This sentence
    # denies the switch was turned on, and the word-matching that used to stand
    # here read it as "on" and opened an approved write (№254).
    refuses(lambda: session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                                    switch_read="I did not turn it on",
                                    switch_confirmed="get_write_switch: off",
                                    write_mode="approved-write",
                                    backup_confirmed="erp-dev-2026-07-31.dt"),
            "must be exactly",
            "a sentence must not be accepted where a state is required")
    # ...and a plainly correct answer in words is refused as a state rather than
    # guessed at: `on` is a preposition, and guessing is what has to stop.
    refuses(lambda: session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                                    switch_read="the switch on the panel reads off",
                                    switch_confirmed="get_write_switch: off"),
            "must be exactly",
            "a state is one of two words, not a sentence to be interpreted")
    refuses(lambda: session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                                    switch_read="on", switch_confirmed="get_write_switch: on"),
            "needs it off",
            "analysis on a base whose switch is on is not analysis")
    refuses(lambda: session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                                    switch_read="off", switch_confirmed="get_write_switch: off",
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
                    switch_read="off", switch_confirmed="get_write_switch: off")
    stripped = json.loads(session.lock_path(root).read_bytes().decode("utf-8"))
    stripped.pop("switch_read")
    session.lock_path(root).write_bytes(json.dumps(stripped).encode("utf-8"))
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "no read of the write switch",
            "a managed lock without the switch read must not authorise even analysis")

    # A lock whose recorded state disagrees with its mode is stale, not usable.
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev",
                    switch_read="off", switch_confirmed="get_write_switch: off")
    flipped = json.loads(session.lock_path(root).read_bytes().decode("utf-8"))
    flipped["switch_read"] = "on"
    session.lock_path(root).write_bytes(json.dumps(flipped).encode("utf-8"))
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "while the lock is in",
            "a switch read that contradicts the lock mode must be refused")

    # --- a lock written before the rule existed is not grandfathered ---------
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_read="on", switch_confirmed="get_write_switch: on", write_mode="approved-write",
                    backup_confirmed="erp-dev-2026-07-31.dt")
    without_backup = json.loads(session.lock_path(root).read_bytes().decode("utf-8"))
    without_backup.pop("backup_confirmed")
    session.lock_path(root).write_bytes(json.dumps(without_backup).encode("utf-8"))
    refuses(lambda: session.require(root, REGISTRY, system="nt", write=True), "backup",
            "an old lock carrying no backup evidence must not authorise a write")

    # --- the runtime half is Windows, the repository half is not -------------
    # Half of criterion 18 used to have no executor at all: the rule that live
    # base operations are blocked elsewhere was a sentence in a plan.
    session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_read="off", switch_confirmed="get_write_switch: off")
    refuses(lambda: session.require(root, REGISTRY, system="posix"), "только на Windows",
            "a live-base operation must be refused off Windows")
    note(session.require(root, REGISTRY, system="nt")["project_id"] == "erp",
         "the same lock must work on Windows")
    # And the refusal is about the runtime alone: the lock itself is a file in
    # the repository, and taking it is how a review on macOS prepares the work.
    lock = session.acquire(root, DEV, confirmed_by="get_metadata: ERP dev", switch_read="off", switch_confirmed="get_write_switch: off")
    note(lock["project_id"] == "erp", "taking a lock must not depend on the platform")

    # --- an unreadable lock is not a lock ------------------------------------
    session.lock_path(root).write_bytes(b"{not json")
    refuses(lambda: session.require(root, REGISTRY, system="nt"), "no session lock",
            "a damaged lock must not be treated as a confirmation")

# --- the executor can be executed (№243) ------------------------------------
#
# The module implemented the lock and nothing could call it: no entry point, no
# wrapper, and no skill naming it. A rule whose executor cannot be run is the
# rule the module was written to replace.

REGISTRY_HEADER = (
    "project_id\tenvironment_id\tfolder\tconfiguration\tplatform_version\tcompatibility_mode\t"
    "application_kind\tsupport_mode\tsource_format\tedt_workspace\tedt_profile\tserver_port\t"
    "is_production\tmcp_enabled\towner\n"
)
REGISTRY_ROW = "erp\tdev\tsrc\tERP\t8.3.27\t-\tmanaged\ton-support\tedt\t-\t-\t6003\tfalse\ttrue\tme\n"


def cli(root: Path, *arguments: str):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "one_c_session.py"), "--root", str(root), *arguments],
        capture_output=True, text=True, encoding="utf-8",
    )


with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    (root / "config").mkdir()
    (root / "config/1c-projects.tsv").write_bytes((REGISTRY_HEADER + REGISTRY_ROW).encode("utf-8"))

    note(cli(root, "show").returncode != 0, "show without a lock must not report success")

    taken = cli(root, "acquire", "--base", "erp/dev", "--confirmed-by", "get_metadata: ERP dev",
                "--switch-read", "off", "--switch-confirmed", "get_write_switch: off")
    note(taken.returncode == 0, f"the CLI must be able to take a lock: {taken.stderr[:200]}")
    note(session.lock_path(root).is_file(), "acquire wrote no lock file")

    # A state the CLI does not know is refused by the parser, before any file is
    # touched: `--switch-read` takes one of two words and nothing else.
    sentence = cli(root, "acquire", "--base", "erp/dev", "--confirmed-by", "call",
                   "--switch-read", "I did not turn it on", "--switch-confirmed", "call")
    note(sentence.returncode != 0, "a sentence must not be accepted as a switch state")

    unknown = cli(root, "acquire", "--base", "ghost/dev", "--confirmed-by", "call",
                  "--switch-read", "off", "--switch-confirmed", "call")
    note(unknown.returncode != 0, "a base outside the registry must be refused")
    note("registry" in unknown.stderr, f"the refusal must say why: {unknown.stderr[:200]}")

    writing = cli(root, "require", "--base", "erp/dev", "--write")
    note(writing.returncode != 0, "a write against an analysis lock must be refused")
    note("[REFUSED]" in writing.stderr, f"a refusal must be recognisable: {writing.stderr[:200]}")

    note(cli(root, "release").returncode == 0, "release must succeed")
    note(not session.lock_path(root).exists(), "release left the lock behind")
    note(cli(root, "require").returncode != 0, "require without a lock must refuse")


if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} session check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("Session lock checks passed.")
