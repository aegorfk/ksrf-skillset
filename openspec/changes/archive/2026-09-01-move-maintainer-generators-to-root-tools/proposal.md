## Why

Пользовательская установка всё ещё содержит две идентичные копии инструментов сопровождения корпуса: `enrich_ksrf_argument_patterns.py` и `extract_ksrf_argument_patterns.py`. Ни один runtime-сценарий, `SKILL.md` или импорт их не использует; канонические byte-identical копии уже входят в корневой `tools/` и в release manifest. Дубли занимают 69 462 байта и создают опасную двустороннюю синхронизацию.

## What Changes

- Оставить оба генератора только в корневом `tools/` как явно классифицированные root-only release tools.
- Удалить их дубли из `skills/ksrf-argument-patterns/scripts/` и запретить случайное возвращение этих exact runtime-путей.
- Сохранить единственный реальный зеркальный runtime-tool `build_constitutionalist_authority_corpus.py`.
- Исправить default target корневого enrich-инструмента на `skills/ksrf-argument-patterns`.
- Обновить reverse-sync, release coverage, OpenSpec-ссылки, документацию и тесты.

## Impact

- Из пользовательской установки исчезают 2 файла / 69 462 байта. После добавления exact guard и release-security checks итоговый manifest уменьшается с 239 / 8 221 998 до 237 / 8 153 384 файлов/байт: net-экономия 2 файла / 68 614 байт.
- Пользовательская функциональность не меняется: runtime-backlinks и imports отсутствуют, а явно маршрутизированный corpus builder остаётся.
- Source/release воспроизводимость сохраняется: оба root-only tools остаются tracked, исполняемыми и хэшируются в `skills-manifest.json`.
- Юридические, human-review, filing и publication gates не расширяются.
