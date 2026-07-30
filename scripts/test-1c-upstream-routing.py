#!/usr/bin/env python3
"""The routing map must cover the pinned upstream, and CI has no checkout of it.

`config/1c-upstream-inventory.txt` is the file list at the pinned commit — the
acceptance checksum the plan names. Checking the map against that list is what
makes "every tracked file has a route" verifiable offline; checking the expansion
against a real git staging is what makes the expansion itself verifiable.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location("import_1c_upstream", SCRIPTS / "import_1c_upstream.py")
assert spec and spec.loader
importer = importlib.util.module_from_spec(spec)
sys.modules["import_1c_upstream"] = importer
spec.loader.exec_module(importer)

agents_spec = importlib.util.spec_from_file_location("one_c_agents", SCRIPTS / "one_c_agents.py")
assert agents_spec and agents_spec.loader
agents_module = importlib.util.module_from_spec(agents_spec)
sys.modules["one_c_agents"] = agents_module
agents_spec.loader.exec_module(agents_module)

INVENTORY = ROOT / "config/1c-upstream-inventory.txt"
EXPECTED_FILES = 241

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def inventory() -> list[str]:
    lines = INVENTORY.read_bytes().decode("utf-8").splitlines()
    return [line for line in lines if line and not line.startswith("#")]


# --- the map covers the pinned upstream, file by file -----------------------

paths = inventory()
note(len(paths) == EXPECTED_FILES,
     f"the pinned inventory must hold {EXPECTED_FILES} files, found {len(paths)}")
note(any(line.startswith("# comol/ai_rules_1c @") for line in
         INVENTORY.read_bytes().decode("utf-8").splitlines()),
     "the inventory must name the commit it was taken at")

routes = importer.read_routing(ROOT)
used: set[str] = set()
for path in paths:
    hit = next((route for route in routes if importer.matches(route["pattern"], path)), None)
    if hit is None:
        failures.append(f"no route for pinned upstream file: {path}")
        continue
    used.add(hit["pattern"])
    # A route that installs something must say where; a route that installs
    # nothing must not pretend to.
    target = importer.target_of(hit, path)
    if hit["action"] == "route":
        note(target == "-", f"{path}: a route produces no output, got '{target}'")
    else:
        note(target not in ("", "-") and "{" not in target,
             f"{path}: unresolved target '{target}'")

for route in routes:
    note(route["pattern"] in used, f"route matches nothing in the pinned upstream: {route['pattern']}")

# Every decision is traceable: a route without the S-decision that put it there
# is a choice nobody can review later.
for route in routes:
    note(route["decision"].startswith("S."), f"{route['pattern']}: decision must reference the plan")

# --- the expansion over a real checkout -------------------------------------

ADAPTER_CODEX = """tool: codex
schemaVersion: 1

agents:
  copyTo: ".codex/agents/{name}.toml"
  mode: rebuild-toml
  template: |
    name = "{name}"
    description = "{description}"
    model = "{modelHint}"
    developer_instructions = \"\"\"
    {body}
    \"\"\"
"""

ADAPTER_CLAUDE = """tool: claude-code
schemaVersion: 1

agents:
  copyTo: ".claude/agents/{name}.md"
  frontmatter:
    keep: [name, description, tools, modelHint]
    rename:
      modelHint: model
    drop: [reasoningEffort]
"""

AGENT = """---
name: 1c-developer
description: "Writes code."
modelTier: build
tools: ["Read", "Write"]
reasoningEffort: high
---

# Developer

Body.
"""

with tempfile.TemporaryDirectory() as raw:
    staging = Path(raw)
    files = {
        # The adapters are the compilation spec: without them a staging cannot
        # produce an agent projection at all.
        "adapters/codex.yaml": ADAPTER_CODEX,
        "adapters/claude-code.yaml": ADAPTER_CLAUDE,
        "USER-RULES.md": "seed\n",
        "content/skills/caveman/SKILL.md": "caveman\n",
        "content/skills/img-grid-analysis/SKILL.md": "grid\n",
        "content/skills/img-grid-analysis/scripts/overlay-grid.py": "print(1)\n",
        "content/agents/developer.md": AGENT,
        "content/skills/transcribe/SKILL.md": "not ours\n",
    }
    for name, body in files.items():
        target = staging / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body.encode("utf-8"))
    subprocess.run(["git", "-C", str(staging), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(staging), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(staging), "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "-qm", "staging"], check=True, capture_output=True,
    )

    rows, problems = importer.expand(ROOT, staging)
    by_path = {}
    for row in rows:
        by_path.setdefault(row["source_path"], []).append(row)

    note(set(by_path) == set(files), f"every staged file must produce a row: {sorted(set(files) - set(by_path))}")

    # The specific route sits above the group route, and the specific one wins.
    grid = by_path["content/skills/img-grid-analysis/scripts/overlay-grid.py"][0]
    note(grid["action"] == "adapt:grid-guards", f"the specific route must win: {grid['action']}")
    note(grid["target_sha256"] == "-", "an adapted output has no hash until it is generated")
    plain = by_path["content/skills/img-grid-analysis/SKILL.md"][0]
    note(plain["action"] == "copy", f"the group route must still apply: {plain['action']}")
    note(plain["target_sha256"] == plain["source_sha256"], "a copy must not change the bytes")
    note(plain["target_path"] == ".agents/skills/img-grid-analysis/SKILL.md",
         f"a skill keeps its layout under the canonical root: {plain['target_path']}")

    # One agent, two client projections: the ledger records each target, so
    # drift in one of them is visible.
    agent = by_path["content/agents/developer.md"]
    note(len(agent) == 2, f"an agent must be projected for both clients, got {len(agent)}")
    note({row["source_selector"] for row in agent} == {"codex", "claude"},
         f"the projections must be told apart by selector: {[row['source_selector'] for row in agent]}")
    note({row["target_path"] for row in agent}
         == {".codex/agents/developer.toml", ".claude/agents/developer.md"},
         f"unexpected agent targets: {[row['target_path'] for row in agent]}")
    # A compiled row carries the hash of what will actually be written, or the
    # ledger records a promise instead of a file.
    note(all(row["target_sha256"] != "-" for row in agent),
         f"an agent projection must carry its output hash: {[row['target_sha256'] for row in agent]}")
    note(len({row["target_sha256"] for row in agent}) == 2,
         "the two projections differ, so their hashes must differ")

    # The output is a function of the two upstream files and nothing else.
    again, _ = importer.expand(ROOT, staging)
    note({(row["source_path"], row["source_selector"], row["target_sha256"]) for row in again}
         == {(row["source_path"], row["source_selector"], row["target_sha256"]) for row in rows},
         "the same input must compile to the same bytes")

    # What the projections actually contain, not merely that they were produced.
    adapter_claude = (staging / "adapters/claude-code.yaml").read_text(encoding="utf-8")
    adapter_codex = (staging / "adapters/codex.yaml").read_text(encoding="utf-8")
    body = (staging / "content/agents/developer.md").read_text(encoding="utf-8")
    claude_text = agents_module.compile_agent(body, adapter_claude, "claude")
    note("model: build" not in claude_text, "modelTier is not kept: it is not in the adapter's keep list")
    note("reasoningEffort" not in claude_text, "a dropped field must not survive the projection")
    note("tools: [\"Read\", \"Write\"]" in claude_text, f"a kept field must survive verbatim: {claude_text[:200]}")
    codex_text = agents_module.compile_agent(body, adapter_codex, "codex")
    note('name = "1c-developer"' in codex_text, f"the template must be filled: {codex_text[:120]}")
    note('description = ""' not in codex_text, "the template supplies the quoting, the value must go in bare")
    note("model = " not in codex_text,
         "a line referencing a value this agent does not declare is dropped, not emitted empty")

    # The rename only shows itself on an agent that declares the renamed field.
    tiered = body.replace("modelTier: build\n", "modelTier: build\nmodelHint: sonnet\n")
    tiered_claude = agents_module.compile_agent(tiered, adapter_claude, "claude")
    note("model: sonnet" in tiered_claude, f"the adapter's rename must be applied: {tiered_claude[:200]}")
    note("modelHint:" not in tiered_claude, "the source name must not survive the rename")
    note('model = "sonnet"' in agents_module.compile_agent(tiered, adapter_codex, "codex"),
         "a declared value must fill its template line")

    # Routed away, not dropped: transcribe belongs to another plan entirely.
    transcribe = by_path["content/skills/transcribe/SKILL.md"][0]
    note(transcribe["action"].startswith("route:") and transcribe["ownership"] == "provider-only",
         f"transcribe must be routed to its own plan: {transcribe}")

    note(any("matches nothing" in problem for problem in problems),
         "routes that match nothing in this staging must be reported")

    # An unrouted file is an error, not a default.
    (staging / "content/rules-new").mkdir(parents=True, exist_ok=True)
    (staging / "content/rules-new/x.md").write_bytes(b"new\n")
    subprocess.run(["git", "-C", str(staging), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(staging), "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "-qm", "new"], check=True, capture_output=True,
    )
    _, problems = importer.expand(ROOT, staging)
    note(any("has no route" in problem for problem in problems),
         f"an unrouted upstream file must be reported: {problems[:3]}")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} routing check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print(f"Routing covers all {len(paths)} pinned upstream files.")
