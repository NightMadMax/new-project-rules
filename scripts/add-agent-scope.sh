#!/bin/sh
set -eu

# Add directory-scoped agent rules. Keep shared rules in the root AGENTS.md;
# use this only when a subdirectory genuinely needs its own rules. Creates
# <dir>/AGENTS.md (the rules) and <dir>/CLAUDE.md (a one-line @AGENTS.md import
# so Claude Code reads the same scoped file). Safe to re-run.

[ "$#" -eq 2 ] || { echo "Usage: $0 <directory> <rule>" >&2; exit 2; }

dir=$1
rule=$2
[ -n "$rule" ] || { echo "Rule must not be empty." >&2; exit 2; }
case "/$dir/" in
  */../*) echo "Scope directory must not contain '..' path components." >&2; exit 1 ;;
esac

probe=$dir
while [ ! -d "$probe" ]; do
  parent=$(dirname "$probe")
  [ "$parent" != "$probe" ] || { echo "Cannot locate an existing parent for $dir." >&2; exit 1; }
  probe=$parent
done

project_root=$(git -C "$probe" rev-parse --show-toplevel 2>/dev/null) || {
  echo "Directory must be inside a git project." >&2
  exit 1
}
index_file="$project_root/INDEX.md"
[ -f "$index_file" ] || { echo "Project index not found: $index_file" >&2; exit 1; }

probe=$(CDPATH= cd "$probe" && pwd -P)
project_root=$(CDPATH= cd "$project_root" && pwd -P)
case "$probe" in
  "$project_root"|"$project_root"/*) ;;
  *) echo "Scope directory must be below the project root: $project_root" >&2; exit 1 ;;
esac

mkdir -p "$dir"
dir=$(CDPATH= cd "$dir" && pwd -P)
case "$dir" in
  "$project_root"/*) relative_dir=${dir#"$project_root"/} ;;
  *) echo "Scope directory must be below the project root: $project_root" >&2; exit 1 ;;
esac

agents="$dir/AGENTS.md"
claude="$dir/CLAUDE.md"

# Validate the Claude bridge before creating or changing any project files.
if [ -L "$claude" ]; then
  link_target=$(readlink "$claude")
  case "$link_target" in
    /*) resolved_target=$link_target ;;
    *) resolved_target="$dir/$link_target" ;;
  esac
  target_dir=$(CDPATH= cd "$(dirname "$resolved_target")" 2>/dev/null && pwd -P) || target_dir=
  normalized_target="$target_dir/$(basename "$resolved_target")"
  if [ -z "$target_dir" ] || [ "$normalized_target" != "$agents" ]; then
    echo "Conflict: $claude is a symlink to '$link_target', not $agents." >&2
    echo "Nothing was changed." >&2
    exit 1
  fi
  claude_action=migrate
elif [ ! -e "$claude" ]; then
  claude_action=create
elif [ "$(cat "$claude")" = '@AGENTS.md' ]; then
  claude_action=keep
else
  echo "Conflict: $claude is not the exact one-line import '@AGENTS.md'." >&2
  echo "Nothing was changed." >&2
  exit 1
fi

if [ ! -e "$agents" ]; then
  cat > "$agents" <<'EOF'
# Agent Instructions

Scope-specific rules for this directory. Shared rules stay in the root
`AGENTS.md`; add here only what differs for this part of the project.

EOF
  printf -- '- %s\n' "$rule" >> "$agents"
  echo "Created $agents"
else
  echo "Kept existing $agents (not overwritten)."
fi

case "$claude_action" in
  migrate)
    rm "$claude"
    printf '@AGENTS.md\n' > "$claude"
    echo "Replaced the scoped AGENTS symlink with an @import."
    ;;
  create)
    printf '@AGENTS.md\n' > "$claude"
    echo "Wrote $claude (@AGENTS.md)."
    ;;
  keep)
    echo "Already configured: $claude imports AGENTS.md."
    ;;
esac

agents_link="[[$relative_dir/AGENTS|$relative_dir/AGENTS.md]]"
claude_link="[[$relative_dir/CLAUDE|$relative_dir/CLAUDE.md]]"

append_index_link() {
  link=$1
  description=$2
  if grep -qF "$link" "$index_file"; then
    return 0
  else
    grep_status=$?
  fi
  if [ "$grep_status" -ne 1 ]; then
    echo "Error: could not read $index_file while checking for '$link'." >&2
    exit 1
  fi
  printf '| %s | %s |\n' "$link" "$description" >> "$index_file"
}

append_index_link "$agents_link" "Scoped agent rules"
append_index_link "$claude_link" "Imports scoped AGENTS for Claude Code"

echo "Updated $index_file with scoped instruction links."
