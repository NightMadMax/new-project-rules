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
manifest="$project_rules_root/config/profiles.tsv"
standard_source_file="$project_rules_root/config/standard-source.txt"
standard_version_file="$project_rules_root/STANDARD_VERSION"
tab=$(printf '\t')

command -v git >/dev/null 2>&1 || {
  echo "Git is required to record project-standard provenance and initialize the project repository." >&2
  exit 1
}
standard_source=$(tr -d '\r\n' < "$standard_source_file") || exit 1
standard_version=$(tr -d '\r\n' < "$standard_version_file") || exit 1
source_commit=$(git -C "$project_rules_root" rev-parse --verify HEAD 2>/dev/null) || {
  echo "Cannot resolve the new-project-rules source commit from $project_rules_root." >&2
  exit 1
}
case "$standard_source" in
  ''|/*|*/|*/*/*|*[!A-Za-z0-9_./-]*) echo "Invalid standard source: $standard_source" >&2; exit 1 ;;
  */*) ;;
esac
case "$standard_version" in
  ''|*[!0-9]*|0) echo "Invalid STANDARD_VERSION: $standard_version" >&2; exit 1 ;;
esac
[ "${#source_commit}" -eq 40 ] || {
  echo "Invalid new-project-rules source commit: $source_commit" >&2
  exit 1
}
case "$source_commit" in
  *[!0-9a-f]*) echo "Invalid new-project-rules source commit: $source_commit" >&2; exit 1 ;;
esac

profile_rank() {
  case "$1" in
    minimal) echo 0 ;;
    software) echo 1 ;;
    operated) echo 2 ;;
    all) echo 3 ;;
    *) return 1 ;;
  esac
}

includes_profile() {
  minimum_rank=$(profile_rank "$1") || return 1
  selected_rank=$(profile_rank "$2") || return 1
  [ "$minimum_rank" -le "$selected_rank" ]
}

expected_header="minimum_profile${tab}source${tab}destination${tab}root_purpose${tab}docs_section${tab}docs_label"
header=$(sed -n '1p' "$manifest")
[ "$header" = "$expected_header" ] || {
  echo "Invalid project profile manifest header: $manifest" >&2
  exit 1
}

seen_destinations='|'
first=1
while IFS="$tab" read -r minimum source artifact_destination root_purpose docs_section docs_label; do
  if [ "$first" -eq 1 ]; then first=0; continue; fi
  profile_rank "$minimum" >/dev/null 2>&1 || {
    echo "Unknown minimum_profile '$minimum' in $manifest" >&2
    exit 1
  }
  case "/$artifact_destination/" in
    /*/../*|//*) echo "Unsafe destination '$artifact_destination' in $manifest" >&2; exit 1 ;;
  esac
  case "$seen_destinations" in
    *"|$artifact_destination|"*)
      echo "Duplicate destination '$artifact_destination' in $manifest" >&2
      exit 1
      ;;
  esac
  seen_destinations="$seen_destinations$artifact_destination|"
  if [ "$source" = @generated ]; then
    case "$artifact_destination" in
      .editorconfig|.gitattributes|.gitignore|.project-standard.json|CLAUDE.md) ;;
      *) echo "Unknown generated artifact '$artifact_destination' in $manifest" >&2; exit 1 ;;
    esac
  elif [ ! -f "$templates/$source" ]; then
    echo "Template not found for '$artifact_destination': $source" >&2
    exit 1
  fi
  if { [ "$docs_section" = - ] && [ "$docs_label" != - ]; } ||
     { [ "$docs_section" != - ] && [ "$docs_label" = - ]; }; then
    echo "docs_section and docs_label must both be '-' or both be set for '$artifact_destination'" >&2
    exit 1
  fi
done < "$manifest"

destination_existed=0
if [ -d "$destination" ]; then
  destination_existed=1
fi
if [ "$destination_existed" -eq 1 ] && ! directory_is_empty "$destination"; then
  echo "Destination is not empty: $destination" >&2
  exit 1
fi

cleanup_failed_bootstrap() {
  status=$?
  trap - EXIT
  if [ "$status" -ne 0 ]; then
    rm -rf "$destination"
    if [ "$destination_existed" -eq 1 ]; then
      mkdir -p "$destination"
    fi
  fi
  exit "$status"
}
trap cleanup_failed_bootstrap EXIT

mkdir -p "$destination"
today=$(date +%Y-%m-%d)
escaped_name=$(printf '%s' "$project_name" | sed 's/[&|\\]/\\&/g')

install_template() {
  source_file=$1
  target_file=$2
  mkdir -p "$(dirname "$destination/$target_file")"
  sed "s|<PROJECT_NAME>|$escaped_name|g; s|<YYYY-MM-DD>|$today|g" \
    "$templates/$source_file" > "$destination/$target_file"
}

install_generated() {
  target=$1
  case "$target" in
    .gitignore)
      printf '%s\n' '.DS_Store' 'Thumbs.db' '.obsidian/' '.trash/' 'CLAUDE.local.md' \
        '.claude/settings.local.json' '.claude/scheduled_tasks.lock' \
        > "$destination/$target"
      ;;
    .gitattributes)
      printf '%s\n' '* text=auto' '*.sh text eol=lf' '*.ps1 text eol=crlf' \
        '*.md text eol=lf' '*.json text eol=lf' > "$destination/$target"
      ;;
    .editorconfig)
      cat > "$destination/$target" <<'EDITORCONFIG'
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
      ;;
    CLAUDE.md) printf '@AGENTS.md\n' > "$destination/$target" ;;
    .project-standard.json)
      printf '{\n  "schema_version": %s,\n  "profile": "%s",\n  "source": "%s",\n  "source_commit": "%s",\n  "created_at": "%s",\n  "adopted_at": "%s",\n  "applied_migrations": [\n    "0001-adopt-project-standard"\n  ]\n}\n' \
        "$standard_version" "$profile" "$standard_source" "$source_commit" "$today" "$today" \
        > "$destination/$target"
      ;;
    *) echo "Unknown generated artifact: $target" >&2; exit 1 ;;
  esac
}

first=1
while IFS="$tab" read -r minimum source artifact_destination root_purpose docs_section docs_label; do
  if [ "$first" -eq 1 ]; then first=0; continue; fi
  includes_profile "$minimum" "$profile" || continue
  if [ "$source" = @generated ]; then
    install_generated "$artifact_destination"
  else
    install_template "$source" "$artifact_destination"
  fi
done < "$manifest"

ensure_index_entry() {
  path=$1
  purpose=$2
  [ "$purpose" != - ] || return 0
  link_path=${path%.md}
  if grep -Fq "[[$link_path" "$destination/INDEX.md"; then
    return 0
  else
    grep_status=$?
  fi
  [ "$grep_status" -eq 1 ] || {
    echo "Could not read $destination/INDEX.md while indexing '$path'." >&2
    exit 1
  }
  printf '| [[%s|%s]] | %s |\n' "$link_path" "$path" "$purpose" >> "$destination/INDEX.md"
}

ensure_docs_index_entry() {
  heading=$1
  path=$2
  label=$3
  [ "$heading" != - ] || return 0
  link_path=${path%.md}
  if grep -Fq "[[$link_path" "$destination/docs/README.md"; then
    return 0
  else
    grep_status=$?
  fi
  [ "$grep_status" -eq 1 ] || {
    echo "Could not read $destination/docs/README.md while indexing '$path'." >&2
    exit 1
  }
  printf '\n## %s\n\n- [[%s|%s]]\n' "$heading" "$link_path" "$label" \
    >> "$destination/docs/README.md"
}

first=1
while IFS="$tab" read -r minimum source artifact_destination root_purpose docs_section docs_label; do
  if [ "$first" -eq 1 ]; then first=0; continue; fi
  includes_profile "$minimum" "$profile" || continue
  ensure_index_entry "$artifact_destination" "$root_purpose"
  ensure_docs_index_entry "$docs_section" "$artifact_destination" "$docs_label"
done < "$manifest"

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

echo "Created '$project_name' at $destination using profile '$profile'."
echo "Keep this project inside the parent Obsidian vault, review INDEX.md, then create its GitHub repository."
trap - EXIT
