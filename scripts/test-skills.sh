#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
root=$(dirname "$script_dir")
fail=0

check_required_literals() {
  file=$1
  shift

  for literal in "$@"; do
    if ! grep -Fq "$literal" "$file"; then
      echo "FAIL: missing required literal '$literal' in $file" >&2
      fail=$((fail + 1))
    fi
  done
}

check_skill() {
  name=$1
  canonical="$root/.agents/skills/$name/SKILL.md"
  bridge="$root/.claude/skills/$name/SKILL.md"
  metadata="$root/.agents/skills/$name/agents/openai.yaml"

  for file in "$canonical" "$bridge" "$metadata"; do
    if [ ! -f "$file" ]; then
      echo "FAIL: missing $file" >&2
      fail=$((fail + 1))
    fi
  done
  [ "$fail" -eq 0 ] || return

  canonical_name=$(sed -n 's/^name: //p' "$canonical" | sed -n '1p')
  bridge_name=$(sed -n 's/^name: //p' "$bridge" | sed -n '1p')
  canonical_description=$(sed -n 's/^description: //p' "$canonical" | sed -n '1p')
  bridge_description=$(sed -n 's/^description: //p' "$bridge" | sed -n '1p')

  if [ "$canonical_name" != "$name" ] || [ "$bridge_name" != "$name" ]; then
    echo "FAIL: name mismatch for $name" >&2
    fail=$((fail + 1))
  fi
  if [ -z "$canonical_description" ] || [ "$canonical_description" != "$bridge_description" ]; then
    echo "FAIL: description mismatch for $name" >&2
    fail=$((fail + 1))
  fi
  if grep -q 'TODO\|\[TODO' "$canonical" "$bridge"; then
    echo "FAIL: TODO remains in $name" >&2
    fail=$((fail + 1))
  fi
  if ! grep -q "../../../.agents/skills/$name/SKILL.md" "$bridge"; then
    echo "FAIL: Claude bridge target mismatch for $name" >&2
    fail=$((fail + 1))
  fi
  if LC_ALL=C grep -q '[^ -~]' "$metadata"; then
    echo "FAIL: non-ASCII UI metadata for $name" >&2
    fail=$((fail + 1))
  fi
}

check_skill setup-new-computer
check_skill create-new-project
check_skill assess-existing-project
check_skill standardize-existing-project
check_skill apply-promotion-candidate
check_skill promote-project-knowledge
check_skill reflect-and-record
check_skill compress-project
check_skill document-process-workflow

reflect_skill="$root/.agents/skills/reflect-and-record/SKILL.md"
check_required_literals "$reflect_skill" \
  'файл можно изменить в текущей' \
  'новым процессам/сессиям' \
  'перебором нескольких неудачных вариантов'
if grep -Fq 'не в середине' "$reflect_skill"; then
  echo "FAIL: reflect-and-record retains the retired mid-session edit prohibition" >&2
  fail=$((fail + 1))
fi

for file in \
  "$root/AGENTS.md" \
  "$root/templates/new-project/AGENTS.template.md"
do
  for heading in '## Knowledge Promotion' '## Defect Tracking'; do
    if ! grep -Fq "$heading" "$file"; then
      echo "FAIL: missing '$heading' in $file" >&2
      fail=$((fail + 1))
    fi
  done
done

agents_template="$root/templates/new-project/AGENTS.template.md"
if ! grep -Fq 'new-project-rules:begin schema=<SCHEMA_VERSION>' "$agents_template"; then
  echo "FAIL: AGENTS.template.md managed marker must use the <SCHEMA_VERSION> placeholder, not a hardcoded schema" >&2
  fail=$((fail + 1))
fi

for file in "$root/AGENTS.md" "$agents_template"; do
  compact_count=$(grep -Fc 'project_doc_max_bytes' "$file" || true)
  process_count=$(grep -Fc 'codex --ask-for-approval never' "$file" || true)
  if [ "$compact_count" -ne 1 ]; then
    echo "FAIL: $file must contain exactly one instruction-size rule" >&2
    fail=$((fail + 1))
  fi
  if [ "$process_count" -ne 1 ]; then
    echo "FAIL: $file must contain exactly one new-process verification rule" >&2
    fail=$((fail + 1))
  fi
done

if grep -Fq 'do not create repositories' "$agents_template"; then
  echo "FAIL: project baseline must not own new-project repository creation policy" >&2
  fail=$((fail + 1))
fi

shared_rule_literals='docs/quality/DEFECTS.md
immediately upon discovery
section where the entry
`Open`, `Fixed`, or `Won'"'"'t Fix`
move the entry to `Fixed`
docs/quality/PLAYBOOK.md
automatically, without waiting for a user reminder
working solution found after testing
raw memory directories.
validator, script, or skill
reusable engineering practice'

for file in \
  "$root/AGENTS.md" \
  "$root/templates/new-project/AGENTS.template.md"
do
  old_ifs=$IFS
  IFS='
'
  set -f
  check_required_literals "$file" $shared_rule_literals
  set +f
  IFS=$old_ifs
done

if [ "$fail" -ne 0 ]; then
  echo "$fail skill check(s) failed." >&2
  exit 1
fi

echo "All skill checks passed."
