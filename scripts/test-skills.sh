#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
root=$(dirname "$script_dir")
fail=0

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
check_skill promote-project-knowledge
check_skill reflect-and-record

for file in \
  "$root/AGENTS.md" \
  "$root/GLOBAL_AGENT_INSTRUCTIONS.md" \
  "$root/templates/new-project/AGENTS.template.md"
do
  for heading in '## Knowledge Promotion' '## Defect Tracking'; do
    if ! grep -Fq "$heading" "$file"; then
      echo "FAIL: missing '$heading' in $file" >&2
      fail=$((fail + 1))
    fi
  done
done

if [ "$fail" -ne 0 ]; then
  echo "$fail skill check(s) failed." >&2
  exit 1
fi

echo "All skill checks passed."
