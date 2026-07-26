#!/usr/bin/env python3
"""Tests for scripts/artifacts_ledger.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "artifacts_ledger.py"
spec = importlib.util.spec_from_file_location("artifacts_ledger", SCRIPT)
assert spec and spec.loader
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)

DIGEST = "sha256:" + "0" * 64
failures: list[str] = []


def entry(**overrides) -> dict:
    base = {
        "target": "config/1c-mcp-catalog.json",
        "owner": "capability:1c",
        "policy": "managed",
        "payload_class": "verbatim",
        "hash": DIGEST,
    }
    base.update(overrides)
    return base


def document(entries: list[dict], schema: int = ledger.LEDGER_SCHEMA) -> dict:
    return {"schema_version": schema, "artifacts": entries}


def case(name: str, data: object, expect: str | None, known_owners=()) -> None:
    issues = ledger.validate_ledger(data, known_owners)
    if expect is None:
        if issues:
            failures.append(f"{name}: expected no issues, got {issues}")
    elif not any(expect in issue for issue in issues):
        failures.append(f"{name}: expected an issue containing '{expect}', got {issues}")


case("healthy ledger", document([entry()]), None)
case("empty ledger", document([]), None)
case("root is not an object", ["artifacts"], "must be a JSON object")
case("schema missing", {"artifacts": []}, "schema_version must be a positive integer")
case("schema is boolean", document([], schema=True), "positive integer")
case("schema from the future", document([], schema=ledger.LEDGER_SCHEMA + 1), "newer than supported")
case("schema from the past", document([], schema=0), "positive integer")
case("unknown top-level key", {"schema_version": 1, "artifacts": [], "extra": 1}, "unknown keys")
case("artifacts is not a list", {"schema_version": 1, "artifacts": {}}, "must be an array")

case("entry is not an object", document(["x"]), "must be a JSON object")
case("unknown entry field", document([dict(entry(), extra=1)]), "unknown fields")
case("missing entry field", document([{"target": "a"}]), "is missing fields")

case("absolute target", document([entry(target="/etc/hosts")]), "safe repository-relative path")
case("escaping target", document([entry(target="../outside.md")]), "safe repository-relative path")
case("backslash target", document([entry(target="config\\file.json")]), "safe repository-relative path")
case("drive-letter target", document([entry(target="C:/file.json")]), "safe repository-relative path")
case("padded target", document([entry(target=" config/a.json ")]), "safe repository-relative path")
case("empty target", document([entry(target="")]), "safe repository-relative path")

case("unknown owner format", document([entry(owner="me")]), "must be 'standard' or 'capability:<id>'")
case("owner not in the known set", document([entry(owner="capability:ghost")]), "owner is unknown", ("capability:1c",))
case("known owner passes", document([entry()]), None, ("capability:1c", "standard"))

case("unknown policy", document([entry(policy="mystery")]), "policy must be one of")
case("unknown payload class", document([entry(payload_class="mystery")]), "payload_class must be one of")
case("seed with a hash", document([entry(policy="seed")]), "hash must be null for a seed")
case("seed without a hash", document([entry(policy="seed", hash=None)]), None)
case("managed without a hash", document([entry(hash=None)]), "sha256:<64 hex>")
case("short hash", document([entry(hash="sha256:abc")]), "sha256:<64 hex>")
case("hash without prefix", document([entry(hash="0" * 64)]), "sha256:<64 hex>")
case(
    "owned-block policy needs its payload class",
    document([entry(policy="owned-block", payload_class="template")]),
    "must use payload_class owned-block",
)
case(
    "owned-block payload needs its policy",
    document([entry(policy="managed", payload_class="owned-block")]),
    "must use policy owned-block",
)
case("owned block is consistent", document([entry(policy="owned-block", payload_class="owned-block")]), None)

case(
    "duplicate targets",
    document([entry(target="a.json"), entry(target="a.json")]),
    "must not repeat a target",
)
case(
    "unsorted targets",
    document([entry(target="b.json"), entry(target="a.json")]),
    "must be sorted by target",
)

built = ledger.build_ledger([entry(target="b.json"), entry(target="a.json")])
if [item["target"] for item in built["artifacts"]] != ["a.json", "b.json"]:
    failures.append("build_ledger(): entries must be sorted by target")
if ledger.validate_ledger(built):
    failures.append("build_ledger(): output must validate")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} artifacts ledger test(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All artifacts ledger tests passed.")
