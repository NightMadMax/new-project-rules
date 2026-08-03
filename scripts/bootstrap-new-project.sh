#!/bin/sh
set -eu

usage() {
  echo "Usage: $0 <destination> <project-name> [minimal|software|operated|all] [capability[,capability...]] [--preset <name>]" >&2
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

preset=
preset_seen=0
remaining=$#
while [ "$remaining" -gt 0 ]; do
  case "$1" in
    --preset)
      [ "$#" -ge 2 ] || usage
      [ "$preset_seen" -eq 0 ] || { echo "--preset given twice" >&2; exit 2; }
      preset=$2
      preset_seen=1
      shift 2
      remaining=$((remaining - 2))
      ;;
    --)
      shift
      remaining=$((remaining - 1))
      ;;
    *)
      set -- "$@" "$1"
      shift
      remaining=$((remaining - 1))
      ;;
  esac
done

[ "$#" -ge 2 ] && [ "$#" -le 4 ] || usage

destination=$1
project_name=$2
profile=${3:-minimal}
capability=${4:-}

[ -n "$destination" ] || { echo "Destination must not be empty" >&2; exit 2; }
[ -n "$project_name" ] || { echo "Project name must not be empty" >&2; exit 2; }

case "$profile" in
  minimal|software|operated|all) ;;
  *) usage ;;
esac

script_dir=$(resolve_script_dir)
project_rules_root=$(dirname "$script_dir")
templates="$project_rules_root/templates/new-project"
manifest="$project_rules_root/config/profiles.tsv"
capabilities_manifest="$project_rules_root/config/capabilities.tsv"
presets_manifest="$project_rules_root/config/presets.tsv"
capability_core_manifest="$project_rules_root/config/capability-core.tsv"
best_practices_stacks=
migrations_manifest="$project_rules_root/config/migrations.tsv"
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
project_migration_ids=$(awk -F "$tab" -v current="$standard_version" '
  NR > 1 && $2 == "project" { count[$3]++; next_schema[$3]=$4; migration_id[$3]=$1 }
  END {
    schema=0
    while (schema < current) {
      if (count[schema] != 1 || next_schema[schema] <= schema || next_schema[schema] > current) exit 2
      print migration_id[schema]
      schema=next_schema[schema]
    }
    if (schema != current) exit 2
  }
' "$migrations_manifest") || {
  echo "Invalid project migration path 0->$standard_version in $migrations_manifest" >&2
  exit 1
}
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

capability_selected() {
  case ",$capability," in
    *",$1,"*) return 0 ;;
    *) return 1 ;;
  esac
}

if [ -n "$preset" ]; then
  [ -f "$presets_manifest" ] || { echo "Preset manifest not found: $presets_manifest" >&2; exit 1; }
  presets_header="preset${tab}min_profile${tab}capabilities${tab}best_practices"
  [ "$(sed -n '1p' "$presets_manifest" | tr -d '\r')" = "$presets_header" ] || {
    echo "Invalid preset manifest header: $presets_manifest" >&2
    exit 1
  }
  preset_row=$(awk -F"$tab" -v want="$preset" 'NR>1 && $1==want {print; exit}' "$presets_manifest")
  [ -n "$preset_row" ] || { echo "Unknown preset '$preset'" >&2; exit 1; }
  preset_min_profile=$(printf '%s' "$preset_row" | cut -f2)
  preset_capabilities=$(printf '%s' "$preset_row" | cut -f3)
  preset_stacks=$(printf '%s' "$preset_row" | cut -f4)
  # The floor is raised, not rejected: asking for a preset with a lighter
  # profile means the preset, not a downgrade of its core.
  if [ "$(profile_rank "$profile")" -lt "$(profile_rank "$preset_min_profile")" ]; then
    profile=$preset_min_profile
  fi
  old_ifs=$IFS
  IFS=,
  for preset_capability in $preset_capabilities; do
    [ -n "$preset_capability" ] && [ "$preset_capability" != - ] || continue
    capability_selected "$preset_capability" || {
      if [ -z "$capability" ]; then capability=$preset_capability; else capability="$capability,$preset_capability"; fi
    }
  done
  IFS=$old_ifs
  best_practices_stacks=$preset_stacks
fi

expected_header="minimum_profile${tab}source${tab}destination${tab}root_purpose${tab}docs_section${tab}docs_label"
header=$(sed -n '1p' "$manifest")
[ "$header" = "$expected_header" ] || {
  echo "Invalid project profile manifest header: $manifest" >&2
  exit 1
}

capabilities_header="capability${tab}source${tab}destination${tab}root_purpose${tab}docs_section${tab}docs_label${tab}payload_class${tab}policy"
[ "$(sed -n '1p' "$capabilities_manifest")" = "$capabilities_header" ] || {
  echo "Invalid capability manifest header: $capabilities_manifest" >&2
  exit 1
}
known_capabilities=""
# Destinations are checked here and not only in the PowerShell adapter. Parity
# tests compare the produced trees, and for a healthy manifest both trees are
# identical — so a manifest check missing on one side is exactly what they
# cannot see (№249). Two capabilities writing into one path is the same class:
# whoever runs second owns a file the first one already recorded as its own.
seen_capability_destinations='|'
while IFS="$tab" read -r row_capability source artifact_destination root_purpose docs_section docs_label payload_class policy; do
  [ "$row_capability" = capability ] && continue
  known_capabilities="$known_capabilities$row_capability
"
  # Wrapped in slashes so the first and the last component are ordinary ones:
  # the earlier spelling anchored the pattern to a leading slash and therefore
  # matched `a/../b` but not `../b`.
  case "/$artifact_destination/" in
    */../*|*//*) echo "Unsafe capability destination '$artifact_destination'" >&2; exit 1 ;;
  esac
  case "$artifact_destination" in
    /*|*:*|*\\*) echo "Unsafe capability destination '$artifact_destination'" >&2; exit 1 ;;
  esac
  case "$seen_capability_destinations" in
    *"|$artifact_destination|"*)
      echo "Duplicate capability destination '$artifact_destination'" >&2
      exit 1
      ;;
  esac
  seen_capability_destinations="$seen_capability_destinations$artifact_destination|"
  [ -f "$templates/$source" ] || { echo "Capability template not found: $source" >&2; exit 1; }
  case "$(printf '%s' "$payload_class" | tr -d '\r')" in
    ""|-|template|verbatim|binary) ;;
    *) echo "Unknown payload class '$payload_class' for $artifact_destination" >&2; exit 1 ;;
  esac
done < "$capabilities_manifest"

# Whatever selected the capability - a preset or a positional argument - its
# core follows: a project cannot exist with the capability but without the
# profile and practice stack that capability requires.
apply_capability_core() {
  [ -n "$capability" ] || return 0
  [ -f "$capability_core_manifest" ] || {
    echo "Capability core manifest not found: $capability_core_manifest" >&2
    exit 1
  }
  core_first=1
  while IFS="$tab" read -r core_capability core_min_profile core_stack; do
    [ "$core_first" -eq 1 ] && { core_first=0; continue; }
    capability_selected "$core_capability" || continue
    if [ "$(profile_rank "$profile")" -lt "$(profile_rank "$core_min_profile")" ]; then
      profile=$core_min_profile
    fi
    [ -n "$core_stack" ] && [ "$core_stack" != - ] || continue
    case ",$best_practices_stacks," in
      *",$core_stack,"*) ;;
      *)
        if [ -z "$best_practices_stacks" ]; then
          best_practices_stacks=$core_stack
        else
          best_practices_stacks="$best_practices_stacks,$core_stack"
        fi
        ;;
    esac
  done < "$capability_core_manifest"
}

# A capability may be declared by a preset before it ships any artifact, so
# both manifests together define what "known" means.
if [ -f "$presets_manifest" ]; then
  known_capabilities="$known_capabilities$(awk -F"$tab" 'NR>1 {n=split($3, parts, ","); for (i=1; i<=n; i++) if (parts[i] != "" && parts[i] != "-") print parts[i]}' "$presets_manifest")
"
fi
old_ifs=$IFS
IFS=,
for selected_capability in $capability; do
  [ -n "$selected_capability" ] || continue
  printf '%s\n' "$known_capabilities" | grep -Fqx "$selected_capability" || {
    echo "Unknown capability '$selected_capability'" >&2
    exit 1
  }
done
IFS=$old_ifs

apply_capability_core

seen_destinations='|'
first=1
while IFS="$tab" read -r minimum source artifact_destination root_purpose docs_section docs_label; do
  if [ "$first" -eq 1 ]; then first=0; continue; fi
  profile_rank "$minimum" >/dev/null 2>&1 || {
    echo "Unknown minimum_profile '$minimum' in $manifest" >&2
    exit 1
  }
  case "/$artifact_destination/" in
    */../*|*//*) echo "Unsafe destination '$artifact_destination' in $manifest" >&2; exit 1 ;;
  esac
  case "$artifact_destination" in
    /*|*:*|*\\*) echo "Unsafe destination '$artifact_destination' in $manifest" >&2; exit 1 ;;
  esac
  case "$seen_destinations" in
    *"|$artifact_destination|"*)
      echo "Duplicate destination '$artifact_destination' in $manifest" >&2
      exit 1
      ;;
  esac
  case "$seen_capability_destinations" in
    *"|$artifact_destination|"*)
      echo "Capability destination conflicts with profile artifact '$artifact_destination'" >&2
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

# One directory is created once, and its name is computed without a process.
# Delivering a capability writes hundreds of files, and the old form spent two
# process spawns per file — `dirname` and an unconditional `mkdir -p` — which is
# cheap on Linux and is not on Windows, where the Python suite ran nine times
# slower than on Ubuntu almost entirely because of this loop.
made_directories=""
ensure_directory() {
  case $1 in
    */*) directory="$destination/${1%/*}" ;;
    *) directory="$destination" ;;
  esac
  case "$made_directories" in
    *"|$directory|"*) return 0 ;;
  esac
  mkdir -p "$directory"
  made_directories="$made_directories|$directory|"
}

install_template() {
  source_file=$1
  target_file=$2
  ensure_directory "$target_file"
  # Substitution only where there is something to substitute. `sed` in git-bash
  # rewrites line endings, so a template without placeholders arrived on Windows
  # with different bytes from the source it was copied from — and the first
  # capability update reported a conflict on a managed file nobody had touched.
  # The condition is the one the update handler uses to decide whether a file is
  # rendered, so delivery and comparison agree by construction.
  if grep -q '<PROJECT_NAME>\|<YYYY-MM-DD>\|<SCHEMA_VERSION>' "$templates/$source_file"; then
    sed "s|<PROJECT_NAME>|$escaped_name|g; s|<YYYY-MM-DD>|$today|g; s|<SCHEMA_VERSION>|$standard_version|g" \
      "$templates/$source_file" > "$destination/$target_file"
  else
    cp "$templates/$source_file" "$destination/$target_file"
  fi
}

# Byte-exact delivery: vendored payload and binaries must arrive unchanged, so
# no placeholder substitution and no text processing touches them.
install_verbatim() {
  source_file=$1
  target_file=$2
  ensure_directory "$target_file"
  cp "$templates/$source_file" "$destination/$target_file"
}

install_artifact() {
  source_file=$1
  target_file=$2
  # A manifest checked out with CRLF would otherwise yield "template\r".
  payload_class=$(printf '%s' "$3" | tr -d '\r')
  case "$payload_class" in
    ""|-|template) install_template "$source_file" "$target_file" ;;
    verbatim|binary) install_verbatim "$source_file" "$target_file" ;;
    *) echo "Unknown payload class '$payload_class' for $target_file" >&2; exit 1 ;;
  esac
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
      # Byte-exact payload must survive the commit as well: without -text the
      # generated rules above would normalise line endings on `git add`.
      if [ -n "$capability" ]; then
        attr_first=1
        while IFS="$tab" read -r attr_capability attr_source attr_destination attr_purpose attr_section attr_label attr_class attr_policy; do
          [ "$attr_first" -eq 1 ] && { attr_first=0; continue; }
          capability_selected "$attr_capability" || continue
          case "$(printf '%s' "$attr_class" | tr -d '\r')" in
            verbatim|binary) printf '%s -text\n' "$attr_destination" >> "$destination/$target" ;;
          esac
        done < "$capabilities_manifest"
      fi
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
      {
        printf '{\n  "schema_version": %s,\n  "profile": "%s",\n  "capabilities": [' "$standard_version" "$profile"
        first_capability=1
        old_ifs=$IFS
        IFS=,
        for metadata_capability in $capability; do
          [ -n "$metadata_capability" ] || continue
          if [ "$first_capability" -eq 1 ]; then first_capability=0; else printf ', '; fi
          printf '"%s"' "$metadata_capability"
        done
        IFS=$old_ifs
        printf '],\n  "capability_releases": {},\n  "source": "%s",\n  "source_commit": "%s",\n  "created_at": "%s",\n  "adopted_at": "%s",\n  "applied_migrations": [\n' \
          "$standard_source" "$source_commit" "$today" "$today"
        first_migration=1
        printf '%s\n' "$project_migration_ids" | while IFS= read -r migration_id; do
          [ -n "$migration_id" ] || continue
          if [ "$first_migration" -eq 1 ]; then first_migration=0; else printf ',\n'; fi
          printf '    "%s"' "$migration_id"
        done
        printf '\n  ]\n}\n'
      } > "$destination/$target"
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

if [ -n "$capability" ]; then
  first=1
  while IFS="$tab" read -r row_capability source artifact_destination root_purpose docs_section docs_label payload_class policy; do
    [ "$first" -eq 1 ] && { first=0; continue; }
    capability_selected "$row_capability" || continue
    install_artifact "$source" "$artifact_destination" "$payload_class"
  done < "$capabilities_manifest"

  # A capability also contributes lines to files the profile generates: what git
  # must not track, what git must not normalise, and which project files an
  # agent has to read. They cannot be separate artifacts because the generated
  # file already exists.
  for appendix_capability in $(printf '%s' "$capability" | tr ',' ' '); do
    appendix_root="$templates/capabilities/$appendix_capability/appendix"
    for appendix_name in gitignore gitattributes AGENTS.md; do
      appendix_file="$appendix_root/$appendix_name"
      [ -f "$appendix_file" ] || continue
      case "$appendix_name" in
        AGENTS.md) appendix_target=AGENTS.md; appendix_mark="<!-- capability: $appendix_capability -->" ;;
        *) appendix_target=".$appendix_name"; appendix_mark="# capability: $appendix_capability" ;;
      esac
      printf '\n%s\n' "$appendix_mark" >> "$destination/$appendix_target"
      cat "$appendix_file" >> "$destination/$appendix_target"
    done
  done
fi

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
  if grep -Fqx "## $heading" "$destination/docs/README.md"; then
    # Into the section that already exists: a second heading with the same name
    # splits the index, and a reader then trusts whichever half they saw first.
    awk -v heading="## $heading" -v entry="- [[$link_path|$label]]" '
      function flush(  i, last) {
        last = 0
        for (i = 1; i <= n; i++) if (substr(buffer[i], 1, 2) == "- ") last = i
        for (i = 1; i <= last; i++) print buffer[i]
        print entry
        for (i = last + 1; i <= n; i++) print buffer[i]
        inside = 0; n = 0
      }
      $0 == heading { inside = 1; n = 0; print; print ""; next }
      inside && /^## / { flush(); print; next }
      inside && n == 0 && $0 == "" { next }
      inside { buffer[++n] = $0; next }
      { print }
      END { if (inside) flush() }
    ' "$destination/docs/README.md" > "$destination/docs/README.md.tmp"
    mv "$destination/docs/README.md.tmp" "$destination/docs/README.md"
  else
    printf '\n## %s\n\n- [[%s|%s]]\n' "$heading" "$link_path" "$label" \
      >> "$destination/docs/README.md"
  fi
}

first=1
while IFS="$tab" read -r minimum source artifact_destination root_purpose docs_section docs_label; do
  if [ "$first" -eq 1 ]; then first=0; continue; fi
  includes_profile "$minimum" "$profile" || continue
  ensure_index_entry "$artifact_destination" "$root_purpose"
  ensure_docs_index_entry "$docs_section" "$artifact_destination" "$docs_label"
done < "$manifest"

if [ -n "$capability" ]; then
  first=1
  while IFS="$tab" read -r row_capability source artifact_destination root_purpose docs_section docs_label payload_class policy; do
    [ "$first" -eq 1 ] && { first=0; continue; }
    capability_selected "$row_capability" || continue
    ensure_index_entry "$artifact_destination" "$root_purpose"
    ensure_docs_index_entry "$docs_section" "$artifact_destination" "$docs_label"
  done < "$capabilities_manifest"
fi

if [ -n "$best_practices_stacks" ]; then
  {
    printf '{\n  "practices": {},\n  "preferences": {\n    "global": "ask",\n    "sections": {\n'
    first_stack=1
    old_ifs=$IFS
    IFS=,
    for stack in $best_practices_stacks; do
      [ -n "$stack" ] && [ "$stack" != - ] || continue
      if [ "$first_stack" -eq 1 ]; then first_stack=0; else printf ',\n'; fi
      printf '      "%s": "ask"' "$stack"
    done
    IFS=$old_ifs
    printf '\n    }\n  },\n  "schema_version": 2\n}\n'
  } > "$destination/.best-practices.json"
fi

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

echo "Created '$project_name' at $destination using profile '$profile'${capability:+ and capability '$capability'}."
echo "Keep this project inside the parent Obsidian vault, review INDEX.md, then create its GitHub repository."
trap - EXIT
