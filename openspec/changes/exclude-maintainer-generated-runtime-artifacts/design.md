## Context

Live source base: `b76026d1f16cc0d8c634a8ede8004ad5864545ff`. После предыдущего cleanup runtime manifest содержит 244 файла / 8 385 193 байта. Backlink-аудит выделил пять файлов, которые обслуживают только source maintenance:

| Source path | Bytes | Source role |
|---|---:|---|
| `ksrf-argument-patterns/references/hearing_argument_techniques.json` | 74 801 | generated snapshot; runtime guide использует Markdown и официальный/source route |
| `ksrf-argument-patterns/references/language_formulas.json` | 44 202 | output maintainer enrichment script; runtime backlinks отсутствуют |
| `ksrf-argument-patterns/references/evidence_maps.json` | 23 765 | output maintainer enrichment script; runtime backlinks отсутствуют |
| `ksrf-argument-patterns/references/argument_techniques_from_decisions.json` | 8 852 | generated marker-pass snapshot; runtime backlinks отсутствуют |
| `ksrf-complaint-cycle/scripts/add_reference_tocs.py` | 12 461 | source maintenance helper; вызывается только source test |

Пять исключаемых файлов занимают 164 081 байт. После добавления exact runtime-контракта и пояснений итоговый manifest составляет 239 файлов / 8 221 998 байт против 244 / 8 385 193 на frozen base: net-экономия 5 файлов / 163 195 байт. Рабочие machine-readable assets (`constitutional_graph.json`, `constitutionalist-authority-corpus.json`, Lawinfo cards, configs, schemas) и исполняемые runtime scripts остаются в payload.

## Goals / Non-Goals

**Goals**

- Уменьшить пользовательскую установку только на доказанную exact allowlist.
- Сохранить source artifacts, tests и воспроизводимость генерации.
- Сделать canonical installer/manifest и portable validator наблюдаемо согласованными.
- Fail closed при stale maintainer-only file в runtime-копии.

**Non-Goals**

- Не удалять файлы из репозитория и не скрывать tracked source через `.gitignore`.
- Не исключать все JSON, все generated-файлы, весь `references/` или весь `scripts/`.
- Не менять содержание юридических методик или полномочия release/filing gates.

## Decisions

1. **Ключ — skill name + exact POSIX-relative path.** Canonical contract хранит versioned set пар, а не basename/prefix/glob. Файл с тем же именем в другом skill и похожий `*-guide.json` остаются runtime-eligible.
2. **Единый development-only predicate.** `payload_files()` передаёт имя skill; `development_files()` использует тот же predicate, поэтому install исключает exact paths, а reverse sync сохраняет их byte-for-byte.
3. **Public-source scan не ослабляется.** При `include_development=true` exact paths проходят canonical public artifact scan так же, как `tests/` и `evals/`.
4. **Portable duplicate минимален и тестируем.** Standalone validator содержит тот же exact set; source manifest security-сканирует, но не публикует эти файлы, runtime profile отклоняет stale copies с `SOURCE_ONLY_ARTIFACT_PRESENT`.
5. **Manifest объясняет состав.** Generated manifest перечисляет exact exclusions в metadata и пересчитывается от frozen base SHA.
6. **No deletion.** Source files и их maintainer test остаются tracked. `.gitignore` не используется, потому что он не удаляет уже tracked bytes из install contract и скрыл бы воспроизводимые QA assets от контроля версий.

## Risks / Trade-offs

- Дублирование allowlist в canonical contract и portable validator может разойтись; parity/adversarial tests блокируют это.
- Будущий runtime consumer может начать использовать один из файлов; особенно `language_formulas.json` хранит больше generated examples, чем компактный Markdown. Пока runtime-readers/backlinks отсутствуют, но backlink test и явное изменение allowlist/OpenSpec обязательны до такого перехода.
- Exact list менее автоматически масштабируется, зато предотвращает случайное удаление полезных JSON/scripts.

## Migration Plan

1. Зафиксировать RED для exact exclusion, non-overmatching, reverse-sync preservation, source scan и runtime cleanliness.
2. Ввести exact source-only predicate в canonical и portable contracts.
3. Обновить docs и manifest от `b76026d1...`.
4. Прогнать full source QA и clean-room runtime strict; сравнить file/byte/tree hashes.
5. Получить независимый review, merge/push `main`, проверить remote SHA, переустановить global runtime и архивировать change.

## Open Questions

Нет. Любое расширение allowlist требует отдельного backlink-аудита и OpenSpec change.
