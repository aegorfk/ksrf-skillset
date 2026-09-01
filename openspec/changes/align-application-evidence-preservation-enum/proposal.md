## Why

`implicit-application-gate.md` публикует значение `raised_not_addressed`, которого нет в каноническом `ApplicationEvidenceRecord`: JSON Schema и runtime принимают только `raised_but_not_addressed`. Такой reference способен породить невалидный filing-significant record, а текущий skillset validator рассинхронизацию не обнаруживает.

## What Changes

- Заменить неканоническое значение в reference на точный enum из `application-evidence.schema.json`.
- Добавить fail-closed проверку равенства списка `preservation_exhaustion` в reference и канонического schema enum.
- Добавить регрессионные тесты для совпадающего и рассинхронизированного контрактов.
- Не менять сам JSON Schema, runtime enum, юридические gates или значения существующих records.

## Capabilities

### New Capabilities

- `ksrf-application-evidence-contract`: единый канонический словарь `preservation_exhaustion` между schema, runtime-facing reference и release validation.

### Modified Capabilities

Нет.

## Impact

- `skills/ksrf-complaint-cycle/references/implicit-application-gate.md`: исправление одного enum token.
- `skills/ksrf-complaint-cycle/scripts/validate_ksrf_skillset.py`: новый cross-contract validator.
- `skills/ksrf-complaint-cycle/tests/test_validate_ksrf_skillset.py`: deterministic regression tests.
- `skills-manifest.json`: регенерация после финальных правок.
- Global skills и `main` не изменяются без отдельного promotion/release шага.
