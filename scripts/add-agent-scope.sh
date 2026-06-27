#!/bin/sh
set -eu

# Add directory-scoped agent rules. Keep shared rules in the root AGENTS.md;
# use this only when a subdirectory genuinely needs its own rules. Creates
# <dir>/AGENTS.md (the rules) and <dir>/CLAUDE.md (a one-line @AGENTS.md import
# so Claude Code reads the same scoped file). Safe to re-run.

[ "$#" -eq 1 ] || { echo "Usage: $0 <directory>" >&2; exit 2; }

dir=$1
mkdir -p "$dir"
agents="$dir/AGENTS.md"
claude="$dir/CLAUDE.md"

if [ ! -e "$agents" ]; then
  cat > "$agents" <<'EOF'
# Agent Instructions

Scope-specific rules for this directory. Shared rules stay in the root
`AGENTS.md`; add here only what differs for this part of the project.

-
EOF
  echo "Created $agents"
else
  echo "Kept existing $agents (not overwritten)."
fi

if [ -L "$claude" ]; then
  rm "$claude"
  printf '@AGENTS.md\n' > "$claude"
  echo "Replaced symlink $claude with an @import."
elif [ ! -e "$claude" ]; then
  printf '@AGENTS.md\n' > "$claude"
  echo "Wrote $claude (@AGENTS.md)."
elif grep -qF '@AGENTS.md' "$claude"; then
  echo "Already configured: $claude imports AGENTS.md."
else
  echo "Conflict: $claude exists without '@AGENTS.md'. Merge manually." >&2
  exit 1
fi
