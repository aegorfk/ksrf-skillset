#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target="${CODEX_HOME:-$HOME/.codex}/skills"

mkdir -p "$target"

for skill_dir in "$repo_dir"/skills/ksrf-*; do
  [ -d "$skill_dir" ] || continue
  rsync -a --delete "$skill_dir/" "$target/$(basename "$skill_dir")/"
done

echo "Installed KSRF skills into $target"
