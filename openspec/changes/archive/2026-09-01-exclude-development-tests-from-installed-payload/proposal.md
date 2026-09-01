## Why

Текущий manifest/install contract копирует в глобальные skills четыре дерева `skills/*/tests`: 47 файлов и 843607 байт. Эти файлы нужны maintainers для проверки исходников, но не импортируются runtime-кодом и не нужны пользователю установленного skillset. При этом `openspec/`, root `tests/`, `docs/` и `tools/` уже не входят в install payload, поэтому добавление `openspec/` в `.gitignore` не улучшит пользовательскую установку и уничтожит проверяемую историю разработки.

## What Changes

- Сохранить все тесты в исходном репозитории и в Git history.
- Исключить любой каталог `tests` внутри skill package из manifest-covered install payload.
- Сохранить tracked `tests/` при обратной синхронизации global skills в source checkout.
- Перенести ошибочно размещённый `scripts/test_ksrf_autocollect.py` в source `tests/`, чтобы он выполнялся full suite и не попадал в runtime.
- Оставить `evals/`, `agents/`, `scripts/`, `references/`, `schemas/`, `lib/` и fixtures вне `tests/` без изменений.
- Добавить RED/GREEN regression test, доказывающий отсутствие development tests в установленном skillset при сохранении runtime-файлов.
- Регенерировать manifest и подтвердить clean-room/global installation exact hashes.

## Capabilities

### New Capabilities

- `ksrf-runtime-payload-boundary`: установленный KSRF skillset содержит только runtime/review payload и не переносит maintainer-only unit tests.

### Modified Capabilities

Нет.

## Impact

- `tools/skillset_file_contract.py`: единая граница runtime payload и явно выделенных development-only paths.
- `tools/install_skillset.py`, `tools/sync_global_skills.sh`: exact runtime install и source-preserving reverse sync.
- `skills/ksrf-complaint-cycle/scripts/validate_ksrf_skillset.py`: portable publish manifest использует ту же development-only границу.
- `skills/ksrf-complaint-cycle/tests/test_ksrf_autocollect.py`: source-only regression в правильном test tree.
- `tests/test_install_skillset.py`: observable install regression.
- `skills-manifest.json`: новый exact runtime payload.
- Исходные тесты, OpenSpec, юридические gates и eval-контракты не удаляются и не ослабляются.
