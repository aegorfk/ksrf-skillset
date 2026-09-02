#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
canonical_target="${CODEX_HOME:-$HOME/.codex}/skills"
target="$canonical_target"
status_mode=false
verify_current_mode=false
json_mode=false

usage() {
  cat <<'EOF'
Использование: ./install.sh [--target ПУТЬ] [--status [--json]|--verify-current]

Установить все 15 навыков КС РФ из этого выпуска. По умолчанию используется
CODEX_HOME/skills, а если CODEX_HOME не задан — HOME/.codex/skills. Параметр
--target задаёт отдельную папку без изменения переменных окружения. Параметр
--status без записи проверяет состояние: он не запускает восстановление,
очистку или блокировку, но файловая система может обновить atime при чтении.
Параметр --verify-current явно использует сеть: проверяет runtime-содержимое
выбранной папки и сравнивает его с текущим опубликованным main.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      [[ $# -ge 2 && "$2" != -* ]] || {
        echo "Параметр --target требует путь, а не другой параметр" >&2
        exit 2
      }
      target="$2"
      shift 2
      ;;
    --status)
      status_mode=true
      shift
      ;;
    --verify-current)
      verify_current_mode=true
      shift
      ;;
    --json)
      json_mode=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Неизвестный параметр: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ -n "$target" ]] || { echo "Путь установки не может быть пустым" >&2; exit 2; }
if [[ "$status_mode" == true && "$verify_current_mode" == true ]]; then
  echo "Параметры --status и --verify-current нельзя использовать вместе" >&2
  exit 2
fi
if [[ "$json_mode" == true && "$status_mode" != true ]]; then
  echo "Параметр --json можно использовать только вместе с --status" >&2
  exit 2
fi

command -v python3 >/dev/null 2>&1 || {
  echo "Для проверяемой установки требуется python3" >&2
  exit 1
}

if [[ "$verify_current_mode" == true ]]; then
  validator="$repo_dir/skills/ksrf-complaint-cycle/scripts/validate_ksrf_skillset.py"
  if [[ ! -f "$validator" || -L "$validator" ]]; then
    echo "Repo-side runtime-валидатор недоступен; обновите репозиторий из опубликованного main" >&2
    exit 1
  fi
  set +e
  preflight_output="$(
    PYTHONDONTWRITEBYTECODE=1 python3 "$repo_dir/tools/install_skillset.py" \
      --status --target "$target"
  )"
  preflight_exit=$?
  set -e
  if [[ "$preflight_exit" -ne 0 ]]; then
    if [[ -n "$preflight_output" ]]; then
      printf '%s\n' "$preflight_output" >&2
    fi
    echo "Проверка актуальности не запускалась: сначала нужна безопасная полная установка" >&2
    exit 1
  fi
  verify_args=(
    --skills-root "$target"
    --profile runtime
    --strict
    --check-updates
    --require-current
  )
  exec python3 "$validator" "${verify_args[@]}"
fi

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

if [[ "$status_mode" == true ]]; then
  status_args=(--status --target "$target")
  if [[ "$json_mode" == true ]]; then
    status_args+=(--json)
  fi
  exec python3 "$repo_dir/tools/install_skillset.py" "${status_args[@]}"
fi

if [[ "$resolved_target" == "$resolved_canonical_target" ]]; then
  python3 "$repo_dir/tools/verify_publication_state.py" --repo "$repo_dir"
else
  echo "Установка в отдельную папку: глобальные навыки изменены не будут"
fi

python3 "$repo_dir/tools/install_skillset.py" --repo "$repo_dir" --target "$target"

python3 - "$resolved_target" <<'PY'
import shlex
import sys

print(f"export KSRF_SKILLS_ROOT={shlex.quote(sys.argv[1])}")
PY
