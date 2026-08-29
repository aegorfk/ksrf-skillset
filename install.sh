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

skill_names=(
  ksrf-argument-patterns
  ksrf-case-triage
  ksrf-cassation-judicial-meaning
  ksrf-complaint-cycle
  ksrf-complaint-facts-demands
  ksrf-complaint-qa
  ksrf-court-request-motion
  ksrf-decision-execution
  ksrf-echr-argumentation
  ksrf-exhaustion-planner
  ksrf-explore-arguments
  ksrf-formal-filing-check
  ksrf-practice-authority-builder
  ksrf-rights-argument-builder
)

for bundled_dir in "$repo_dir"/skills/ksrf-*; do
  [[ -d "$bundled_dir" ]] || continue
  bundled_name="$(basename "$bundled_dir")"
  case " ${skill_names[*]} " in
    *" $bundled_name "*) ;;
    *)
      echo "Refusing undeclared bundled skill: $bundled_name" >&2
      exit 1
      ;;
  esac
done

for skill_name in "${skill_names[@]}"; do
  skill_dir="$repo_dir/skills/$skill_name"
  [[ -f "$skill_dir/SKILL.md" ]] || {
    echo "Required bundled skill is missing: $skill_dir" >&2
    exit 1
  }
  destination="$target/$skill_name"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$skill_dir/" "$destination/"
  else
    command -v python3 >/dev/null 2>&1 || {
      echo "python3 is required when rsync is unavailable" >&2
      exit 1
    }
    python3 - "$skill_dir" "$destination" "$target" <<'PY'
from pathlib import Path
import shutil
import sys

source = Path(sys.argv[1]).resolve(strict=True)
destination = Path(sys.argv[2]).resolve(strict=False)
target = Path(sys.argv[3]).resolve(strict=True)
if target == Path(target.anchor) or target == Path.home():
    raise SystemExit("Refusing a broad install target")
if destination.parent != target or destination.name != source.name:
    raise SystemExit("Install destination escaped the declared skills root")
if destination.is_symlink():
    raise SystemExit("Refusing to replace a symlinked skill destination")
if destination.exists():
    if not destination.is_dir():
        raise SystemExit("Skill destination exists and is not a directory")
    shutil.rmtree(destination)
shutil.copytree(source, destination)
PY
  fi
done

echo "Installed KSRF skills into $target"
