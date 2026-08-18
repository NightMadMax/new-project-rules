#!/usr/bin/env python3
"""Validation the `1c` capability owns, kept out of the core validator.

The core answers "does this project match its profile". Which columns an
infobase registry has, which values its enums allow and which channels the Toolkit
may use are facts about one capability, and they lived in `validate-project.py`
— so a second capability with a registry of its own would have added a second
such block to a file that is supposed to know nothing about either.

The seam is deliberately small: this module returns plain tuples and the core
turns them into its own findings through a registry of one row per capability.
That is enough for a second capability to arrive without touching the core, and
it stops short of inventing a validation DSL for a second consumer that does not
exist yet.
"""

from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_project_support  # noqa: E402
from validate_project_support import machine_path  # noqa: E402

ONE_C_REGISTRY = "config/1c-projects.tsv"
ONE_C_REGISTRY_FIELDS = (
    "project_id", "environment_id", "folder", "configuration", "platform_version",
    "compatibility_mode", "application_kind", "support_mode", "source_format",
    "edt_workspace", "edt_profile", "toolkit_channel", "is_production", "mcp_enabled", "owner",
)
ONE_C_ENUMS = {
    "application_kind": {"ordinary", "managed"},
    "support_mode": {"on-support", "partially", "off-support"},
    "source_format": {"edt", "designer-xml"},
    "is_production": {"true", "false"},
    "mcp_enabled": {"true", "false"},
}
ONE_C_CHANNEL_RE = validate_project_support.ONE_C_TOOLKIT_CHANNEL_RE
ONE_C_REQUIRED = ("project_id", "environment_id", "folder", "configuration")
ONE_C_ID_RE = validate_project_support.ONE_C_ID_RE


def check_registry(root: Path) -> list[tuple[str, str, str, str]]:
    """The registry of infobases: identity, Toolkit channels and no credentials.

    Every rule here exists because getting it wrong is expensive at runtime: a
    duplicate identity makes "which base" ambiguous, a shared port sends an
    operation to the wrong infobase, and a credential column would put a
    password into Git.
    """
    path = root / ONE_C_REGISTRY
    if not path.is_file():
        return []
    try:
        # The registry is a TSV people open in a spreadsheet, which is where a
        # BOM comes from; quoting is not a TSV convention, so a value that
        # starts with a quote must stay the value it is.
        text = path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return [("ERROR", "registry.unreadable", f"Cannot read the 1C registry: {exc}", ONE_C_REGISTRY)]

    reader = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    header = tuple(reader.fieldnames or ())
    # The known columns are a prefix, not the whole header: the standard adds
    # columns over time and a project may keep its own after them, and this file
    # belongs to the project, so nothing can rewrite it on upgrade.
    if header[:len(ONE_C_REGISTRY_FIELDS)] != ONE_C_REGISTRY_FIELDS:
        return [(
            "ERROR", "registry.header",
            f"{ONE_C_REGISTRY} header must start with: {', '.join(ONE_C_REGISTRY_FIELDS)}.",
            ONE_C_REGISTRY,
        )]

    findings: list[tuple[str, str, str, str]] = []
    identities: set[tuple[str, str]] = set()
    channels: dict[str, str] = {}
    for row in reader:
        where = f"{ONE_C_REGISTRY}:{reader.line_num}"
        if None in row or any(value is None for value in row.values()):
            findings.append(("ERROR", "registry.row", f"{where} does not match the header.", ONE_C_REGISTRY))
            continue

        for column in ONE_C_REQUIRED:
            if not row[column]:
                findings.append((
                    "ERROR", "registry.value", f"{where} column '{column}' must not be empty.", ONE_C_REGISTRY,
                ))
        for column in ("project_id", "environment_id"):
            # These two become a base name and an MCP namespace downstream, so a
            # space or a slash here breaks routing after installation.
            if row[column] and not ONE_C_ID_RE.fullmatch(row[column]):
                findings.append((
                    "ERROR", "registry.value",
                    f"{where} column '{column}' must match {ONE_C_ID_RE.pattern}.", ONE_C_REGISTRY,
                ))

        identity = (row["project_id"], row["environment_id"])
        if identity in identities:
            findings.append((
                "ERROR", "registry.duplicate",
                f"{where} repeats the identity {identity[0]}/{identity[1]}.", ONE_C_REGISTRY,
            ))
        identities.add(identity)

        for column, allowed in ONE_C_ENUMS.items():
            if row[column] not in allowed:
                findings.append((
                    "ERROR", "registry.value",
                    f"{where} column '{column}' must be one of {', '.join(sorted(allowed))}.", ONE_C_REGISTRY,
                ))

        if row["mcp_enabled"] == "true":
            channel = row["toolkit_channel"]
            if not ONE_C_CHANNEL_RE.match(channel):
                findings.append((
                    "ERROR", "registry.channel",
                    f"{where} exposes MCP and needs a Toolkit channel of 1-64 characters "
                    "from a-z, A-Z, 0-9, '_' or '-'.",
                    ONE_C_REGISTRY,
                ))
            elif channel in channels:
                findings.append((
                    "ERROR", "registry.channel",
                    f"{where} shares channel {channel} with {channels[channel]}; "
                    "an operation would reach the wrong infobase.",
                    ONE_C_REGISTRY,
                ))
            else:
                channels[channel] = f"{row['project_id']}/{row['environment_id']}"
        elif row["toolkit_channel"]:
            findings.append((
                "ERROR", "registry.channel",
                f"{where} does not expose MCP, so its Toolkit channel must stay empty.", ONE_C_REGISTRY,
            ))

        for column in ("edt_workspace", "edt_profile", "folder"):
            if row[column] not in ("", "-") and machine_path(row[column]):
                findings.append((
                    "ERROR", "registry.path",
                    f"{where} column '{column}' must not hold a machine path.", ONE_C_REGISTRY,
                ))

    # The ten-base ceiling went away with the port range (decision 1.8, revised
    # 2026-08-18): one proxy serves every channel, so the number of exposed bases
    # is no longer bounded by the topology and there is nothing left to count.
    # Uniqueness of the channel is checked per row above and remains the thing
    # that keeps an operation from reaching the wrong infobase.
    return findings


