#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
canonical_target="${CODEX_HOME:-$HOME/.codex}/skills"
target="$canonical_target"

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

command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required for publication-safe installation" >&2
  exit 1
}

resolved_target="$(python3 - "$target" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
)"
resolved_canonical_target="$(python3 - "$canonical_target" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
)"

if [[ "$resolved_target" == "$resolved_canonical_target" ]]; then
  python3 "$repo_dir/tools/verify_publication_state.py" --repo "$repo_dir"
else
  echo "Custom-target clean-room install: canonical global skills will not be changed"
fi

python3 "$repo_dir/tools/install_skillset.py" --repo "$repo_dir" --target "$target"
