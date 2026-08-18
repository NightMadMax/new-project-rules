"""Read the capability manifest without importing the validator CLI.

`validate-project.py` has a dash in its name, so it cannot be imported as a
module; this helper exposes the one lookup other scripts need.
"""

from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

# One Toolkit proxy serves every base and separates them by channel (decision
# 1.8, revised 2026-08-18). Both constants are defined once: the port range they
# replace was written out in the validator and in the client renderer, so
# widening it in one place produced a base the validator accepted and the
# renderer silently dropped.
ONE_C_TOOLKIT_PROXY_PORT = 6003
# Channel id charset is fixed by the proxy: a-z, A-Z, 0-9, underscore, hyphen.
ONE_C_TOOLKIT_CHANNEL_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# What a base identity may be spelled with, defined once for the same reason.
# These two columns become an MCP server name and a TOML table header, so a
# quote, a dot or a space in them produces a configuration file the client
# cannot parse — including the part of it the user owns. The rule lived in the
# validator only, and the validator is a separate run: the renderer wrote the
# broken file whether or not anyone had validated first.
ONE_C_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# What may follow a wikilink target: the closing bracket, an alias pipe, or a
# heading anchor. Presence used to be tested with the bare prefix `[[<link>`,
# which makes every link a prefix of every longer one — an index carrying
# `[[docs/quality/DEFECTS_ARCHIVE|…]]` counted as already linking
# `docs/quality/DEFECTS`. The installer then never added the missing entry and
# the validator never reported it missing, because both asked the same wrong
# question. Defined once so they cannot drift apart again.
LINK_TERMINATORS = ("]", "|", "#")
DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


def machine_path(value: str) -> bool:
    """A path that only resolves on the machine that wrote it.

    Both conventions are checked on every host: the repository is prepared on
    macOS and used on Windows, so a check that depends on where it runs would
    let each side through the other's mistake. Defined here because it is a
    fact about paths, not about any one capability.
    """
    return bool(
        PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
        or DRIVE_PATH_RE.match(value)
        or value.startswith("~")
        or ".." in value.replace("\\", "/").split("/")
    )


def link_present(text: str, link: str) -> bool:
    """Whether `text` links exactly `link`, not merely something starting with it."""
    marker = f"[[{link}"
    start = 0
    while True:
        found = text.find(marker, start)
        if found < 0:
            return False
        after = text[found + len(marker): found + len(marker) + 1]
        if after in LINK_TERMINATORS:
            return True
        start = found + len(marker)

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


def manifest_rows(contract_root: Path, capability: str) -> list[dict[str, str]]:
    """Every declared row of one capability, columns unchanged.

    `release_artifacts` answers "what is delivered"; the install also has to
    answer "where is it indexed", and that lives in the same rows.
    """
    path = contract_root / MANIFEST
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ManifestError(f"Cannot read {MANIFEST}: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    if tuple(reader.fieldnames or ()) != EXPECTED_FIELDS:
        raise ManifestError(f"Unexpected header in {MANIFEST}")
    rows = []
    for number, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ManifestError(f"{MANIFEST}:{number} does not match the header")
        if row["capability"] == capability:
            rows.append(dict(row))
    if not rows:
        raise ManifestError(f"No artifacts declared for capability '{capability}'")
    return rows


def release_artifacts(contract_root: Path, capability: str) -> list[tuple[str, Path, str, str]]:
    """Return (target, source, payload_class, policy) for one capability."""
    path = contract_root / MANIFEST
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ManifestError(f"Cannot read {MANIFEST}: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
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
