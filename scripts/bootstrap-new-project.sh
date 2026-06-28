#!/bin/sh
set -eu

usage() {
  echo "Usage: $0 <destination> <project-name> [minimal|software|operated|all]" >&2
  exit 2
}

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

directory_is_empty() {
  for entry in "$1"/* "$1"/.[!.]* "$1"/..?*; do
    if [ -e "$entry" ] || [ -L "$entry" ]; then
      return 1
    fi
  done
  return 0
}

[ "$#" -ge 2 ] && [ "$#" -le 3 ] || usage

destination=$1
project_name=$2
profile=${3:-minimal}

case "$profile" in
  minimal|software|operated|all) ;;
  *) usage ;;
esac

script_dir=$(resolve_script_dir)
project_rules_root=$(dirname "$script_dir")
templates="$project_rules_root/templates/new-project"

if [ -d "$destination" ] && ! directory_is_empty "$destination"; then
  echo "Destination is not empty: $destination" >&2
  exit 1
fi

mkdir -p "$destination/.obsidian"
printf '{}\n' > "$destination/.obsidian/app.json"
printf '%s\n' '.DS_Store' 'Thumbs.db' '.trash/' '.obsidian/workspace.json' \
  '.obsidian/workspace-mobile.json' '.obsidian/cache/' \
  'CLAUDE.local.md' '.claude/settings.local.json' '.claude/scheduled_tasks.lock' \
  > "$destination/.gitignore"
printf '%s\n' '* text=auto' '*.sh text eol=lf' '*.ps1 text eol=crlf' \
  '*.md text eol=lf' '*.json text eol=lf' > "$destination/.gitattributes"

# EditorConfig is the one language-agnostic, zero-dependency formatting baseline
# every editor honours, so it belongs in the required core of every project.
cat > "$destination/.editorconfig" <<'EDITORCONFIG'
# EditorConfig — https://editorconfig.org
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false

[*.ps1]
end_of_line = crlf
indent_size = 4

[Makefile]
indent_style = tab

[*.go]
indent_style = tab
EDITORCONFIG

today=$(date +%Y-%m-%d)
escaped_name=$(printf '%s' "$project_name" | sed 's/[&|\\]/\\&/g')

install_template() {
  source_file=$1
  target_file=$2
  mkdir -p "$(dirname "$destination/$target_file")"
  sed "s|<PROJECT_NAME>|$escaped_name|g; s|<YYYY-MM-DD>|$today|g" \
    "$templates/$source_file" > "$destination/$target_file"
}

install_template README.template.md README.md
install_template AGENTS.template.md AGENTS.md
install_template INDEX.template.md INDEX.md
install_template PROJECT.template.md PROJECT.md

# CLAUDE.md is a portable pointer so Claude Code reads the same AGENTS.md that
# Codex and other AGENTS.md-aware tools read. A one-line @import avoids fragile
# symlinks on Windows and never duplicates instruction content.
printf '@AGENTS.md\n' > "$destination/CLAUDE.md"

append_index() {
  link_path=${1%.md}
  printf '| [[%s|%s]] | %s |\n' "$link_path" "$1" "$2" >> "$destination/INDEX.md"
}

if [ "$profile" != minimal ]; then
  install_template DOCS_INDEX.template.md docs/README.md
  install_template CHANGELOG.template.md CHANGELOG.md
  install_template ARCHITECTURE.template.md docs/architecture/ARCHITECTURE.md
  install_template TESTING.template.md docs/quality/TESTING.md
  append_index docs/README.md "Documentation directory index"
  append_index CHANGELOG.md "User-visible changes and releases"
  append_index docs/architecture/ARCHITECTURE.md "Current system architecture"
  append_index docs/quality/TESTING.md "Testing strategy and acceptance criteria"
fi

if [ "$profile" = operated ] || [ "$profile" = all ]; then
  install_template ACTIONS.template.md ACTIONS.md
  install_template TOOLS.template.md TOOLS.md
  install_template INTEGRATIONS.template.md INTEGRATIONS.md
  install_template ENVIRONMENTS.template.md docs/operations/ENVIRONMENTS.md
  append_index ACTIONS.md "Consequential actions outside git"
  append_index TOOLS.md "Non-obvious project tools and helper scripts"
  append_index INTEGRATIONS.md "External systems and integrations"
  append_index docs/operations/ENVIRONMENTS.md "Environment differences without secrets"
fi

if [ "$profile" = all ]; then
  install_template INTERFACES.template.md docs/api/INTERFACES.md
  install_template DATA_MODEL.template.md docs/data/DATA_MODEL.md
  install_template SECURITY.template.md SECURITY.md
  install_template THREAT_MODEL.template.md docs/security/THREAT_MODEL.md
  append_index docs/api/INTERFACES.md "Interface catalog and links to API specifications"
  append_index docs/data/DATA_MODEL.md "Data model and migration rules"
  append_index SECURITY.md "Vulnerability reporting policy"
  append_index docs/security/THREAT_MODEL.md "Threats, mitigations, and residual risks"
fi

if command -v git >/dev/null 2>&1; then
  if ! git_output=$(git -C "$destination" init 2>&1); then
    printf 'Git initialization failed:\n%s\n' "$git_output" >&2
    exit 1
  fi
  if ! git_output=$(git -C "$destination" symbolic-ref HEAD refs/heads/main 2>&1); then
    printf 'Setting the initial git branch to main failed:\n%s\n' "$git_output" >&2
    exit 1
  fi
  if ! git_output=$(git -C "$destination" add -A 2>&1); then
    printf 'Staging the initial project files failed:\n%s\n' "$git_output" >&2
    exit 1
  fi

  if git -C "$destination" var GIT_AUTHOR_IDENT >/dev/null 2>&1 && \
     git -C "$destination" var GIT_COMMITTER_IDENT >/dev/null 2>&1; then
    if ! git_output=$(git -C "$destination" commit -q -m "Bootstrap project with new-project-rules" 2>&1); then
      printf 'Creating the initial git commit failed:\n%s\n' "$git_output" >&2
      exit 1
    fi
    echo "Initialized git repository with an initial commit."
  else
    echo "Initialized git repository with staged files; set git user.name and git user.email, then commit the initial state." >&2
  fi
else
  echo "Git was not found; project files were created, but the repository was not initialized." >&2
fi

echo "Created '$project_name' at $destination using profile '$profile'."
echo "Open this folder as an Obsidian vault, review INDEX.md, then create its GitHub repository."
