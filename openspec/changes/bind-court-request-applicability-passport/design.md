# Проектирование

## Инвариант

Проза о будущей применимости недостаточна. Для каждого оспариваемого структурного положения должна существовать явная связь с точными `passport_id`, `passport_revision_id`, `timepoint_id` и `edition_id`. `applicability_status=verified` допустим только при неизменённой ревизии паспорта, `gate.status=passed` и ровно одной записи `timepoint_edition_map`, связывающей выбранную временную точку с выбранной редакцией.

## Fail-closed поведение

- Отсутствующее либо несовпадающее значение одного из четырёх идентификаторов возвращает `applicability_status=blocked` и `FIX_FIRST`.
- `gate.status` со значением `blocked` или `ready_for_human_review` не повышается локальным выводом и возвращает `FIX_FIRST` с исходными blockers паспорта.
- Caller-supplied сохранённый gate не используется: без свежего `assess_norm_version_passport(...)` с действующими verifier и approval ledger binding остаётся заблокированным.
- Нулевое, множественное либо противоречивое соответствие `timepoint_id → edition_id` возвращает `FIX_FIRST`.
- Отсутствующий официальный документ для изменяющего акта или переходного положения возвращает `ABSTAIN_PENDING_OFFICIAL_SOURCE` и список недостающих актов.
- Неизвестный future decision horizon, способный пересечь границу редакций, возвращает `ABSTAIN_PENDING_RECORD`; filing-timepoint не используется как суррогат даты решения.
- Статус `verified` требует, чтобы подтверждённый decision horizon целиком находился в интервале выбранной редакции либо официальный transition rule однозначно выбирал эту редакцию для всего возможного горизонта.
- Уникальная event-time пара — необходимое, но недостаточное условие: без доказательства, что эта временная точка юридически управляет future applicability, либо без transition rule для всего horizon она остаётся `blocked`.
- При blocked-статусе нельзя выдавать готовую к подаче формулу предмета или просьбы; разрешены только диагностическая карточка и перечень исправлений.

## Форма контракта

Обязательный reference содержит единственный JSON fence непосредственно под точным заголовком `### Исполнимый контракт CourtRequestApplicabilityBinding`. Корневой объект имеет ключ `CourtRequestApplicabilityBinding`; вложенное появление этого имени не считается контрактом. Шаблон намеренно начинается с `applicability_status=blocked` и `blockers=["FIX_FIRST"]`.

Binding является проверяемой методологической статической проекцией, а не новым runtime validator, legal approval или filing authority.

## TDD и stop rule

1. RED: exact base `7c934ebf0282221c0efe3321d6cec57e6c403841` не содержит section-anchored верхнеуровневого binding с шестью полями.
2. GREEN: канонический блок проходит; ранний decoy, закрытый или незакрытый HTML-комментарий, заголовок внутри внешнего code fence и вложенный binding не принимаются; eval фиксирует официальный source stop, пересчёт gate, неизвестный future horizon и known-horizon event-time trap.
3. REFACTOR: не добавлять runtime validator, новые поля паспорта, relation к complaint/exhaustion или broad route overhaul.

Candidate-этап завершается после focused/full tests, strict skill validation, чистой проверки и независимого review. Разрешена только feature branch; `main` и `~/.codex/skills` остаются неизменными, OpenSpec change — открытым. Полное завершение требует отдельного exact-byte human approval, публикации одобренного commit в `main`, live-SHA проверки, global sync и повторной проверки опубликованных байтов.
