---
name: ksrf-complaint-qa
description: Проверить проект жалобы в КС РФ на некомпенсируемые пороги допустимости, доказательную трассировку и устойчивость выбранного портфеля аргументов. Используй перед формальной подачей, чтобы смоделировать отказ, проверить principal/reserve hypotheses и remedy без требования совпасть с известным корпусным паттерном.
---

# Проверка качества жалобы в КС РФ

## Порядок работы

1. Собери и сверь `CaseFile`; проверь официальные редакции статей 37, 43, 74, 96 и 97 ФКЗ о КС РФ и зафиксируй дату.
2. Примени hard gates, которые нельзя компенсировать rubric result:
   - точная норма и редакция;
   - судебное применение, а не упоминание;
   - конкретное дело и надлежащий заявитель;
   - исчерпание и годичный срок;
   - source/quote integrity;
   - human approval портфеля.
3. Для каждой нормы собери трассировку `норма -> смысл -> судебный locator -> влияние на результат -> вред -> вопрос -> remedy`. Непрошедшие нормы пометь `не готово`; не снимай их молча.
4. Проверь, что `ArgumentPortfolio` содержит principal, при необходимости reserve, adverse findings, falsifier, refusal model, transfer limits и причину human selection.
5. Проведи critic pass отдельно по каждой активной гипотезе:
   - нормативный ли это вопрос;
   - подтверждают ли источники весь тезис;
   - выдерживает ли причинность альтернативное объяснение;
   - сопоставимы ли corpus analogies по механизму и remedy;
   - устраняет ли просительная формула дефект;
   - не противоречат ли principal и reserve общей фактуре.
6. Используй `ksrf-argument-patterns` для аналогий и контрпримеров. Отсутствие известного паттерна само по себе не является дефектом проекта; оцени прямую аргументацию, official anchors и transferability risk.
7. Проверь роль международных, сравнительных, научных, статистических, законодательных и состязательных материалов. Они могут поддерживать, ограничивать или порождать гипотезу, но не выдаются за российскую правовую норму. Для доктрины сверь автора и работу с `../ksrf-argument-patterns/references/constitutionalist-authority-corpus.json`: статус `discovery_only` не годится как авторитет, а карточка `method_integrated` должна использоваться вместе с её guardrail и точным locator первичной работы.
8. Для доводов о доказывании найди нормативный носитель: презумпцию, распределение риска, закрытый перечень, недостижимый стандарт, запрет оценки обстоятельства или устойчивый автоматизм.
9. Смоделируй сильнейший отказ Секретариата и более узкое чтение нормы. Для каждой причины дай: подтверждение, ответ, требуемую правку и признак неустранимости.
10. Сравни активные гипотезы по измерениям из `../ksrf-explore-arguments/references/evaluation-and-promotion.md`. Не сворачивай проверку в разрешающий scalar score.
11. Выдай verdict и section-level rewrite plan. `готово` означает только переход к `ksrf-formal-filing-check` после явного решения человека.

## Вердикты

- `готово`: hard gates пройдены, портфель утверждён, существенные claims проверены, остаются малые правки.
- `есть замечания`: линия жизнеспособна, но нужны точечные материалы или переписывание.
- `существенные проблемы`: hard gate, причинность, source integrity или remedy не пройдены.
- `переписать заново`: проект в основном просит переоценить дело, не устанавливает норму/применение либо не имеет согласованного портфеля.

## Вывод

- `Вердикт`;
- `Hard gates`;
- `Матрица нормы и применения`;
- `Portfolio review` по principal/reserve;
- `Adverse findings и контрпримеры`;
- `Обычная апелляционная логика`;
- `Source/quote traceability`;
- `Refusal model`;
- `Remedy fit`;
- `Dimension comparison`;
- `Fix list и следующий скилл`.

## Ограничения

- Не ставь `готово` при `unknown/fail` по применению, исчерпанию или сроку.
- Не исправляй молча факты, цитаты, портфель или решение человека.
- Не считай число ссылок, pattern match или completeness score мерой юридической готовности.
- Не отклоняй новую линию только потому, что её нет в текущем реестре.

## Справочники

- `../ksrf-complaint-cycle/references/offline-practice-core.md` — автономная refusal-модель и финальный контроль полного цикла.
- `../ksrf-complaint-cycle/references/source-authority-and-route.md` — маршрут и источники.
- `references/workflow-reference.md` — подробный checklist и rewrite map.
- `../ksrf-explore-arguments/references/artifact-contracts.md` и `evaluation-and-promotion.md` — portfolio/critic contracts.
- `../ksrf-argument-patterns/references/*` — optional analogies, evidence maps, counterarguments и language checks.
- `../ksrf-argument-patterns/references/constitutionalist-authority-corpus.json` — аудит статуса автора, работы, маршрута и готовности методики.
- `../ksrf-complaint-cycle/references/ksrf-defect-taxonomy.md` — vocabulary/anti-patterns.
