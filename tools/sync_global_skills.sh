#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="${CODEX_HOME:-$HOME/.codex}/skills"
target_dir="$repo_dir/skills"

if [[ ! -d "$source_dir" ]]; then
  echo "Global Codex skills directory does not exist: $source_dir" >&2
  exit 1
fi

mkdir -p "$target_dir"

for skill_dir in "$source_dir"/ksrf-*; do
  [[ -d "$skill_dir" ]] || continue
  rsync -a --delete --delete-excluded \
    --exclude='.DS_Store' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    "$skill_dir/" "$target_dir/$(basename "$skill_dir")/"
done

argument_scripts="$source_dir/ksrf-argument-patterns/scripts"
for tool_name in \
  build_constitutionalist_authority_corpus.py \
  enrich_ksrf_argument_patterns.py \
  extract_ksrf_argument_patterns.py; do
  if [[ -f "$argument_scripts/$tool_name" ]]; then
    cp "$argument_scripts/$tool_name" "$repo_dir/tools/$tool_name"
  fi
done

echo "Synced global KSRF skills into $target_dir"
