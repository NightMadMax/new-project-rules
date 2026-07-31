#!/bin/sh
# Read-only check of the must-have baseline for the dual Codex + Claude Code
# workflow on macOS/Linux. Changes nothing; exits non-zero if a required tool
# or credential is missing. See docs/research/MUST_HAVE_PROJECT_TOOLING_2026.md.

missing=0

agent_mode=${1:-both}
case "$agent_mode" in
  codex|claude|both) ;;
  *) echo "Usage: $0 [codex|claude|both]" >&2; exit 2 ;;
esac

# The canon knows the install locations outside PATH; this script cannot assume
# Python, so it asks the canon when Python is there and walks PATH otherwise.
# Without this the two disagree about the same machine: check-cli starts a CLI
# that check-environment calls missing.
discovery=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    script_dir=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
    if [ -f "$script_dir/cli_discovery.py" ]; then
      discovery=$("$candidate" "$script_dir/cli_discovery.py" --porcelain git gh codex claude 2>/dev/null) || discovery=""
    fi
    break
  fi
done

has() {
  if [ -n "$discovery" ]; then
    line=$(printf '%s
' "$discovery" | grep "^$1	") || line=""
    if [ -n "$line" ]; then
      [ "$(printf '%s' "$line" | cut -f2)" = "ok" ]
      return $?
    fi
  fi
  command -v "$1" >/dev/null 2>&1 && "$1" --version >/dev/null 2>&1
}

req() {
  if has "$1"; then printf '  [ ok ] %s\n' "$1"
  else printf '  [MISS] %s — %s (не найден запускаемый бинарник)\n' "$1" "$2"; missing=$((missing + 1)); fi
}

rec() {
  if has "$1"; then printf '  [ ok ] %s\n' "$1"
  else printf '  [ -- ] %s — %s\n' "$1" "$2"; fi
}

echo "Required on this machine (agent mode: $agent_mode):"
req git "version control"
req gh "GitHub CLI for repos, pull requests, releases"
case "$agent_mode" in codex|both) req codex "OpenAI Codex agent; вне PATH его найдёт scripts/check-cli.sh" ;; esac
case "$agent_mode" in claude|both) req claude "Anthropic Claude Code agent; вне PATH его найдёт scripts/check-cli.sh" ;; esac

echo
echo "Authentication and credentials:"
if has gh; then
  if gh auth status >/dev/null 2>&1; then
    echo "  [ ok ] gh is authenticated"
  else
    echo "  [MISS] gh is not authenticated — run: gh auth login"
    missing=$((missing + 1))
  fi
fi
if has git; then
  transport=""
  if has gh; then
    transport=$(gh config get git_protocol 2>/dev/null || true)
  fi
  helper=$(git config --get credential.helper 2>/dev/null || true)
  if [ "$transport" = "ssh" ] && [ -z "$helper" ]; then
    # SSH transport authenticates with keys; a credential helper is not used.
    echo "  [ ok ] git transport is SSH (gh git_protocol=ssh); credential helper not required"
  else
    case "$helper" in
      "") echo "  [MISS] no git credential helper — configure Keychain or Git Credential Manager"
          missing=$((missing + 1)) ;;
      store) echo "  [WARN] credential.helper=store saves tokens UNENCRYPTED; prefer Keychain/GCM" ;;
      *) printf '  [ ok ] credential.helper=%s\n' "$helper" ;;
    esac
  fi
fi
case "$agent_mode" in
  claude|both)
    if [ -f "$HOME/.claude/CLAUDE.md" ]; then
      echo "  [ ok ] ~/.claude/CLAUDE.md present"
    else
      echo "  [ -- ] ~/.claude/CLAUDE.md missing — run scripts/setup-global-agents.sh"
    fi
    ;;
esac

echo
echo "Recommended (not required):"
rec python3 "cross-platform automation"
rec pwsh "PowerShell 7 for testing .ps1 scripts"
rec rg "ripgrep fast search (often bundled with Claude Code)"
rec brew "Homebrew package manager"

echo
if [ "$missing" -eq 0 ]; then
  echo "All required tools and credentials are present."
else
  echo "$missing required item(s) missing — see [MISS] above."
  exit 1
fi
