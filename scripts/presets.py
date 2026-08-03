"""Resolve a creation preset into profile, capabilities and practice stacks.

A preset is a name a person uses when creating a project; the project itself
stores only what the preset expanded into. Keeping the expansion declarative
means adding a preset is a row in `config/presets.tsv`, not a code change, and
both bootstrap implementations resolve it the same way.
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import best_practices_manifest  # noqa: E402
import project_metadata  # noqa: E402

MANIFEST = Path("config/presets.tsv")
EXPECTED_FIELDS = ("preset", "min_profile", "capabilities", "best_practices")


class PresetError(Exception):
    """The preset manifest or the requested preset is invalid."""


def read_presets(contract_root: Path) -> dict[str, dict[str, str]]:
    path = contract_root / MANIFEST
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PresetError(f"Cannot read {MANIFEST}: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    if tuple(reader.fieldnames or ()) != EXPECTED_FIELDS:
        raise PresetError(f"Unexpected header in {MANIFEST}")

    presets: dict[str, dict[str, str]] = {}
    for number, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise PresetError(f"{MANIFEST}:{number} does not match the header")
        if row["preset"] in presets:
            raise PresetError(f"{MANIFEST}:{number} duplicate preset '{row['preset']}'")
        if row["min_profile"] not in project_metadata.PROFILE_RANKS:
            raise PresetError(f"{MANIFEST}:{number} unknown profile '{row['min_profile']}'")
        for capability in split(row["capabilities"]):
            if capability not in project_metadata.CAPABILITY_NAMES:
                raise PresetError(f"{MANIFEST}:{number} unknown capability '{capability}'")
        for stack in split(row["best_practices"]):
            if stack not in best_practices_manifest.ALLOWED_SECTIONS:
                raise PresetError(f"{MANIFEST}:{number} unknown practice stack '{stack}'")
        presets[row["preset"]] = row
    if not presets:
        raise PresetError(f"{MANIFEST} declares no presets")
    return presets


def split(value: str) -> list[str]:
    return [item for item in value.split(",") if item and item != "-"]


def resolve(
    contract_root: Path,
    preset: str,
    profile: str,
    capabilities: list[str],
) -> tuple[str, list[str], list[str]]:
    """Return (profile, capabilities, best_practices) after expanding a preset.

    The profile is raised to the preset floor rather than rejected: a person who
    asks for `1c` with a lighter profile means the preset, not a downgrade.
    """
    presets = read_presets(contract_root)
    if preset not in presets:
        raise PresetError(f"Unknown preset '{preset}'")
    row = presets[preset]

    ranks = project_metadata.PROFILE_RANKS
    if profile not in ranks:
        raise PresetError(f"Unknown profile '{profile}'")
    if ranks[profile] < ranks[row["min_profile"]]:
        profile = row["min_profile"]

    merged = list(capabilities)
    for capability in split(row["capabilities"]):
        if capability not in merged:
            merged.append(capability)
    return profile, merged, split(row["best_practices"])
