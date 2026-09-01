## Context

Canonical source содержит 15 `evals/evals.json` и 15 `evals/trigger-evals.json`. Они нужны для source QA, но обычный skill runtime их не импортирует. Текущий portable validator всегда вызывает `_validate_behavioral_evals()` и `_validate_trigger_evals()`, поэтому runtime payload без evals детерминированно красный.

## Goals / Non-Goals

**Goals:**

- Убрать eval suites из пользовательской установки.
- Не ослабить source/release validation.
- Сделать ограниченность runtime validation machine-readable и видимой человеку.
- Сохранить exact reverse-sync и public-source safety.

**Non-Goals:**

- Удалять evals из Git или перестать запускать их перед публикацией.
- Делать runtime PASS достаточным для release/promotion.
- Исключать runtime references, schemas, scripts, agents или libraries.
- Менять юридические выводы, источники или human-review gates.

## Decisions

1. **Два явных профиля.** `source` требует evals и остаётся default/API/release профилем. `runtime` пропускает только две eval-specific проверки.
2. **Честный отчёт.** Report содержит `validation_profile`, `source_release_eligible`, `validation_coverage.evals`, `validation_coverage.public_source_safety` и `validation_coverage.public_repository_safety` со значением `validated` либо `not_checked`; text output показывает профиль и предупреждает, что runtime-проверка не заменяет source QA. Source release eligibility требует доступного канонического public-source contract, его успешного прогона по source-only assets и repository-wide public-source scan именно в каноническом source checkout. Runtime report не экспортирует `publish_manifest`, а CLI отклоняет сочетание `--profile runtime --manifest-out`.
3. **Один distribution contract.** Exact path components `tests` и `evals` считаются development-only в canonical и portable manifest builders.
4. **Source preservation.** Reverse sync сохраняет оба development tree exact до атомарной замены runtime.
5. **Source safety отдельно от distribution.** Repository public-source guard перечисляет development paths через `include_development=True`; исключение из установки не скрывает их от проверки.
6. **Fail closed для неизвестного профиля.** Python API отклоняет неизвестный profile; CLI ограничивает choices.
7. **Runtime не является shortcut для source checkout.** Runtime profile требует полного отсутствия source-only `tests/` и `evals/`; найденный development artifact даёт `SOURCE_ONLY_ARTIFACT_PRESENT`.
8. **Partial source check не release evidence.** `source_release_eligible=true` возможно только для успешной проверки exact canonical allowlist всех 15 packages.
9. **Runtime-гайды не требуют отсутствующих eval assets.** Пользовательская инструкция по retrieval описывает ручную проверку и stop rules; автоматический benchmark остаётся отдельным maintainer source/release QA только при наличии реального versioned harness.

## Risks / Trade-offs

- Пользователь должен запускать установленный валидатор с `--profile runtime`; без флага безопасный default `source` сообщит об отсутствующих evals.
- Maintainer может ошибочно принять runtime PASS за release QA; явные report fields и text disclaimer делают это наблюдаемой ошибкой.
- Maintainer может запустить runtime profile на source checkout; обязательная проверка отсутствия development artifacts блокирует такой обход.
- Reverse sync может удалить evals после их исключения; regression обязан доказать сохранение path+digest.
- Portable и canonical exclusion rules дублируются из-за автономности установленного validator; тест сравнивает их observable manifests.

## Migration Plan

1. Добавить RED для отсутствующих evals в runtime profile при неизменной ошибке source profile.
2. Добавить RED, что installer/portable manifest исключают evals, а reverse sync их сохраняет.
3. Реализовать минимальные profiles и development-only boundary.
4. Выполнить source strict QA и clean-room runtime strict QA.
5. Провести независимый review, опубликовать в `main`, установить exact global payload и проверить hashes.

## Open Questions

Нет блокирующих вопросов.
