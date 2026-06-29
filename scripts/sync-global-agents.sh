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

script_dir=$(resolve_script_dir)
python_command=
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    python_command=$candidate
    break
  fi
done
if [ -z "$python_command" ]; then
  echo "Python 3.9+ is required for global policy sync inspection." >&2
  exit 1
fi
exec "$python_command" "$script_dir/sync_global_agents.py" "$@"
