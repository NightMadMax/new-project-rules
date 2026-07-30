#!/usr/bin/env python3
"""Compile upstream agent definitions into the two client projections.

The upstream adapters already describe the transformation — `.codex/agents/*.toml`
is rebuilt from a template, `.claude/agents/*.md` keeps a named subset of the
frontmatter with one rename — so the spec is read from them rather than restated
here. Restating it would create a second canon that drifts the first time
upstream changes a field name.

Determinism is the contract: the same agent and the same adapter must produce
byte-identical output, because the ledger records the output hash and a release
identifier that changes without an input change is worthless.

Only the slice of YAML the adapters use is parsed. A dependency on a YAML
library for four keys would be a dependency the created project also has to
carry, and the plan keeps build inputs out of the project.
"""

from __future__ import annotations

import re
from pathlib import Path

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.S)
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_]+)\}")


class AgentError(Exception):
    """An agent definition or an adapter cannot be compiled."""


def split_document(text: str) -> tuple[dict[str, str], str]:
    """Frontmatter as written, plus the body. Values keep their source form.

    Re-quoting a value would change bytes that upstream chose, and the ledger
    would record our formatting rather than their content.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise AgentError("agent definition has no frontmatter")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line[:1].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, match.group(2)


def adapter_section(text: str, section: str) -> dict[str, object]:
    """The one block of an adapter we need, from the YAML subset it uses."""
    lines = text.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.rstrip() == f"{section}:")
    except StopIteration:
        raise AgentError(f"adapter has no '{section}' section") from None

    block: dict[str, object] = {}
    # (indent, mapping) from outermost to innermost: `frontmatter:` opens one
    # level and `rename:` another, and a key at the outer indent has to return
    # to the outer mapping rather than all the way to the section.
    stack: list[tuple[int, dict[str, object]]] = []
    index = start + 1
    while index < len(lines):
        line = lines[index]
        if line and not line[:1].isspace():
            break
        stripped = line.strip()
        index += 1
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if ":" not in stripped:
            continue
        # Which mapping this key belongs to. Without this `keep` and `rename`
        # land beside `frontmatter` instead of inside it, and the kept fields
        # read as empty.
        while stack and indent <= stack[-1][0]:
            stack.pop()
        container: dict[str, object] = stack[-1][1] if stack else block
        key, value = (part.strip() for part in stripped.split(":", 1))
        if value == "|":
            # A block scalar: everything indented deeper, dedented by its own
            # first line, with the trailing newline the block form implies.
            body, base = [], None
            while index < len(lines):
                candidate = lines[index]
                if candidate.strip() and len(candidate) - len(candidate.lstrip()) <= indent:
                    break
                if base is None and candidate.strip():
                    base = len(candidate) - len(candidate.lstrip())
                body.append(candidate[base:] if base is not None and candidate.strip() else "")
                index += 1
            container[key] = "\n".join(body).rstrip("\n") + "\n"
            continue
        if value.startswith("[") and value.endswith("]"):
            container[key] = [item.strip() for item in value[1:-1].split(",") if item.strip()]
            continue
        if value:
            container[key] = value.strip('"')
            continue
        # A nested mapping: `frontmatter:` and `rename:` are the only ones.
        opened: dict[str, object] = {}
        container[key] = opened
        stack.append((indent, opened))
    return block


def compile_claude(fields: dict[str, str], body: str, spec: dict[str, object]) -> str:
    frontmatter = spec.get("frontmatter", {})
    keep = list(frontmatter.get("keep", [])) if isinstance(frontmatter, dict) else []
    rename = frontmatter.get("rename", {}) if isinstance(frontmatter, dict) else {}
    lines = ["---"]
    for key in fields:
        if key not in keep:
            continue
        lines.append(f"{rename.get(key, key)}: {fields[key]}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip("\n")


def compile_codex(fields: dict[str, str], body: str, spec: dict[str, object]) -> str:
    template = spec.get("template")
    if not isinstance(template, str):
        raise AgentError("the codex adapter has no agent template")
    # The template supplies the quoting, so the value goes in bare: keeping the
    # source quotes would emit `description = ""…""`.
    values = {key: value.strip('"') for key, value in fields.items()}
    values["body"] = body.strip("\n")
    rendered = []
    for line in template.splitlines():
        names = PLACEHOLDER_RE.findall(line)
        # The adapter states it: a line referencing a value this agent does not
        # declare is dropped, not emitted with a hole in it.
        if any(name not in values for name in names):
            continue
        rendered.append(PLACEHOLDER_RE.sub(lambda match: values[match.group(1)], line))
    return "\n".join(rendered).rstrip("\n") + "\n"


def compile_agent(agent_text: str, adapter_text: str, client: str) -> str:
    fields, body = split_document(agent_text)
    spec = adapter_section(adapter_text, "agents")
    if client == "claude":
        return compile_claude(fields, body, spec)
    if client == "codex":
        return compile_codex(fields, body, spec)
    raise AgentError(f"unknown client: {client}")


def target_for(agent_path: Path, adapter_text: str) -> str:
    spec = adapter_section(adapter_text, "agents")
    pattern = spec.get("copyTo")
    if not isinstance(pattern, str):
        raise AgentError("the adapter does not say where agents go")
    return pattern.replace("{name}", agent_path.stem)
