#!/usr/bin/env python3
"""Refuse to act on a project whose capability release is not the one here.

Delivery is versioned to the byte: `release_id` is the hash of the release
passport and the ledger together, and `capability_artifacts` refuses to touch a
file whose bytes drifted. Runtime had none of that. `one_c_session`,
`one_c_doctor` and `one_c_provider` are run out of a `new-project-rules`
checkout against a project directory, the two are updated on different days by
different people, and nothing compared them — so the scripts that decide whether
a live infobase may be written could be a different version of the standard than
the one the project installed, silently.

The strictness has to end somewhere, and it should not end at the point where
the tool starts acting on a live system.

Two cases are deliberately not failures:

* **The project has no `1c` capability installed.** Then there is nothing to
  match, and the caller is doing something else (a fresh project, a diagnosis
  before install). Answering "mismatch" there would be noise.
* **The checkout has no release passport.** That is a broken checkout, not a
  broken project, and it is reported as such rather than blamed on the project.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

CAPABILITY = "1c"
PASSPORT = Path("config/1c-release.json")
METADATA = Path(".project-standard.json")


class ReleaseMismatch(Exception):
    """The checkout and the project describe different releases of a capability."""


def _read_json(path: Path) -> Optional[dict]:
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def installed_release(project_root: Path, capability: str = CAPABILITY) -> Optional[str]:
    """The release the project says it installed, or None if it installed none."""
    data = _read_json(project_root / METADATA)
    if data is None:
        return None
    releases = data.get("capability_releases")
    if not isinstance(releases, dict):
        return None
    record = releases.get(capability)
    if not isinstance(record, dict):
        return None
    value = record.get("release_id")
    return value if isinstance(value, str) and value else None


def checkout_release(standard_root: Path, capability: str = CAPABILITY) -> Optional[str]:
    """The release this checkout of the standard carries."""
    data = _read_json(standard_root / PASSPORT)
    if data is None or data.get("capability") != capability:
        return None
    value = data.get("release_id")
    return value if isinstance(value, str) and value else None


def require_matching_release(project_root: Path, standard_root: Path,
                             capability: str = CAPABILITY) -> Optional[str]:
    """Return the agreed release id, or raise naming both sides.

    Returns None when the project has not installed this capability: there is
    nothing to disagree about yet.
    """
    installed = installed_release(project_root, capability)
    if installed is None:
        return None
    here = checkout_release(standard_root, capability)
    if here is None:
        raise ReleaseMismatch(
            f"the project has capability '{capability}' release {installed[:12]} installed, but "
            f"this checkout of the standard carries no readable {PASSPORT.as_posix()}: "
            "the checkout is incomplete, so nothing here can be trusted to match it")
    if here != installed:
        raise ReleaseMismatch(
            f"capability '{capability}': the project installed release {installed[:12]} and this "
            f"checkout of the standard is {here[:12]}. These scripts act on a live infobase, so "
            "the mismatch is refused rather than reported: update the checkout to the project's "
            "release, or update the capability in the project to this one")
    return here
