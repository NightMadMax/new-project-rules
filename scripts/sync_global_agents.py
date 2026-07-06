#!/usr/bin/env python3
"""Read-only inspection and secret-safe diff for global agent instructions."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


MIN_PYTHON = (3, 9)
BEGIN_TEMPLATE = "<!-- new-project-rules:begin schema={schema} -->"
END_MARKER = "<!-- new-project-rules:end -->"
BEGIN_RE = re.compile(r"^<!-- new-project-rules:begin schema=([1-9][0-9]*) -->$")


@dataclass(frozen=True)
class SyncState:
    status: str
    active_path: Path
    portable_path: Path
    schema_version: int
    portable_text: str
    active_text: Optional[str]
    managed_text: Optional[str] = None
    prefix: str = ""
    suffix: str = ""
    detail: str = ""


class SyncConfigError(Exception):
    pass


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").rstrip("\n") + "\n"


def digest(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def read_schema(contract_root: Path) -> int:
    path = contract_root / "STANDARD_VERSION"
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise SyncConfigError(f"Cannot read {path}: {exc}") from exc
    if not re.fullmatch(r"[1-9][0-9]*", raw):
        raise SyncConfigError(f"Invalid STANDARD_VERSION: {path}")
    return int(raw)


def inspect_sync_state(
    portable_path: Path,
    active_path: Path,
    schema_version: int,
) -> SyncState:
    try:
        with portable_path.open(encoding="utf-8", newline="") as handle:
            portable_text = handle.read()
    except OSError as exc:
        raise SyncConfigError(f"Cannot read portable policy {portable_path}: {exc}") from exc
    return inspect_state(portable_text, active_path, schema_version, portable_path)


def extract_managed_region(text: str) -> Optional[str]:
    """Return the normalized text between managed markers, or None if absent/ambiguous."""
    lines = text.splitlines(keepends=True)
    marker_lines = [line.rstrip("\r\n") for line in lines]
    begins = [i for i, line in enumerate(marker_lines) if line.startswith("<!-- new-project-rules:begin")]
    ends = [i for i, line in enumerate(marker_lines) if line == END_MARKER]
    if len(begins) != 1 or len(ends) != 1 or ends[0] <= begins[0]:
        return None
    return normalize("".join(lines[begins[0] + 1:ends[0]]))


def inspect_state(
    portable_text: str,
    active_path: Path,
    schema_version: int,
    portable_path: Optional[Path] = None,
) -> SyncState:
    portable_text = normalize(portable_text)
    if portable_path is None:
        portable_path = Path("<baseline>")

    if not active_path.exists():
        return SyncState("missing", active_path, portable_path, schema_version, portable_text, None)
    try:
        with active_path.open(encoding="utf-8", newline="") as handle:
            active_text = handle.read()
    except OSError as exc:
        raise SyncConfigError(f"Cannot read active policy {active_path}: {exc}") from exc

    lines = active_text.splitlines(keepends=True)
    marker_lines = [line.rstrip("\r\n") for line in lines]
    begins = [(index, BEGIN_RE.fullmatch(line)) for index, line in enumerate(marker_lines) if line.startswith("<!-- new-project-rules:begin")]
    ends = [index for index, line in enumerate(marker_lines) if line == END_MARKER]

    if not begins and not ends:
        status = "legacy_exact" if normalize(active_text) == portable_text else "unmanaged_conflict"
        return SyncState(status, active_path, portable_path, schema_version, portable_text, active_text)
    if len(begins) != 1 or len(ends) != 1 or begins[0][1] is None:
        return SyncState(
            "malformed", active_path, portable_path, schema_version, portable_text, active_text,
            detail=f"begin_markers={len(begins)}, end_markers={len(ends)}",
        )

    begin_index, match = begins[0]
    end_index = ends[0]
    assert match is not None
    block_schema = int(match.group(1))
    if end_index <= begin_index:
        return SyncState(
            "malformed", active_path, portable_path, schema_version, portable_text, active_text,
            detail="end marker appears before begin marker",
        )
    if block_schema != schema_version:
        return SyncState(
            "unsupported_schema", active_path, portable_path, schema_version, portable_text, active_text,
            detail=f"managed_schema={block_schema}, supported_schema={schema_version}",
        )

    managed_text = normalize("".join(lines[begin_index + 1:end_index]))
    prefix = "".join(lines[:begin_index])
    suffix = "".join(lines[end_index + 1:])
    status = "managed_match" if managed_text == portable_text else "managed_drift"
    return SyncState(
        status, active_path, portable_path, schema_version, portable_text, active_text,
        managed_text=managed_text, prefix=prefix, suffix=suffix,
    )


def managed_block(portable_text: str, schema_version: int) -> str:
    return (
        BEGIN_TEMPLATE.format(schema=schema_version)
        + "\n"
        + normalize(portable_text)
        + END_MARKER
        + "\n"
    )


def desired_text(state: SyncState) -> Optional[str]:
    block = managed_block(state.portable_text, state.schema_version)
    if state.status in {"missing", "legacy_exact"}:
        return block
    if state.status in {"managed_match", "managed_drift"}:
        return state.prefix + block + state.suffix
    if state.status == "unmanaged_conflict":
        assert state.active_text is not None
        return normalize(state.active_text) + "\n" + block
    return None


def hash_range(lines: Sequence[str], start: int, end: int) -> str:
    return hashlib.sha256("\n".join(lines[start:end]).encode("utf-8")).hexdigest()[:12]


def secret_safe_diff(state: SyncState) -> str:
    header = [f"status={state.status}", f"active={state.active_path}", f"portable={state.portable_path}"]
    if state.status == "managed_match":
        return "\n".join(header + ["No managed-policy differences."])
    if state.status == "missing":
        lines = normalize(state.portable_text).splitlines()
        return "\n".join(header + [f"Plan: create managed block with {len(lines)} line(s), sha256={digest(state.portable_text)}."])
    if state.status == "legacy_exact":
        lines = normalize(state.portable_text).splitlines()
        return "\n".join(header + [f"Plan: wrap {len(lines)} matching line(s) with managed markers, sha256={digest(state.portable_text)}."])
    if state.status == "unmanaged_conflict":
        assert state.active_text is not None
        return "\n".join(header + [
            f"Active unmanaged policy: {len(state.active_text.splitlines())} line(s), sha256={digest(state.active_text)}.",
            f"Portable policy: {len(state.portable_text.splitlines())} line(s), sha256={digest(state.portable_text)}.",
            "Plan: append managed block below existing content; existing lines are preserved unchanged.",
        ])
    if state.status == "managed_drift":
        active_lines = normalize(state.managed_text or "").splitlines()
        portable_lines = normalize(state.portable_text).splitlines()
        output = header + [
            f"Managed active: {len(active_lines)} line(s), sha256={digest(state.managed_text or '')}.",
            f"Portable expected: {len(portable_lines)} line(s), sha256={digest(state.portable_text)}.",
            "Changed ranges (content redacted):",
        ]
        matcher = difflib.SequenceMatcher(a=active_lines, b=portable_lines, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            output.append(
                f"- {tag}: active[{i1}:{i2}] sha256={hash_range(active_lines, i1, i2)} "
                f"-> portable[{j1}:{j2}] sha256={hash_range(portable_lines, j1, j2)}"
            )
        return "\n".join(output)
    return "\n".join(header + [f"Cannot produce a plan: {state.detail or 'managed markers require review' }."])


def status_message(state: SyncState) -> str:
    messages = {
        "managed_match": "Managed global policy matches the portable source.",
        "managed_drift": "Managed global policy differs from the portable source.",
        "legacy_exact": "Legacy unmanaged policy matches content but has no ownership markers.",
        "unmanaged_conflict": "Unmanaged active policy differs; ownership cannot be inferred safely.",
        "missing": "Active global policy is missing.",
        "malformed": "Managed markers are malformed or duplicated.",
        "unsupported_schema": "Managed block schema is not supported by this rules version.",
    }
    return messages[state.status]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only global agent policy sync inspection.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Print sync state and return 0 only for managed_match.")
    mode.add_argument("--diff", action="store_true", help="Print a secret-safe structural diff without file content.")
    parser.add_argument("--contract-root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--report-only", action="store_true", help="Always return 0 after reporting state.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if sys.version_info < MIN_PYTHON:
        print("Python 3.9+ is required.", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    contract_root = Path(args.contract_root).resolve()
    home = Path(args.home).resolve()
    try:
        schema = read_schema(contract_root)
        state = inspect_sync_state(
            contract_root / "GLOBAL_AGENT_INSTRUCTIONS.md",
            home / ".codex" / "AGENTS.md",
            schema,
        )
    except SyncConfigError as exc:
        print(f"Sync configuration error: {exc}", file=sys.stderr)
        return 0 if args.report_only else 2
    if args.diff:
        print(secret_safe_diff(state))
    else:
        print(f"status={state.status}")
        print(status_message(state))
        if state.detail:
            print(f"detail={state.detail}")
    if args.report_only:
        return 0
    return 0 if state.status == "managed_match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
