#!/bin/sh
# Regression tests for bootstrap-new-project.sh. All Git configuration and
# generated projects are isolated under a temporary directory.

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
bootstrap="$script_dir/bootstrap-new-project.sh"
standard_version=$(cat "$script_dir/../STANDARD_VERSION") || exit 1

if [ "${BOOTSTRAP_TEST_RESOLVER_PROBE:-0}" = 1 ]; then
  [ -f "$bootstrap" ] || exit 1
  exit 0
fi

real_git=$(command -v git) || {
  echo "git is required to run bootstrap regression tests." >&2
  exit 1
}
original_path=$PATH

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
  if [ -e "$1/$2" ] || [ -L "$1/$2" ]; then bad "$3: unexpected $2"; else ok; fi
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
  status_output=$("$real_git" -C "$1" status --porcelain 2>/dev/null)
  status_code=$?
  if [ "$status_code" -ne 0 ]; then
    bad "$2: git status failed"
  elif [ -n "$status_output" ]; then
    bad "$2: git working tree not clean after bootstrap"
  else
    ok
  fi
}

run_with_identity() {
  home=$1
  shift
  mkdir -p "$home"
  (
    HOME=$home
    XDG_CONFIG_HOME=$home/.config
    GIT_CONFIG_NOSYSTEM=1
    GIT_CONFIG_GLOBAL=/dev/null
    GIT_AUTHOR_NAME='Bootstrap Test'
    GIT_AUTHOR_EMAIL='bootstrap@example.invalid'
    GIT_COMMITTER_NAME='Bootstrap Test'
    GIT_COMMITTER_EMAIL='bootstrap@example.invalid'
    export HOME XDG_CONFIG_HOME GIT_CONFIG_NOSYSTEM GIT_CONFIG_GLOBAL
    export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL
    export PATH
    if [ "${FAKE_GIT_REAL+x}" = x ]; then
      export FAKE_GIT_REAL FAKE_GIT_FAIL
    fi
    "$@"
  )
}

run_without_identity() {
  home=$1
  shift
  mkdir -p "$home"
  (
    HOME=$home
    XDG_CONFIG_HOME=$home/.config
    GIT_CONFIG_NOSYSTEM=1
    GIT_CONFIG_GLOBAL=/dev/null
    GIT_AUTHOR_NAME=
    GIT_AUTHOR_EMAIL=
    GIT_COMMITTER_NAME=
    GIT_COMMITTER_EMAIL=
    export HOME XDG_CONFIG_HOME GIT_CONFIG_NOSYSTEM GIT_CONFIG_GLOBAL
    export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL
    export PATH
    "$@"
  )
}

echo "Core invariants across profiles..."
for profile in minimal software operated all; do
  dir="$tmp/$profile"
  if ! run_with_identity "$tmp/home-$profile" sh "$bootstrap" \
    "$dir" "Test $profile" "$profile" >"$tmp/$profile.out" 2>&1; then
    bad "$profile: bootstrap exited non-zero"
    continue
  fi
  for f in README.md AGENTS.md CLAUDE.md INDEX.md PROJECT.md \
    .editorconfig .gitignore .gitattributes .project-standard.json; do
    assert_file "$dir" "$f" "$profile"
  done
  assert_absent "$dir" ".obsidian" "$profile"
  assert_file "$dir" "docs/quality/STANDARD_ADOPTION.json" "$profile metrics"
  assert_grep "$dir/docs/quality/STANDARD_ADOPTION.json" '"first_green_at": null' "$profile metrics"
  if [ "$(cat "$dir/CLAUDE.md" 2>/dev/null)" = "@AGENTS.md" ]; then ok
  else bad "$profile: CLAUDE.md is not exactly '@AGENTS.md'"; fi
  assert_no_placeholder "$dir" "$profile"
  assert_no_bom "$dir/AGENTS.md" "$profile"
  assert_grep "$dir/AGENTS.md" "Test $profile" "$profile"
  assert_grep "$dir/AGENTS.md" "Always answer the user in Russian" "$profile"
  assert_grep "$dir/AGENTS.md" "new-project-rules:begin schema=$standard_version" "$profile"
  assert_grep "$dir/AGENTS.md" "new-project-rules:end" "$profile"
  assert_grep "$dir/.gitignore" "CLAUDE.local.md" "$profile"
  assert_grep "$dir/.gitignore" ".obsidian/" "$profile"
  assert_grep "$dir/.project-standard.json" "\"profile\": \"$profile\"" "$profile metadata"
  assert_grep "$dir/.project-standard.json" '"source": "NightMadMax/new-project-rules"' "$profile metadata"
  assert_grep "$dir/.project-standard.json" '"0001-adopt-project-standard"' "$profile metadata"
  assert_grep "$dir/.project-standard.json" '"0004-upgrade-project-standard-v2"' "$profile metadata"
  assert_grep "$dir/.project-standard.json" '"created_at": "' "$profile metadata"
  assert_no_bom "$dir/.project-standard.json" "$profile metadata"
  if [ "$("$real_git" -C "$dir" symbolic-ref --short HEAD 2>/dev/null)" = main ]; then ok
  else bad "$profile: initial branch is not main"; fi
  if "$real_git" -C "$dir" rev-parse --verify HEAD >/dev/null 2>&1; then ok
  else bad "$profile: initial commit is missing"; fi
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
assert_grep "$tmp/operated/docs/README.md" '[[docs/operations/ENVIRONMENTS|Environments]]' "operated docs index"
assert_absent "$tmp/operated" "SECURITY.md" "operated"

assert_file "$tmp/all" "docs/api/INTERFACES.md" "all"
assert_file "$tmp/all" "docs/data/DATA_MODEL.md" "all"
assert_file "$tmp/all" "SECURITY.md" "all"
assert_file "$tmp/all" "docs/security/THREAT_MODEL.md" "all"
assert_grep "$tmp/all/docs/README.md" '[[docs/api/INTERFACES|Interfaces]]' "all docs index"
assert_grep "$tmp/all/docs/README.md" '[[docs/data/DATA_MODEL|Data model]]' "all docs index"
assert_grep "$tmp/all/docs/README.md" '[[docs/security/THREAT_MODEL|Threat model]]' "all docs index"
assert_absent "$tmp/all" "docs/architecture/decisions" "all (no auto ADR dir)"

echo "Git identity and failure handling..."
no_identity="$tmp/no-identity"
if run_without_identity "$tmp/home-no-identity" sh "$bootstrap" \
  "$no_identity" "No Identity" minimal >"$tmp/no-identity.out" 2>&1; then ok
else bad "no identity: bootstrap should succeed"; fi
if "$real_git" -C "$no_identity" rev-parse --verify HEAD >/dev/null 2>&1; then
  bad "no identity: initial commit should not exist"
else ok; fi
if "$real_git" -C "$no_identity" diff --cached --quiet --exit-code; then
  bad "no identity: generated files should remain staged"
else ok; fi
assert_grep "$tmp/no-identity.out" "set git user.name and git user.email" "no identity"

mock_bin="$tmp/mock-bin"
mkdir -p "$mock_bin"
cat > "$mock_bin/git" <<'MOCK_GIT'
#!/bin/sh
for arg in "$@"; do
  if [ "$arg" = "$FAKE_GIT_FAIL" ]; then
    echo "simulated git $FAKE_GIT_FAIL failure" >&2
    exit 42
  fi
done
exec "$FAKE_GIT_REAL" "$@"
MOCK_GIT
chmod +x "$mock_bin/git"

for operation in init add commit; do
  failed_dir="$tmp/fail-$operation"
  if (PATH="$mock_bin:$original_path"
    FAKE_GIT_REAL=$real_git
    FAKE_GIT_FAIL=$operation
    export PATH FAKE_GIT_REAL FAKE_GIT_FAIL
    run_with_identity "$tmp/home-fail-$operation" sh "$bootstrap" \
      "$failed_dir" "Fail $operation" minimal
  ) >"$tmp/fail-$operation.out" 2>&1; then
    bad "git $operation failure: bootstrap should fail"
  else ok; fi
  assert_grep "$tmp/fail-$operation.out" "simulated git $operation failure" "git $operation failure"
  if grep -qF "Created 'Fail $operation'" "$tmp/fail-$operation.out"; then
    bad "git $operation failure: misleading success message was printed"
  else ok; fi
  if [ ! -e "$failed_dir" ]; then ok
  else bad "git $operation failure: partial destination was not rolled back"; fi
done

existing_empty="$tmp/fail-existing-empty"
mkdir -p "$existing_empty"
if (PATH="$mock_bin:$original_path"
  FAKE_GIT_REAL=$real_git
  FAKE_GIT_FAIL=init
  export PATH FAKE_GIT_REAL FAKE_GIT_FAIL
  run_with_identity "$tmp/home-fail-existing" sh "$bootstrap" \
    "$existing_empty" "Fail Existing" minimal
) >"$tmp/fail-existing.out" 2>&1; then
  bad "rollback existing empty: bootstrap should fail"
else ok; fi
if [ -d "$existing_empty" ] && directory_contents=$(find "$existing_empty" -mindepth 1 -print -quit) && [ -z "$directory_contents" ]; then ok
else bad "rollback existing empty: original empty directory was not restored"; fi

echo "PATH, symlink, missing-git, and destination guards..."
path_bin="$tmp/path-bin"
outside="$tmp/outside"
mkdir -p "$path_bin" "$outside"
ln -s "$bootstrap" "$path_bin/bootstrap-new-project"
if (cd "$outside" && PATH="$path_bin:$original_path" run_with_identity "$tmp/home-path" \
  bootstrap-new-project "$tmp/path-project" "PATH Project" minimal \
  >"$tmp/path.out" 2>&1); then ok
else bad "PATH symlink: bootstrap failed"; fi
assert_file "$tmp/path-project" "README.md" "PATH symlink"

ln -s "$script_dir/test-bootstrap.sh" "$path_bin/test-bootstrap"
if (cd "$outside" && PATH="$path_bin:$original_path" BOOTSTRAP_TEST_RESOLVER_PROBE=1 \
  test-bootstrap >/dev/null 2>&1); then ok
else bad "PATH symlink: test-bootstrap resolver failed"; fi

no_git_bin="$tmp/no-git-bin"
mkdir -p "$no_git_bin"
for command_name in cat date dirname grep mkdir sed; do
  command_path=$(command -v "$command_name")
  ln -s "$command_path" "$no_git_bin/$command_name"
done
if PATH="$no_git_bin" /bin/sh "$bootstrap" "$tmp/no-git" "No Git" minimal \
  >"$tmp/no-git.out" 2>&1; then bad "missing git: bootstrap should fail"
else ok; fi
assert_absent "$tmp/no-git" ".git" "missing git"
assert_grep "$tmp/no-git.out" "Git is required to record project-standard provenance" "missing git"

mkdir -p "$tmp/hidden-only"
: > "$tmp/hidden-only/.hidden"
if sh "$bootstrap" "$tmp/hidden-only" "Hidden" minimal >/dev/null 2>&1; then
  bad "guard: hidden files should make destination non-empty"
else ok; fi
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
