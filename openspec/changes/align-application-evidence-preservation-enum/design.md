## Context

Канонический enum хранится в `skills/ksrf-complaint-cycle/schemas/ksrf_filing/application-evidence.schema.json` и повторён runtime dataclass validation. Reference, который обязаны читать `ksrf-complaint-cycle` и `ksrf-exhaustion-planner`, содержит отличающееся имя одного статуса. Общий validator сейчас проверяет упаковку, ссылки, evals и секреты, но не сопоставляет machine contract с методическим словарём.

## Goals / Non-Goals

**Goals:**

- Сделать JSON Schema единственным проверяемым источником enum для reference.
- Fail closed при пропуске, лишнем значении, alias или изменённом порядке списка.
- Сохранить совместимость валидных существующих records.
- Добавить узкие unit tests без внешних зависимостей и сети.

**Non-Goals:**

- Добавлять новый canonical enum или legacy alias.
- Мигрировать пользовательские данные.
- Менять оценку preservation/exhaustion или полномочия человека.
- Сканировать произвольный исторический текст на любые упоминания enum.

## Decisions

1. **Schema является источником истины.** Validator читает `properties.preservation_exhaustion.enum`; Python source не парсится и не исполняется.
2. **Проверяется только нормативный список reference.** Из секции `### preservation_exhaustion` извлекаются backtick tokens из bullet-строк до следующего heading. Это не запрещает обсуждать aliases в явно историческом/диагностическом контексте вне списка.
3. **Требуется точное упорядоченное равенство.** Missing, extra, duplicate или reordered value создаёт один error `APPLICATION_EVIDENCE_ENUM_DRIFT` с expected/actual evidence.
4. **Проверка scoped к `ksrf-complaint-cycle`.** Синтетические unit-test packages и остальные skills не обязаны содержать schema/reference; полный канонический package обязан.
5. **Исправление не расширяет authority.** Оно только предотвращает генерацию schema-invalid status и не доказывает исчерпание, готовность или human approval.

## Risks / Trade-offs

- **[Schema layout изменится]** → validator выдаст отдельный contract error и потребует осознанно обновить extraction, а не молча пропустит drift.
- **[Reference переформатируют]** → fail-closed ошибка потребует сохранить машиночитаемый список либо обновить checker и tests одним change.
- **[Порядок enum юридически незначим]** → порядок всё равно сохраняется ради детерминированной документации и простого review; runtime semantics не меняются.

## Migration Plan

1. Исправить reference token.
2. Добавить validator и tests.
3. Выполнить focused/root tests, strict skillset/OpenSpec validation и clean-room install.
4. Регенерировать manifest от точного base commit.
5. При достижении threshold опубликовать только feature branch и подтвердить live SHA; stable/global promotion остаётся отдельным человеческим gate.

## Open Questions

Нет блокирующих вопросов.
