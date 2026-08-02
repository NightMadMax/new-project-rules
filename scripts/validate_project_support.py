"""Read the capability manifest without importing the validator CLI.

`validate-project.py` has a dash in its name, so it cannot be imported as a
module; this helper exposes the one lookup other scripts need.
"""

from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

# The Toolkit port range, defined once. It was written out in both the
# validator and the client renderer, so widening it in one place produced a
# base the validator accepted and the renderer silently dropped.
ONE_C_PORTS = range(6003, 6013)
# What a base identity may be spelled with, defined once for the same reason.
# These two columns become an MCP server name and a TOML table header, so a
# quote, a dot or a space in them produces a configuration file the client
# cannot parse — including the part of it the user owns. The rule lived in the
# validator only, and the validator is a separate run: the renderer wrote the
# broken file whether or not anyone had validated first.
ONE_C_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifacts_ledger  # noqa: E402

MANIFEST = Path("config/capabilities.tsv")
TEMPLATES = Path("templates/new-project")
POLICIES = {"managed", "seed"}
EXPECTED_FIELDS = (
    "capability", "source", "destination", "root_purpose", "docs_section", "docs_label",
    "payload_class", "policy",
)


class ManifestError(Exception):
    """The capability manifest cannot be read."""


def release_artifacts(contract_root: Path, capability: str) -> list[tuple[str, Path, str, str]]:
    """Return (target, source, payload_class, policy) for one capability."""
    path = contract_root / MANIFEST
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ManifestError(f"Cannot read {MANIFEST}: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if tuple(reader.fieldnames or ()) != EXPECTED_FIELDS:
        raise ManifestError(f"Unexpected header in {MANIFEST}")

    artifacts: list[tuple[str, Path, str, str]] = []
    for number, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ManifestError(f"{MANIFEST}:{number} does not match the header")
        if row["capability"] != capability:
            continue
        if row["payload_class"] not in artifacts_ledger.MANIFEST_PAYLOAD_CLASSES:
            raise ManifestError(f"{MANIFEST}:{number} unknown payload class '{row['payload_class']}'")
        if row["policy"] not in POLICIES:
            raise ManifestError(f"{MANIFEST}:{number} unknown policy '{row['policy']}'")
        artifacts.append((
            row["destination"],
            contract_root / TEMPLATES / row["source"],
            row["payload_class"],
            row["policy"],
        ))
    if not artifacts:
        raise ManifestError(f"No artifacts declared for capability '{capability}'")
    return artifacts
