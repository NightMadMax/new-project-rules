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

has() { command -v "$1" >/dev/null 2>&1; }

req() {
  if has "$1"; then printf '  [ ok ] %s\n' "$1"
  else printf '  [MISS] %s — %s\n' "$1" "$2"; missing=$((missing + 1)); fi
}

rec() {
  if has "$1"; then printf '  [ ok ] %s\n' "$1"
  else printf '  [ -- ] %s — %s\n' "$1" "$2"; fi
}

echo "Required on this machine (agent mode: $agent_mode):"
req git "version control"
req gh "GitHub CLI for repos, pull requests, releases"
case "$agent_mode" in codex|both) req codex "OpenAI Codex agent" ;; esac
case "$agent_mode" in claude|both) req claude "Anthropic Claude Code agent" ;; esac

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
  helper=$(git config --get credential.helper 2>/dev/null || true)
  case "$helper" in
    "") echo "  [MISS] no git credential helper — configure Keychain or Git Credential Manager"
        missing=$((missing + 1)) ;;
    store) echo "  [WARN] credential.helper=store saves tokens UNENCRYPTED; prefer Keychain/GCM" ;;
    *) printf '  [ ok ] credential.helper=%s\n' "$helper" ;;
  esac
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
