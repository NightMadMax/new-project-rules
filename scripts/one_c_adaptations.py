#!/usr/bin/env python3
"""Adaptations: the few upstream files this standard may not take verbatim.

An adaptation is allowed only where a decision of the plan conflicts with the
upstream text, and it is written as exact replacements rather than as a diff.
Two reasons, and both are about the day upstream changes:

* **A replacement must match exactly once.** Zero matches means the sentence it
  was written against is gone, and applying the rest would produce a file nobody
  reviewed. More than one match means the anchor is ambiguous and the patch
  would land in a place nobody chose. Both stop the build instead of guessing.
* **The reason travels with the change.** Each file carries the decision that
  allows it and the sentence explaining what would break otherwise, so a
  reviewer a year later does not have to reconstruct the argument from a diff.
"""

from __future__ import annotations

import json
from pathlib import Path

ADAPTATIONS_DIRECTORY = "config/1c-adaptations"
REQUIRED_FIELDS = ("source_path", "decision", "reason", "replacements")


class AdaptationError(Exception):
    """An adaptation is malformed or no longer applies to its source."""


def load(contract_root: Path, action_id: str) -> dict:
    path = contract_root / ADAPTATIONS_DIRECTORY / f"{action_id}.json"
    if not path.is_file():
        raise AdaptationError(f"no adaptation declared for '{action_id}'")
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        raise AdaptationError(f"{action_id}: unreadable adaptation: {error}") from error
    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        raise AdaptationError(f"{action_id}: missing {', '.join(missing)}")
    if not isinstance(data["replacements"], list):
        raise AdaptationError(f"{action_id}: replacements must be a list")
    for position, replacement in enumerate(data["replacements"]):
        if not isinstance(replacement, dict) or set(replacement) != {"find", "replace"}:
            raise AdaptationError(f"{action_id}: replacements[{position}] must hold find and replace")
        if not replacement["find"]:
            raise AdaptationError(f"{action_id}: replacements[{position}] has an empty anchor")
    return data


def apply(text: str, adaptation: dict, action_id: str) -> str:
    for position, replacement in enumerate(adaptation["replacements"]):
        found = text.count(replacement["find"])
        if found != 1:
            raise AdaptationError(
                f"{action_id}: replacements[{position}] matches {found} times, expected exactly one — "
                "the upstream text it was written against has changed and needs review"
            )
        text = text.replace(replacement["find"], replacement["replace"])
    return text


def adapt(contract_root: Path, action_id: str, source_path: str, text: str) -> str:
    adaptation = load(contract_root, action_id)
    if adaptation["source_path"] != source_path:
        raise AdaptationError(
            f"{action_id}: declared for {adaptation['source_path']}, applied to {source_path}"
        )
    return apply(text, adaptation, action_id)
