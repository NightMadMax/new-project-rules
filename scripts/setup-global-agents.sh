#!/bin/sh
set -eu

# Wire global agent instructions for both Codex and Claude Code without
# duplicating content. Codex reads ~/.codex/AGENTS.md; Claude Code reads
# ~/.claude/CLAUDE.md, which here only imports the Codex file. Safe to re-run.

resolve_script_dir() {
  case $0 in
    */*) script_path=$0 ;;
    *) script_path=$(command -v "$0") || {
      echo "Cannot resolve script path: $0" >&2
      exit 1
    } ;;
  esac

  while [ -L "$script_path" ]; do
    link_dir=$(CDPATH= cd -P "$(dirname "$script_path")" && pwd) || exit 1
    link_target=$(readlink "$script_path") || {
      echo "Cannot read script symlink: $script_path" >&2
      exit 1
    }
    case $link_target in
      /*) script_path=$link_target ;;
      *) script_path=$link_dir/$link_target ;;
    esac
  done

  CDPATH= cd -P "$(dirname "$script_path")" && pwd
}

script_dir=$(resolve_script_dir)
rules_root=$(dirname "$script_dir")
global_src="$rules_root/GLOBAL_AGENT_INSTRUCTIONS.md"

codex_dir="$HOME/.codex"
claude_dir="$HOME/.claude"
codex_file="$codex_dir/AGENTS.md"
claude_file="$claude_dir/CLAUDE.md"
import_line='@~/.codex/AGENTS.md'

mkdir -p "$codex_dir" "$claude_dir"

# 1. Validate the Claude bridge before creating or changing any files.
if [ -L "$claude_file" ]; then
  link_target=$(readlink "$claude_file")
  case "$link_target" in
    /*) resolved_target=$link_target ;;
    *) resolved_target="$claude_dir/$link_target" ;;
  esac
  target_dir=$(CDPATH= cd "$(dirname "$resolved_target")" 2>/dev/null && pwd -P) || target_dir=
  expected_dir=$(CDPATH= cd "$codex_dir" && pwd -P)
  normalized_target="$target_dir/$(basename "$resolved_target")"
  normalized_expected="$expected_dir/$(basename "$codex_file")"
  if [ -z "$target_dir" ] || [ "$normalized_target" != "$normalized_expected" ]; then
    echo "Conflict: $claude_file is a symlink to '$link_target', not $codex_file." >&2
    echo "Keep or migrate that configuration manually; nothing was changed." >&2
    exit 1
  fi
  claude_action=migrate
elif [ ! -e "$claude_file" ]; then
  claude_action=create
elif [ "$(cat "$claude_file")" = "$import_line" ]; then
  claude_action=keep
else
  echo "Conflict: $claude_file is not the exact one-line import '$import_line'." >&2
  echo "Keep or merge its existing rules manually; nothing was changed." >&2
  exit 1
fi

# 2. Ensure the canonical Codex global instructions exist; never overwrite.
if [ ! -e "$codex_file" ]; then
  if [ -f "$global_src" ]; then
    cp "$global_src" "$codex_file"
    echo "Created $codex_file from GLOBAL_AGENT_INSTRUCTIONS.md"
  else
    echo "Error: $codex_file is missing and GLOBAL_AGENT_INSTRUCTIONS.md was not found." >&2
    echo "Add your global rules to $codex_file before agents can use them." >&2
    exit 1
  fi
else
  echo "Kept existing $codex_file (not overwritten)."
fi

# 3. Point Claude Code at the same file via a one-line import.
case "$claude_action" in
  migrate)
    rm "$claude_file"
    printf '%s\n' "$import_line" > "$claude_file"
    echo "Replaced the canonical Codex symlink with an @import."
    ;;
  create)
    printf '%s\n' "$import_line" > "$claude_file"
    echo "Created $claude_file importing ~/.codex/AGENTS.md."
    ;;
  keep)
    echo "Already configured: $claude_file imports ~/.codex/AGENTS.md."
    ;;
esac

echo "Global agent setup complete."
