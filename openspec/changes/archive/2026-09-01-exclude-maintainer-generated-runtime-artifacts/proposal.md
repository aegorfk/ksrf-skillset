## Why

После исключения `tests/` и `evals/` пользовательская установка всё ещё получает пять подтверждённых maintainer-only файлов общим размером 164 081 байт. Четыре JSON являются generated snapshots без runtime-consumer backlinks, а `scripts/add_reference_tocs.py` вызывается только source-тестом для массового обслуживания справочников. Они нужны в репозитории для воспроизводимости и QA, но не для выполнения пользовательских skills.

## What Changes

- Добавить точный source-only allowlist из пары `skill name + relative path` для пяти файлов, без широкого исключения по расширению, имени каталога или всему `scripts/`.
- Исключить эти файлы из canonical manifest, portable publish manifest и пользовательской установки.
- Сохранять source-копии byte-for-byte при global→repo sync, как уже сохраняются `tests/` и `evals/`.
- Требовать, чтобы runtime-профиль валидатора отклонял stale-копии этих exact paths, но source-профиль продолжал их security/public-source проверку.
- Защитить рабочие JSON, схемы и исполняемые scripts adversarial-тестами от случайного исключения.
- Зафиксировать удаление 5 source-only файлов / 164 081 байта и подтвердить exact clean-room/global hashes. С учётом нового runtime-контракта и пояснений итоговый manifest уменьшается с 244 / 8 385 193 до 239 / 8 221 998 файлов/байт, то есть на 5 файлов и 163 195 байт net.

## Capabilities

### Modified Capabilities

- `ksrf-runtime-payload-boundary`: installed payload исключает дополнительный точный набор maintainer-generated artifacts, сохраняя их в source QA.

## Impact

- `tools/skillset_file_contract.py`: versioned exact source-only path contract и reverse-sync preservation.
- Portable validator: совпадающий exact allowlist, runtime cleanliness и source safety.
- Installer/manifest/root tests: RED/GREEN для exact exclusion, non-overmatching и preservation.
- `skills-manifest.json`: уменьшенный runtime payload.
- Пользовательские сценарии, legal gates, active schemas/scripts и source release QA не меняются.
