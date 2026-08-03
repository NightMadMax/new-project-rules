"""What installing a capability is, besides copying its files.

The artifact handler delivers files and records them in the ledger. That is
half of an install: bootstrap also writes the capability into the project
metadata, links the new documents from both indexes and connects the practice
stack the capability cannot exist without. Running the handler alone therefore
produced a project whose files were installed and whose metadata said the
capability was not there — and the validator, correctly, called that a *removed*
capability and told the user to recreate the project they had just extended
(№242).

So the record is computed here and handed to the handler as part of the same
transaction. Three rules:

* **Refuse before writing, not after.** A capability whose minimum profile the
  project does not meet cannot be installed by adding files: the documents its
  index step needs belong to the profile. That is a blocker, not a repair.
* **Add a line, never rewrite a document.** The indexes and the practice
  manifest belong to the project. An entry that is already there is left alone,
  and everything around it is preserved byte for byte.
* **Record the release that was installed.** `capability_releases` existed in
  the schema, was validated, and had no writer at all, so the field on which the
  update story rests was empty in every project ever created (№244). It is
  written here, from the release passport, or not claimed at all.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import best_practices_manifest  # noqa: E402
import project_metadata  # noqa: E402
from validate_project_support import link_present  # noqa: E402
import validate_project_support as support  # noqa: E402

METADATA = ".project-standard.json"
PRACTICES = ".best-practices.json"
INDEX = "INDEX.md"
DOCS_INDEX = "docs/README.md"


class InstallError(Exception):
    """The install cannot proceed, and this says what would have to change."""


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InstallError(f"Cannot read {path.name}: {exc}") from exc


def encode_json(data: object) -> bytes:
    """The spelling every other writer of these files uses."""
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def release_record(contract_root: Path, capability: str) -> dict[str, str] | None:
    """Version and release_id of the capability being installed, if it has a passport."""
    path = contract_root / "config" / f"{capability}-release.json"
    if not path.is_file():
        return None
    passport = read_json(path)
    if not isinstance(passport, dict):
        raise InstallError(f"{path.name} is not a JSON object")
    version, release_id = passport.get("version"), passport.get("release_id")
    if not isinstance(version, str) or not project_metadata.SEMVER_RE.fullmatch(version):
        raise InstallError(f"{path.name} has no SemVer version to record")
    if not isinstance(release_id, str) or not project_metadata.RELEASE_ID_RE.fullmatch(release_id):
        raise InstallError(f"{path.name} has no release_id to record")
    return {"version": version, "release_id": release_id}


def link_target(destination: str) -> str:
    return destination[:-3] if destination.endswith(".md") else destination


def newline_of(text: str) -> str:
    """The line ending the file already uses.

    These files belong to the project, and adding a line is not a reason to
    rewrite every other one: a project created on Windows may hold CRLF, and a
    whole-file re-ending would read as a change nobody made.
    """
    return "\r\n" if "\r\n" in text else "\n"


def index_document(current: str, rows: list[dict[str, str]]) -> str | None:
    """`INDEX.md` with the capability's root documents listed, or None if unchanged."""
    end = newline_of(current)
    added = []
    for row in rows:
        if row["root_purpose"] == "-":
            continue
        link = link_target(row["destination"])
        if link_present(current, link) or link_present("".join(added), link):
            continue
        added.append(f"| [[{link}|{row['destination']}]] | {row['root_purpose']} |{end}")
    if not added:
        return None
    body = current if current.endswith(("\n", "\r")) else current + end
    return body + "".join(added)


def docs_index_document(current: str, rows: list[dict[str, str]]) -> str | None:
    """`docs/README.md` with the capability's documents under their sections.

    An entry goes into the section that is already there. A second heading with
    the same name splits the index, and a reader then trusts whichever half they
    saw first — the rule bootstrap follows, kept identical here.
    """
    end = newline_of(current)
    text = current
    changed = False
    for row in rows:
        if row["docs_section"] == "-":
            continue
        link = link_target(row["destination"])
        if link_present(text, link):
            continue
        entry = f"- [[{link}|{row['docs_label']}]]"
        heading = f"## {row['docs_section']}"
        # `keepends` so every other line keeps the terminator it had. Rejoining
        # with one chosen ending rewrote the whole file when a single CRLF line
        # was present, and `splitlines()` without it also swallows the other
        # characters it treats as breaks — a form feed disappeared from a file
        # this function claims to preserve byte for byte around its own edit.
        lines = text.splitlines(keepends=True)
        stripped = [line.rstrip("\r\n") for line in lines]
        if heading in stripped:
            start = stripped.index(heading)
            stop = start + 1
            while stop < len(lines) and not stripped[stop].startswith("## "):
                stop += 1
            last = start
            for position in range(start + 1, stop):
                if stripped[position].startswith("- "):
                    last = position
            at = last + 1 if last > start else start + 2
            # The new line takes the ending of the line it follows, so a CRLF
            # section stays CRLF and an LF section stays LF.
            neighbour = lines[at - 1] if 0 < at <= len(lines) else ""
            local_end = "\r\n" if neighbour.endswith("\r\n") else ("\n" if neighbour.endswith("\n") else end)
            lines.insert(at, entry + local_end)
            text = "".join(lines)
            if not text.endswith(("\n", "\r")):
                text += end
        else:
            body = text if text.endswith(("\n", "\r")) else text + end
            text = f"{body}{end}{heading}{end}{end}{entry}{end}"
        changed = True
    return text if changed else None


def metadata_document(current: dict, capability: str, record: dict[str, str] | None) -> bytes | None:
    capabilities = list(current.get("capabilities") or [])
    releases = dict(current.get("capability_releases") or {})
    desired = dict(current)
    changed = False
    if capability not in capabilities:
        capabilities.append(capability)
        desired["capabilities"] = capabilities
        changed = True
    if record is not None and releases.get(capability) != record:
        releases[capability] = record
        desired["capability_releases"] = releases
        changed = True
    return encode_json(desired) if changed else None


def practices_document(current: object, stack: str) -> bytes | None:
    """The practice stack a capability requires, connected but never forced on.

    `ask` is the value bootstrap writes: the stack is connected and the person
    still decides per case. An explicit `optout` is left as it is — overriding a
    refusal would be the install deciding something the user already decided —
    and reported as a blocker instead.
    """
    manifest = current if isinstance(current, dict) else best_practices_manifest.empty_manifest()
    preferences = manifest.setdefault("preferences", {})
    sections = preferences.setdefault("sections", {})
    if sections.get(stack) == "optout" or preferences.get("global") == "optout":
        raise InstallError(
            f"the practice stack '{stack}' is declined in {PRACTICES}, and this capability "
            "cannot exist without it; change that choice first"
        )
    if sections.get(stack):
        return None
    sections[stack] = "ask"
    preferences.setdefault("global", "ask")
    return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def documents(project_root: Path, contract_root: Path, capability: str) -> list[tuple[str, bytes]]:
    """Every project file the install has to touch, with its new content."""
    metadata_path = project_root / METADATA
    if not metadata_path.is_file():
        raise InstallError(
            f"{METADATA} is missing, so this directory does not state what it is; "
            "capabilities are installed into projects created from the standard"
        )
    metadata = read_json(metadata_path)
    if not isinstance(metadata, dict):
        raise InstallError(f"{METADATA} is not a JSON object")

    profile = metadata.get("profile")
    minimum = project_metadata.CAPABILITY_MIN_PROFILE.get(capability)
    ranks = project_metadata.PROFILE_RANKS
    if minimum and profile in ranks and ranks[profile] < ranks[minimum]:
        raise InstallError(
            f"capability '{capability}' needs profile '{minimum}' and this project is "
            f"'{profile}'. Adding files cannot raise a profile: the documents its index "
            "step needs belong to the profile, and they are not here"
        )

    result: list[tuple[str, bytes]] = []
    rows = support.manifest_rows(contract_root, capability)

    body = metadata_document(metadata, capability, release_record(contract_root, capability))
    if body is not None:
        result.append((METADATA, body))

    stack = project_metadata.CAPABILITY_REQUIRED_STACK.get(capability)
    if stack:
        practices_path = project_root / PRACTICES
        current = read_json(practices_path) if practices_path.is_file() else None
        practices = practices_document(current, stack)
        if practices is not None:
            result.append((PRACTICES, practices))

    index_path = project_root / INDEX
    if index_path.is_file():
        updated = index_document(index_path.read_bytes().decode("utf-8"), rows)
        if updated is not None:
            result.append((INDEX, updated.encode("utf-8")))

    docs_path = project_root / DOCS_INDEX
    if any(row["docs_section"] != "-" for row in rows):
        if not docs_path.is_file():
            raise InstallError(
                f"{DOCS_INDEX} is missing and this capability indexes documents there; "
                "the file belongs to the profile, so the profile is what is missing"
            )
        updated = docs_index_document(docs_path.read_bytes().decode("utf-8"), rows)
        if updated is not None:
            result.append((DOCS_INDEX, updated.encode("utf-8")))

    return result
