# Привязка применимости нормы к точному паспорту редакции

## Почему

`ksrf-court-request-motion` требует различать event-time, decision-time и переходные правила, но карточка применимости сейчас не оставляет машиночитаемой связи с конкретной ревизией `NormVersionPassport`, временной точкой и единственной редакцией. Поэтому текст может выглядеть убедительно, даже если паспорт заблокирован, ревизия подменена либо временная точка не имеет однозначного соответствия редакции.

## Что меняется

- В обязательном `workflow-reference.md` появляется верхнеуровневый `CourtRequestApplicabilityBinding` с шестью полями: `passport_id`, `passport_revision_id`, `timepoint_id`, `edition_id`, `applicability_status`, `blockers`.
- Статус `verified` разрешён только для точной текущей ревизии паспорта с `gate.status=passed` и единственным совпадением `timepoint_id → edition_id` в `timepoint_edition_map`.
- Сохранённые caller-supplied `gate.status` и `filing_ready` не считаются authority: перед binding выполняется текущая оценка существующим `assess_norm_version_passport(...)` с verifier и approval ledger.
- Любая недоказанная переходная норма, заблокированный паспорт, несовпадение ревизии или неоднозначное соответствие переводят binding в `blocked` и запрещают filing-ready формулу.
- Неизвестная будущая дата, горизонт которой может пересечь границу редакций, не выдумывается и не подменяется датой подачи.
- Уникальная event-time пара не считается доказательством future applicability без отдельной связи с governing horizon или официальным переходным правилом.
- Новый offline contract test отвергает ранние decoy-блоки и вложенный вместо верхнеуровневого контракт.
- Eval получает adversarial сценарий с отсутствующим официальным переходным источником.

## Не входит

- Изменение общей схемы или runtime `NormVersionPassport`.
- Изменение маршрутов статей 84–87, 96–104 ФКЗ о КС РФ, теста исчерпания либо классификации заявителя.
- Автоматическое определение редакции, подмена официального source gate или выпуск готового документа при blocked-статусе.
- Новый runtime/schema/validator: кандидат использует существующую оценку паспорта и закрепляет проверяемый интерфейс скилла.
- Представление binding как runtime authority или автоматического filing approval: объект остаётся методологической статической проекцией.
- Публикация в `main` либо синхронизация `~/.codex/skills` без отдельного exact-byte human approval.

## Затрагиваемые файлы

- `skills/ksrf-court-request-motion/references/workflow-reference.md`
- `skills/ksrf-court-request-motion/tests/test_interface_contract.py`
- `skills/ksrf-court-request-motion/evals/evals.json`
- `skills-manifest.json` (механически пересобранный publish manifest)
