## Context

Frozen live base: `54a3b7cb7b08844aa4d46c1dfd5052aa30333681`. Текущий runtime manifest: 15 пакетов / 239 файлов / 8 221 998 байт.

Две пары файлов byte-identical:

| Skill duplicate | Root owner | Bytes | SHA256 |
|---|---|---:|---|
| `skills/ksrf-argument-patterns/scripts/enrich_ksrf_argument_patterns.py` | `tools/enrich_ksrf_argument_patterns.py` | 54 872 | `c5581c091cf62bb1042ea921b694b63b5da4e9c2c4508b9acffd4d34c039ffa6` |
| `skills/ksrf-argument-patterns/scripts/extract_ksrf_argument_patterns.py` | `tools/extract_ksrf_argument_patterns.py` | 14 590 | `cef29d616962463bf1c65b32956a9fdd21a0adbf8ed358670aed63e9cac38cff` |

После удаления двух дублей и добавления exact stale/security guards итоговый manifest содержит 237 файлов / 8 153 384 байт: на 2 файла / 68 614 байт меньше frozen base. Корневые release-tools в эти runtime-счётчики не входят, но остаются отдельно хэшированы манифестом.

После исправления default target и русификации CLI итоговые root-only SHA256: `enrich` — `c96c6bbd2639499d0a90cac1c804b97188af1f10f73ae3cc3f83d3623c31dfae`; `extract` — `f7d4a7f74593edf5a03bcd253e4e4e9bebe5d62dbbe577f34b0f9f61ebbe8149`.

Импортов и пользовательских CLI-ссылок нет. Оба инструмента обслуживают source-корпус: extract строит анализ из явно указанного PDF-корпуса, enrich потребляет результаты и перезаписывает generated references. `build_constitutionalist_authority_corpus.py` остаётся реальным runtime mirror и явно указан в `SKILL.md`.

## Decisions

1. **Ownership migration, а не третья копия исключения.** Nested duplicates удаляются; корневые файлы становятся единственными каноническими копиями.
2. **Три непересекающихся класса.** `MIRRORED_TOOL_NAMES` содержит только реальный mirror; `ROOT_ONLY_TOOL_NAMES` содержит два генератора; `RETIRED_MIRRORED_TOOL_NAMES` не используется для root-only файлов, иначе reverse-sync удалил бы канонические tools.
3. **Release coverage сохраняется.** `RELEASE_FILE_PATHS` строится из union mirrored и root-only names, поэтому публикационный манифест продолжает хэшировать оба генератора.
4. **Exact stale guard.** Два удалённых skill-пути добавляются в package-qualified source-only contract и portable validator. Случайно возвращённый файл не попадёт в runtime и будет отвергнут runtime-профилем; одноимённые или похожие файлы вне exact identity не overmatch.
5. **Reverse sync не владеет root-only.** Sync читает из global только active mirrored tools, не требует, не копирует и не удаляет root-only files.
6. **Исправляется default target.** `tools/enrich_ksrf_argument_patterns.py` по умолчанию указывает на `<repo>/skills/ksrf-argument-patterns`, а не ошибочно на корень репозитория.
7. **Source release запрещает возврат дублей.** Exact stale guard исключает старые копии из runtime, но canonical repository guard и portable source-профиль дополнительно завершаются ошибкой при самом наличии любого из двух nested-путей.
8. **Root-only security coverage сохраняется.** Перед manifest/release оба корневых генератора проходят exact content scan на встроенные токены, закрытые ключи и абсолютные локальные пути; сообщение об ошибке не раскрывает найденное значение.

## Risks / Trade-offs

- Старые внешние команды с nested path перестанут работать; публичных/runtime-ссылок на них нет, а активная OpenSpec-документация переводится на `tools/...`.
- Дублируемая exact allowlist в canonical и portable contracts может разойтись; parity test остаётся обязательным.
- Root-only tools не приезжают в `~/.codex/skills`; это намеренно, поскольку они обслуживают публикационный checkout, а не выполнение пользовательского скилла.
- Exact security scan ограничен двумя root-only release paths, чтобы синтетические тестовые fixtures и сам код детектора не создавали ложные срабатывания; расширение на другие release-tools требует отдельной калибровки.

## Migration Plan

1. Зафиксировать RED на ownership classes, release coverage, stale exact paths, reverse-sync semantics и default target.
2. Ввести root-only contract, исправить default, удалить nested duplicates и обновить ссылки.
3. Пересобрать manifest от frozen base, прогнать source/runtime QA и независимое ревью.
4. Опубликовать atomically в `main`, проверить live SHA, переустановить global runtime и архивировать change.

## Non-Goals

- Не удалять корневые инструменты или их release hashes.
- Не исключать весь `scripts/` и не применять basename/glob-правила.
- Не менять алгоритмы extraction/enrichment и юридическую методологию.
