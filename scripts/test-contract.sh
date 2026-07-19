#!/bin/sh
set -u

script_dir=$(CDPATH= cd -P "$(dirname "$0")" && pwd) || exit 1
root=$(dirname "$script_dir")
bootstrap="$script_dir/bootstrap-new-project.sh"
manifest="$root/config/profiles.tsv"
policy_contract="$root/config/policy-contract.tsv"
templates="$root/templates/new-project"
tmp=$(mktemp -d 2>/dev/null || mktemp -d -t contracttest) || exit 1
trap 'rm -rf "$tmp"' EXIT INT TERM

pass=0
fail=0
ok() { pass=$((pass + 1)); }
bad() { fail=$((fail + 1)); printf '  FAIL: %s\n' "$1"; }

rank() {
  case "$1" in
    minimal) echo 0 ;;
    software) echo 1 ;;
    operated) echo 2 ;;
    all) echo 3 ;;
    *) return 1 ;;
  esac
}

includes_profile() {
  minimum_rank=$(rank "$1") || return 1
  profile_rank=$(rank "$2") || return 1
  [ "$minimum_rank" -le "$profile_rank" ]
}

echo "Contract structure..."
version=$(tr -d '\r\n' < "$root/STANDARD_VERSION")
case "$version" in
  ''|*[!0-9]*|0) bad "STANDARD_VERSION must be a positive integer" ;;
  *) ok ;;
esac

header=$(sed -n '1p' "$manifest")
if [ "$header" = "minimum_profile	source	destination	root_purpose	docs_section	docs_label" ]; then ok
else bad "unexpected profiles.tsv header"; fi

destinations="$tmp/destinations"
: > "$destinations"
first=1
tab=$(printf '\t')
while IFS="$tab" read -r minimum source destination root_purpose docs_section docs_label; do
  if [ "$first" -eq 1 ]; then first=0; continue; fi
  rank "$minimum" >/dev/null 2>&1 || bad "unknown minimum_profile '$minimum'"
  case "/$destination/" in
    /*/../*|//* ) bad "unsafe destination '$destination'" ;;
  esac
  if grep -Fxq "$destination" "$destinations"; then
    bad "duplicate destination '$destination'"
  else
    printf '%s\n' "$destination" >> "$destinations"
  fi
  if [ "$source" != @generated ] && [ ! -f "$templates/$source" ]; then
    bad "missing template '$source'"
  fi
  if [ -z "$root_purpose" ] ||
     { [ "$docs_section" = - ] && [ "$docs_label" != - ]; } ||
     { [ "$docs_section" != - ] && [ "$docs_label" = - ]; }; then
    bad "invalid index relationship for '$destination'"
  fi
done < "$manifest"

first=1
while IFS="$tab" read -r file literal; do
  if [ "$first" -eq 1 ]; then first=0; continue; fi
  if [ -f "$root/$file" ] && grep -Fq "$literal" "$root/$file"; then ok
  else bad "policy literal '$literal' missing from '$file'"; fi
done < "$policy_contract"

echo "Bootstrap parity across profiles..."
for profile in minimal software operated all; do
  destination="$tmp/$profile"
  home="$tmp/home-$profile"
  mkdir -p "$home"
  if HOME="$home" XDG_CONFIG_HOME="$home/.config" GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME='Contract Test' \
    GIT_AUTHOR_EMAIL='contract@example.invalid' GIT_COMMITTER_NAME='Contract Test' \
    GIT_COMMITTER_EMAIL='contract@example.invalid' \
    sh "$bootstrap" "$destination" "Contract $profile" "$profile" >/dev/null 2>&1; then
    :
  else
    bad "$profile: bootstrap failed"
    continue
  fi

  expected="$tmp/expected-$profile"
  actual="$tmp/actual-$profile"
  : > "$expected"
  first=1
  while IFS="$tab" read -r minimum source path root_purpose docs_section docs_label; do
    if [ "$first" -eq 1 ]; then first=0; continue; fi
    if includes_profile "$minimum" "$profile"; then
      printf '%s\n' "$path" >> "$expected"
    fi
  done < "$manifest"
  sort "$expected" -o "$expected"
  find "$destination" -type f ! -path "$destination/.git/*" -print \
    | sed "s|^$destination/||" | sort > "$actual"
  if diff -u "$expected" "$actual" >/dev/null; then ok
  else bad "$profile: generated files differ from config/profiles.tsv"; fi

  first=1
  while IFS="$tab" read -r minimum source path root_purpose docs_section docs_label; do
    if [ "$first" -eq 1 ]; then first=0; continue; fi
    includes_profile "$minimum" "$profile" || continue
    link_path=${path%.md}
    if [ "$root_purpose" != - ]; then
      if grep -Fq "[[$link_path" "$destination/INDEX.md"; then ok
      else bad "$profile: root INDEX.md misses '$link_path'"; fi
    fi
    if [ "$docs_section" != - ]; then
      if grep -Fq "[[$link_path" "$destination/docs/README.md"; then ok
      else bad "$profile: docs/README.md misses '$link_path'"; fi
    fi
  done < "$manifest"
done

echo "Manifest drives bootstrap output..."
fixture="$tmp/rules-fixture"
mkdir -p "$fixture/scripts" "$fixture/config" "$fixture/templates"
cp "$bootstrap" "$fixture/scripts/bootstrap-new-project.sh"
cp "$root/STANDARD_VERSION" "$fixture/STANDARD_VERSION"
cp "$root/config/standard-source.txt" "$fixture/config/standard-source.txt"
cp "$root/config/migrations.tsv" "$fixture/config/migrations.tsv"
cp "$root/config/capabilities.tsv" "$fixture/config/capabilities.tsv"
cp -R "$templates" "$fixture/templates/"
grep -v "${tab}CHANGELOG.template.md${tab}" "$manifest" \
  | sed "s/Current system architecture/Manifest-owned architecture/; s/${tab}Environments\$/${tab}Manifest Environments/" \
  > "$fixture/config/profiles.tsv"
git -C "$fixture" init -q
git -C "$fixture" add -A
git -C "$fixture" -c user.name='Contract Test' -c user.email='contract@example.invalid' commit -qm fixture
fixture_destination="$tmp/manifest-driven"
fixture_home="$tmp/home-manifest-driven"
mkdir -p "$fixture_home"
if HOME="$fixture_home" XDG_CONFIG_HOME="$fixture_home/.config" GIT_CONFIG_NOSYSTEM=1 \
  GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME='Contract Test' \
  GIT_AUTHOR_EMAIL='contract@example.invalid' GIT_COMMITTER_NAME='Contract Test' \
  GIT_COMMITTER_EMAIL='contract@example.invalid' \
  sh "$fixture/scripts/bootstrap-new-project.sh" "$fixture_destination" \
    "Manifest Driven" operated >/dev/null 2>&1; then
  if [ ! -e "$fixture_destination/CHANGELOG.md" ] &&
     [ -f "$fixture_destination/docs/architecture/ARCHITECTURE.md" ] &&
     grep -Fq 'Manifest-owned architecture' "$fixture_destination/INDEX.md" &&
     grep -Fq 'Manifest Environments' "$fixture_destination/docs/README.md"; then ok
  else bad "bootstrap output did not follow the modified fixture manifest"; fi
else
  bad "modified manifest bootstrap failed"
fi

{
  echo 'invalid-header'
  sed -n '2,$p' "$manifest"
} > "$fixture/config/profiles.tsv"
invalid_destination="$tmp/invalid-manifest-target"
if sh "$fixture/scripts/bootstrap-new-project.sh" "$invalid_destination" \
  "Invalid Manifest" minimal >/dev/null 2>&1; then
  bad "invalid manifest was accepted"
elif [ ! -e "$invalid_destination" ]; then
  ok
else
  bad "invalid manifest changed destination before validation"
fi

echo
total=$((pass + fail))
if [ "$fail" -eq 0 ]; then
  echo "All $total contract checks passed."
  exit 0
fi
echo "$fail of $total contract checks FAILED."
exit 1
