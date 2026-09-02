#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="${CODEX_HOME:-$HOME/.codex}/skills"
target_dir="$repo_dir/skills"

if [[ ! -d "$source_dir" ]]; then
  echo "Global Codex skills directory does not exist: $source_dir" >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required for publication verification" >&2
  exit 1
}

python3 "$repo_dir/tools/verify_publication_state.py" --repo "$repo_dir"
base_commit="$(git -C "$repo_dir" rev-parse HEAD)"

argument_scripts="$source_dir/ksrf-argument-patterns/scripts"

# Validate all mirrored tools before changing either skills/ or tools/.
while IFS= read -r tool_name; do
  [[ -n "$tool_name" ]] || continue
  source_tool="$argument_scripts/$tool_name"
  target_tool="$repo_dir/tools/$tool_name"
  [[ -f "$source_tool" && ! -L "$source_tool" ]] || {
    echo "Required mirrored source tool is missing or symlinked: $source_tool" >&2
    echo "For an intentional rename/removal, update the active/retired allowlist first" >&2
    exit 1
  }
  if [[ -L "$target_tool" || ( -e "$target_tool" && ! -f "$target_tool" ) ]]; then
    echo "Refusing unsafe mirrored tool destination: $target_tool" >&2
    exit 1
  fi
done < <(python3 "$repo_dir/tools/skillset_file_contract.py" --active-mirrored-tools)

python3 "$repo_dir/tools/install_skillset.py" \
  --source-skills-root "$source_dir" \
  --preserve-target-development \
  --target "$target_dir"

while IFS= read -r tool_name; do
  [[ -n "$tool_name" ]] || continue
  cp "$argument_scripts/$tool_name" "$repo_dir/tools/$tool_name"
done < <(python3 "$repo_dir/tools/skillset_file_contract.py" --active-mirrored-tools)

# Only explicitly retired first-party mirrors may be removed automatically.
while IFS= read -r tool_name; do
  [[ -n "$tool_name" ]] || continue
  stale_tool="$repo_dir/tools/$tool_name"
  if [[ -e "$stale_tool" || -L "$stale_tool" ]]; then
    rm -f "$stale_tool"
  fi
done < <(python3 "$repo_dir/tools/skillset_file_contract.py" --retired-mirrored-tools)

python3 "$repo_dir/tools/generate_skills_manifest.py" \
  --repo "$repo_dir" \
  --base-commit "$base_commit"

echo "Synced global KSRF skills into $target_dir"
echo "Publication is still incomplete: validate, inspect the exact diff, commit atomically, push main, and verify the live remote SHA"
