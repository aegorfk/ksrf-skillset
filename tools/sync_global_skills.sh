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
  rsync -a --delete "$skill_dir/" "$target_dir/$(basename "$skill_dir")/"
done

echo "Synced global KSRF skills into $target_dir"
