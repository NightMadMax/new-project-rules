#!/bin/sh
set -u

resolve_script_dir() {
  case $0 in
    */*) script_path=$0 ;;
    *) script_path=$(command -v "$0") || { echo "Cannot resolve script path: $0" >&2; exit 1; } ;;
  esac
  while [ -L "$script_path" ]; do
    link_dir=$(CDPATH= cd -P "$(dirname "$script_path")" && pwd) || exit 1
    link_target=$(readlink "$script_path") || exit 1
    case $link_target in
      /*) script_path=$link_target ;;
      *) script_path=$link_dir/$link_target ;;
    esac
  done
  CDPATH= cd -P "$(dirname "$script_path")" && pwd
}

usage() {
  echo "Usage: $0 [--root PATH] [--agent-mode codex|claude|both] [--profile auto|minimal|software|operated|all] [--report-only]" >&2
  exit 2
}

root=.
agent_mode=both
profile=auto
report_only=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --root) [ "$#" -ge 2 ] || usage; root=$2; shift 2 ;;
    --agent-mode) [ "$#" -ge 2 ] || usage; agent_mode=$2; shift 2 ;;
    --profile) [ "$#" -ge 2 ] || usage; profile=$2; shift 2 ;;
    --report-only) report_only=1; shift ;;
    *) usage ;;
  esac
done
case "$agent_mode" in codex|claude|both) ;; *) usage ;; esac
case "$profile" in auto|minimal|software|operated|all) ;; *) usage ;; esac

script_dir=$(resolve_script_dir)
echo "Environment diagnostics:"
sh "$script_dir/check-environment.sh" "$agent_mode"
environment_exit=$?

echo
echo "Project diagnostics:"
python_command=
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    python_command=$candidate
    break
  fi
done

if [ -z "$python_command" ]; then
  echo "[WARN] validator.runtime: Python 3.9+ is unavailable; structural validation was skipped."
  validator_exit=0
else
  if [ "$report_only" -eq 1 ]; then
    "$python_command" "$script_dir/validate-project.py" --root "$root" --kind auto \
      --profile "$profile" --doctor --report-only
  else
    "$python_command" "$script_dir/validate-project.py" --root "$root" --kind auto \
      --profile "$profile" --doctor
  fi
  validator_exit=$?
fi

[ "$report_only" -eq 0 ] || exit 0
[ "$validator_exit" -ne 2 ] || exit 2
if [ "$environment_exit" -ne 0 ] || [ "$validator_exit" -ne 0 ]; then exit 1; fi
exit 0
