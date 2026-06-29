#!/bin/sh
# Smoke tests for global and directory-scoped agent instruction setup.

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
setup="$script_dir/setup-global-agents.sh"
scope="$script_dir/add-agent-scope.sh"
validator="$script_dir/validate-project.sh"
doctor="$script_dir/project-doctor.sh"
sync_agents="$script_dir/sync-global-agents.sh"
plan_migration="$script_dir/plan-migration.sh"
real_git=$(command -v git) || {
  echo "git is required to run agent setup smoke tests." >&2
  exit 1
}

tmp=$(mktemp -d 2>/dev/null || mktemp -d -t agenttest)
trap 'rm -rf "$tmp"' EXIT INT TERM

pass=0
fail=0
ok() { pass=$((pass + 1)); }
bad() { fail=$((fail + 1)); printf '  FAIL: %s\n' "$1"; }

assert_file() {
  if [ -f "$1" ]; then ok; else bad "$2: missing $1"; fi
}
assert_absent() {
  if [ -e "$1" ] || [ -L "$1" ]; then bad "$2: unexpected $1"; else ok; fi
}
assert_exact() {
  if [ "$(cat "$1" 2>/dev/null)" = "$2" ]; then ok
  else bad "$3: unexpected content in $1"; fi
}
assert_count() {
  count=$(grep -Fc "$2" "$1" 2>/dev/null || true)
  if [ "$count" -eq "$3" ]; then ok
  else bad "$4: expected $3 occurrence(s), found $count"; fi
}

echo "Global agent setup..."
path_bin="$tmp/path-bin"
outside="$tmp/outside"
home="$tmp/home"
mkdir -p "$path_bin" "$outside" "$home"
ln -s "$setup" "$path_bin/setup-global-agents"
if (cd "$outside" && HOME="$home" PATH="$path_bin:$PATH" \
  setup-global-agents >"$tmp/setup-create.out" 2>&1); then ok
else bad "global creation through PATH symlink failed"; fi
assert_file "$home/.codex/AGENTS.md" "global creation"
assert_file "$home/.claude/CLAUDE.md" "global creation"
if cmp -s "$rules_root/GLOBAL_AGENT_INSTRUCTIONS.md" "$home/.codex/AGENTS.md"; then ok
else bad "global creation: canonical instructions differ from source"; fi
assert_exact "$home/.claude/CLAUDE.md" '@~/.codex/AGENTS.md' "global creation"

printf '\n# preserved marker\n' >> "$home/.codex/AGENTS.md"
if HOME="$home" sh "$setup" >"$tmp/setup-repeat.out" 2>&1; then ok
else bad "global idempotent rerun failed"; fi
if grep -qF '# preserved marker' "$home/.codex/AGENTS.md"; then ok
else bad "global idempotence: existing AGENTS.md was overwritten"; fi
assert_exact "$home/.claude/CLAUDE.md" '@~/.codex/AGENTS.md' "global idempotence"

conflict_home="$tmp/conflict-home"
mkdir -p "$conflict_home/.claude"
printf 'custom rules\n' > "$conflict_home/.claude/CLAUDE.md"
if HOME="$conflict_home" sh "$setup" >"$tmp/setup-conflict.out" 2>&1; then
  bad "global conflict should fail"
else ok; fi
assert_exact "$conflict_home/.claude/CLAUDE.md" 'custom rules' "global conflict"
assert_absent "$conflict_home/.codex/AGENTS.md" "global conflict"

echo "Scoped agent setup..."
project="$tmp/project"
mkdir -p "$project"
"$real_git" -C "$project" init -q
"$real_git" -C "$project" symbolic-ref HEAD refs/heads/main
printf '# Index\n\n| File | Purpose |\n|---|---|\n' > "$project/INDEX.md"

scope_dir="$project/services/api"
if sh "$scope" "$scope_dir" "Run API tests." >"$tmp/scope-create.out" 2>&1; then ok
else bad "scope creation failed"; fi
assert_file "$scope_dir/AGENTS.md" "scope creation"
assert_exact "$scope_dir/CLAUDE.md" '@AGENTS.md' "scope creation"
if grep -qF -- '- Run API tests.' "$scope_dir/AGENTS.md"; then ok
else bad "scope creation: rule is missing"; fi
agents_link='[[services/api/AGENTS|services/api/AGENTS.md]]'
claude_link='[[services/api/CLAUDE|services/api/CLAUDE.md]]'
assert_count "$project/INDEX.md" "$agents_link" 1 "scope creation"
assert_count "$project/INDEX.md" "$claude_link" 1 "scope creation"

if sh "$scope" "$scope_dir" "A replacement rule." >"$tmp/scope-repeat.out" 2>&1; then ok
else bad "scope idempotent rerun failed"; fi
if grep -qF -- '- Run API tests.' "$scope_dir/AGENTS.md" && \
   ! grep -qF 'A replacement rule.' "$scope_dir/AGENTS.md"; then ok
else bad "scope idempotence: existing AGENTS.md changed"; fi
assert_count "$project/INDEX.md" "$agents_link" 1 "scope idempotence"
assert_count "$project/INDEX.md" "$claude_link" 1 "scope idempotence"

conflict_dir="$project/services/conflict"
mkdir -p "$conflict_dir"
printf 'custom scoped rules\n' > "$conflict_dir/CLAUDE.md"
cp "$project/INDEX.md" "$tmp/index-before-conflict"
if sh "$scope" "$conflict_dir" "Should not be written." >"$tmp/scope-conflict.out" 2>&1; then
  bad "scope conflict should fail"
else ok; fi
assert_exact "$conflict_dir/CLAUDE.md" 'custom scoped rules' "scope conflict"
assert_absent "$conflict_dir/AGENTS.md" "scope conflict"
if cmp -s "$tmp/index-before-conflict" "$project/INDEX.md"; then ok
else bad "scope conflict: INDEX.md changed"; fi

escaped_dir="$project/services/../../escaped-scope"
if sh "$scope" "$escaped_dir" "Must not be created." >"$tmp/scope-traversal.out" 2>&1; then
  bad "scope traversal should fail"
else ok; fi
if grep -qF "must not contain '..'" "$tmp/scope-traversal.out"; then ok
else bad "scope traversal diagnostic is missing"; fi
assert_absent "$tmp/escaped-scope" "scope traversal"

grep_error_dir="$project/services/grep-error"
fake_bin="$tmp/fake-bin"
mkdir -p "$fake_bin"
cat > "$fake_bin/grep" <<'FAKE_GREP'
#!/bin/sh
echo "simulated grep read error" >&2
exit 2
FAKE_GREP
chmod +x "$fake_bin/grep"
cp "$project/INDEX.md" "$tmp/index-before-grep-error"
if PATH="$fake_bin:$PATH" sh "$scope" "$grep_error_dir" "Temporary rule." \
  >"$tmp/scope-grep-error.out" 2>&1; then
  bad "grep read error should fail"
else ok; fi
if cmp -s "$tmp/index-before-grep-error" "$project/INDEX.md"; then ok
else bad "grep read error: INDEX.md changed"; fi
if grep -qF 'could not read' "$tmp/scope-grep-error.out"; then ok
else bad "grep read error: diagnostic is missing"; fi

echo "Environment check without git..."
if PATH="$tmp/empty-path" HOME="$tmp/check-home" /bin/sh "$script_dir/check-environment.sh" codex \
  >"$tmp/check-no-git.out" 2>&1; then
  bad "environment check should report missing required tools"
else ok; fi
assert_count "$tmp/check-no-git.out" '[MISS] git' 1 "environment check"
assert_count "$tmp/check-no-git.out" '[MISS] claude' 0 "codex-only environment check"
if grep -qF 'credential.helper' "$tmp/check-no-git.out"; then
  bad "environment check queried credential helper without git"
else ok; fi
if PATH="$tmp/empty-path" HOME="$tmp/check-home" /bin/sh "$script_dir/check-environment.sh" both \
  >"$tmp/check-both.out" 2>&1; then
  bad "both-mode environment check should report missing required tools"
else ok; fi
assert_count "$tmp/check-both.out" '[MISS] claude' 1 "both-mode environment check"

echo "Validator and doctor wrappers..."
if sh "$validator" --root "$rules_root" --kind rules >"$tmp/validator.out" 2>&1; then ok
else bad "validator wrapper failed"; fi
if grep -qF 'Summary: 0 error(s)' "$tmp/validator.out"; then ok
else bad "validator wrapper summary is missing"; fi
if sh "$doctor" --root "$rules_root" --agent-mode codex --report-only \
  >"$tmp/doctor.out" 2>&1; then ok
else bad "report-only doctor failed"; fi
if grep -qF 'Project diagnostics:' "$tmp/doctor.out"; then ok
else bad "doctor project diagnostics are missing"; fi

echo "Read-only global policy sync wrapper..."
sync_home="$tmp/sync-home"
mkdir -p "$sync_home/.codex"
cp "$rules_root/GLOBAL_AGENT_INSTRUCTIONS.md" "$sync_home/.codex/AGENTS.md"
if sh "$sync_agents" --check --home "$sync_home" >"$tmp/sync-check.out" 2>&1; then
  bad "legacy sync check should return drift status"
else ok; fi
if grep -qF 'status=legacy_exact' "$tmp/sync-check.out"; then ok
else bad "sync check did not report legacy_exact"; fi
if sh "$sync_agents" --diff --home "$sync_home" --report-only >"$tmp/sync-diff.out" 2>&1; then ok
else bad "sync diff report-only failed"; fi
if grep -qF 'Plan: wrap' "$tmp/sync-diff.out" && grep -qF 'sha256=' "$tmp/sync-diff.out"; then ok
else bad "sync diff summary is missing"; fi

echo "Read-only migration planner wrapper..."
if sh "$plan_migration" --plan --target global --home "$sync_home" --report-only >"$tmp/migration-plan.out" 2>&1; then ok
else bad "migration plan report-only failed"; fi
if grep -qF 'migration=0002-adopt-global-managed-block' "$tmp/migration-plan.out" &&
   grep -qF 'No files were changed.' "$tmp/migration-plan.out"; then ok
else bad "migration plan summary is missing"; fi

echo
total=$((pass + fail))
if [ "$fail" -eq 0 ]; then
  echo "All $total checks passed."
else
  echo "$fail of $total checks FAILED."
  exit 1
fi
