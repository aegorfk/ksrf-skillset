#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target="${CODEX_HOME:-$HOME/.codex}/skills"

usage() {
  cat <<'EOF'
Usage: ./install.sh [--target PATH]

Install all bundled KSRF skills. By default the target is
CODEX_HOME/skills when CODEX_HOME is set, otherwise HOME/.codex/skills. Use
--target for a clean-room or custom installation without changing either
environment variable.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      [[ $# -ge 2 ]] || { echo "--target requires PATH" >&2; exit 2; }
      target="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ -n "$target" ]] || { echo "Install target must not be empty" >&2; exit 2; }

mkdir -p "$target"

for skill_dir in "$repo_dir"/skills/ksrf-*; do
  [ -d "$skill_dir" ] || continue
  destination="$target/$(basename "$skill_dir")"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$skill_dir/" "$destination/"
  else
    mkdir -p "$destination"
    cp -R "$skill_dir/." "$destination/"
  fi
done

echo "Installed KSRF skills into $target"
