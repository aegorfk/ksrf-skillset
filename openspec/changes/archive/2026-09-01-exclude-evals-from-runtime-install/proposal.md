## Why

Пользовательская установка всё ещё получает 30 файлов `skills/*/evals/**` общим размером 94 270 байт на live base, хотя они нужны maintainers для behavioral/trigger QA и не используются рабочими сценариями skills. Простое исключение сейчас невозможно: portable validator считает отсутствие evals ошибкой и не отличает проверку исходного release от проверяемой runtime-установки.

## What Changes

- Ввести явные профили валидатора `source` и `runtime`.
- Сохранить `source` профилем по умолчанию и обязательным release-QA: он по-прежнему требует и полноценно проверяет behavioral/trigger evals.
- В `runtime`-профиле пропускать только eval-specific проверки, сохраняя проверки структуры, metadata, ссылок, безопасности, контрактов и состава пакетов.
- Явно записывать профиль, охват eval-проверки и public-source safety в JSON/text отчёте, чтобы runtime PASS или неполный source PASS нельзя было принять за release QA.
- Исключить exact path component `evals` из manifest-covered install payload вместе с `tests`.
- Сохранить source `tests/` и `evals/` byte-for-byte при global→repo sync и продолжить repository-wide public-source scanning этих каталогов.
- Заменить неработающую runtime-инструкцию на отсутствующие retrieval eval assets ручными evidence checks и stop rules.
- Подтвердить clean-room/global installation точными file/byte/tree hashes.

## Capabilities

### Modified Capabilities

- `ksrf-runtime-payload-boundary`: установленный payload больше не содержит maintainer eval suites и получает отдельный ограниченный режим валидации.

## Impact

- `tools/skillset_file_contract.py`, manifest generator и installer: новая development-only граница `tests|evals`.
- `skills/ksrf-complaint-cycle/scripts/validate_ksrf_skillset.py`: profile-aware source/runtime validation и честная маркировка охвата.
- Root и complaint-cycle tests: RED/GREEN для install, reverse sync, portable manifest и validator profiles.
- `skills-manifest.json`: меньший exact runtime payload.
- Legal/human/file/publication gates не меняются; runtime PASS не является release authority.
