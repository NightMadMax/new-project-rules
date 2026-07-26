"""Read the capability manifest without importing the validator CLI.

`validate-project.py` has a dash in its name, so it cannot be imported as a
module; this helper exposes the one lookup other scripts need.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

MANIFEST = Path("config/capabilities.tsv")
TEMPLATES = Path("templates/new-project")
EXPECTED_FIELDS = (
    "capability", "source", "destination", "root_purpose", "docs_section", "docs_label",
    "payload_class",
)


class ManifestError(Exception):
    """The capability manifest cannot be read."""


def release_artifacts(contract_root: Path, capability: str) -> list[tuple[str, Path, str]]:
    """Return (target, source, payload_class) for one capability."""
    path = contract_root / MANIFEST
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ManifestError(f"Cannot read {MANIFEST}: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if tuple(reader.fieldnames or ()) != EXPECTED_FIELDS:
        raise ManifestError(f"Unexpected header in {MANIFEST}")

    artifacts: list[tuple[str, Path, str]] = []
    for number, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ManifestError(f"{MANIFEST}:{number} does not match the header")
        if row["capability"] != capability:
            continue
        artifacts.append((
            row["destination"],
            contract_root / TEMPLATES / row["source"],
            row["payload_class"],
        ))
    if not artifacts:
        raise ManifestError(f"No artifacts declared for capability '{capability}'")
    return artifacts
