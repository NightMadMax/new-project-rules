#!/bin/sh
set -eu

# Wire global agent instructions for both Codex and Claude Code without
# duplicating content. Codex reads ~/.codex/AGENTS.md; Claude Code reads
# ~/.claude/CLAUDE.md, which here only imports the Codex file. Safe to re-run.

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
rules_root=$(dirname "$script_dir")
global_src="$rules_root/GLOBAL_AGENT_INSTRUCTIONS.md"

codex_dir="$HOME/.codex"
claude_dir="$HOME/.claude"
codex_file="$codex_dir/AGENTS.md"
claude_file="$claude_dir/CLAUDE.md"
import_line='@~/.codex/AGENTS.md'

mkdir -p "$codex_dir" "$claude_dir"

# 1. Ensure the canonical Codex global instructions exist; never overwrite.
if [ ! -e "$codex_file" ]; then
  if [ -f "$global_src" ]; then
    cp "$global_src" "$codex_file"
    echo "Created $codex_file from GLOBAL_AGENT_INSTRUCTIONS.md"
  else
    echo "Note: $codex_file is missing and GLOBAL_AGENT_INSTRUCTIONS.md was not found." >&2
    echo "Add your global rules to $codex_file before agents can use them." >&2
  fi
else
  echo "Kept existing $codex_file (not overwritten)."
fi

# 2. Point Claude Code at the same file via a one-line import.
if [ -L "$claude_file" ]; then
  rm "$claude_file"
  printf '%s\n' "$import_line" > "$claude_file"
  echo "Replaced symlink $claude_file with an @import."
elif [ ! -e "$claude_file" ]; then
  printf '%s\n' "$import_line" > "$claude_file"
  echo "Created $claude_file importing ~/.codex/AGENTS.md."
elif grep -qF "$import_line" "$claude_file"; then
  echo "Already configured: $claude_file imports ~/.codex/AGENTS.md."
else
  echo "Conflict: $claude_file exists without '$import_line'." >&2
  echo "Keep your existing rules and add this line to $claude_file manually:" >&2
  echo "  $import_line" >&2
  exit 1
fi

echo "Global agent setup complete."
