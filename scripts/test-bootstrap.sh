#!/bin/sh
# Regression test for bootstrap-new-project.sh. Creates throwaway projects for
# every profile, asserts invariants, and cleans up. No dependencies beyond a
# POSIX shell and git. Run before committing changes to the bootstrap path.

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
bootstrap="$script_dir/bootstrap-new-project.sh"

tmp=$(mktemp -d 2>/dev/null || mktemp -d -t bstest)
trap 'rm -rf "$tmp"' EXIT INT TERM

pass=0
fail=0
ok() { pass=$((pass + 1)); }
bad() { fail=$((fail + 1)); printf '  FAIL: %s\n' "$1"; }

assert_file() {
  if [ -f "$1/$2" ]; then ok; else bad "$3: missing $2"; fi
}
assert_absent() {
  if [ -e "$1/$2" ]; then bad "$3: unexpected $2"; else ok; fi
}
assert_grep() {
  if grep -qF "$2" "$1" 2>/dev/null; then ok; else bad "$3: '$2' not found in $1"; fi
}
assert_no_placeholder() {
  if find "$1" -name '*.md' -not -path '*/.git/*' -exec grep -lE '<PROJECT_NAME>|<YYYY-MM-DD>' {} + 2>/dev/null | grep -q .; then
    bad "$2: leftover template placeholder"
  else ok; fi
}
assert_no_bom() {
  if [ "$(head -c 3 "$1" 2>/dev/null | od -An -tx1 | tr -d ' \n')" = "efbbbf" ]; then
    bad "$2: UTF-8 BOM present in $1"
  else ok; fi
}
assert_clean_tree() {
  if [ -z "$(git -C "$1" status --porcelain 2>/dev/null)" ]; then ok
  else bad "$2: git working tree not clean after bootstrap"; fi
}

echo "Core invariants across profiles..."
for profile in minimal software operated all; do
  dir="$tmp/$profile"
  if ! sh "$bootstrap" "$dir" "Test $profile" "$profile" >/dev/null 2>&1; then
    bad "$profile: bootstrap exited non-zero"
    continue
  fi
  for f in README.md AGENTS.md CLAUDE.md INDEX.md PROJECT.md \
    .editorconfig .gitignore .gitattributes .obsidian/app.json; do
    assert_file "$dir" "$f" "$profile"
  done
  if [ "$(cat "$dir/CLAUDE.md" 2>/dev/null)" = "@AGENTS.md" ]; then ok
  else bad "$profile: CLAUDE.md is not exactly '@AGENTS.md'"; fi
  assert_no_placeholder "$dir" "$profile"
  assert_no_bom "$dir/AGENTS.md" "$profile"
  assert_grep "$dir/AGENTS.md" "Test $profile" "$profile"
  assert_grep "$dir/AGENTS.md" "Always answer the user in Russian" "$profile"
  assert_grep "$dir/.gitignore" "CLAUDE.local.md" "$profile"
  assert_clean_tree "$dir" "$profile"
done

echo "Profile-specific outputs..."
assert_absent "$tmp/minimal" "CHANGELOG.md" "minimal"
assert_absent "$tmp/minimal" "docs/architecture/ARCHITECTURE.md" "minimal"

assert_file "$tmp/software" "CHANGELOG.md" "software"
assert_file "$tmp/software" "docs/architecture/ARCHITECTURE.md" "software"
assert_file "$tmp/software" "docs/quality/TESTING.md" "software"
assert_absent "$tmp/software" "ACTIONS.md" "software"

assert_file "$tmp/operated" "ACTIONS.md" "operated"
assert_file "$tmp/operated" "TOOLS.md" "operated"
assert_file "$tmp/operated" "docs/operations/ENVIRONMENTS.md" "operated"
assert_absent "$tmp/operated" "SECURITY.md" "operated"

assert_file "$tmp/all" "docs/api/INTERFACES.md" "all"
assert_file "$tmp/all" "docs/data/DATA_MODEL.md" "all"
assert_file "$tmp/all" "SECURITY.md" "all"
assert_file "$tmp/all" "docs/security/THREAT_MODEL.md" "all"
# Per-instance templates must never be auto-created by a profile.
assert_absent "$tmp/all" "docs/architecture/decisions" "all (no auto ADR dir)"

echo "Guards..."
if sh "$bootstrap" "$tmp/software" "Dup" minimal >/dev/null 2>&1; then
  bad "guard: bootstrap into a non-empty destination should fail"
else ok; fi
if sh "$bootstrap" "$tmp/badprofile" "Bad" nonsense >/dev/null 2>&1; then
  bad "guard: invalid profile should fail"
else ok; fi

echo
total=$((pass + fail))
if [ "$fail" -eq 0 ]; then
  echo "All $total checks passed."
else
  echo "$fail of $total checks FAILED."
  exit 1
fi
