---
name: ksrf-complaint-qa
description: Проверить проект жалобы в КС РФ на некомпенсируемые пороги допустимости, доказательную трассировку и устойчивость выбранного портфеля аргументов. Используй перед формальной подачей, чтобы смоделировать отказ, проверить principal/reserve hypotheses и remedy без требования совпасть с известным корпусным паттерном.
---

# Проверка качества жалобы в КС РФ

## Порядок работы

1. Если входом был UID, сначала проверь `UIDCaseDossier`, матрицу ожидаемых стадий и журнал поиска по `../ksrf-complaint-cycle/references/uid-first-case-workflow.md`. Затем собери и сверь `CaseFile` и `AutonomousIntakeRecord`; самостоятельно перепроверь кандидатов нормы, событийную хронологию, предполагаемое право и правовое последствие по полным актам и официальным источникам. Только после этого проверь официальные редакции статей 37, 43, 74, 96 и 97 ФКЗ о КС РФ и зафиксируй дату. Не выдавай `неясно` лишь потому, что пользователь не подготовил юридическую выжимку.
2. До оценки портфеля примени единый `AdmissibilityMatrix`. Юридические hard gates нельзя компенсировать rubric result, качеством текста, полнотой источников или human approval: маршрут и компетенция; точная норма, носитель и редакция; применение и причинная роль; конкретное дело и надлежащий заявитель; нарушение права через применение; исчерпание и годичный срок; продолжающийся эффект; prior-decision/delta check; anti-appeal filter и допустимый remedy. Вынеси source/quote integrity в `EvidenceGate`, а privacy и human approval — в `ReleaseGate`; они обязательны для выпуска, но не смешиваются с юридической допустимостью.
3. Для каждой нормы собери трассировку `норма -> смысл -> судебный locator -> влияние на результат -> вред -> вопрос -> remedy`. Непрошедшие нормы пометь `не готово`; не снимай их молча.
4. Проверь, что `ArgumentPortfolio` содержит principal, при необходимости reserve, adverse findings, falsifier, refusal model, transfer limits и причину human selection.
5. Проведи critic pass отдельно по каждой активной гипотезе:
   - нормативный ли это вопрос;
   - подтверждают ли источники весь тезис;
   - выдерживает ли причинность альтернативное объяснение;
   - сопоставимы ли corpus analogies по механизму и remedy;
   - устраняет ли просительная формула дефект;
   - не противоречат ли principal и reserve общей фактуре.
   Для полного разбора используй `../ksrf-argument-patterns/references/constitutional-argument-architecture.md`; если есть прежняя позиция, отказ или довод об изменившемся контексте, отдельно пройди `references/argument-quality-revision.md`. Не сворачивай его gates в общий score и не выдавай доктринальную дельту за процессуальное основание.
6. Используй `ksrf-argument-patterns` для аналогий и контрпримеров. Отсутствие известного паттерна само по себе не является дефектом проекта; оцени прямую аргументацию, official anchors и transferability risk.
7. Проверь роль международных, сравнительных, научных, статистических, законодательных и состязательных материалов. Они могут поддерживать, ограничивать или порождать гипотезу, но не выдаются за российскую правовую норму. Для доктрины сверь автора и работу с `../ksrf-argument-patterns/references/constitutionalist-authority-corpus.json`: статус `discovery_only` не годится как авторитет, а карточка `method_integrated` должна использоваться вместе с её guardrail и точным locator первичной работы. Если использована иностранная мотивировка, проверь её по `../ksrf-argument-patterns/references/comparative-argument-coding.md`; если использована сравнительная модель соразмерности или legislative review, потребуй `model_conflict` и российский authority status по `../ksrf-rights-argument-builder/references/proportionality-and-lawmaking-workbook.md`.
   Для спорного rules/principles, purpose, уровня абстракции, holding или аналогии проверь параллельные ветви по `../ksrf-argument-patterns/references/legal-reasoning-model-branches.md`. Для foreign transfer требуй заполненную context card из `../ksrf-argument-patterns/references/institutional-discourse-and-comparative-transfer.md`. Если проект использует баланс, идентичность или эволюцию как мета-паттерн, пройди `references/meta-argumentation-qa.md`; отсутствие trigger или доказательств даёт `insufficient_evidence`, а не риторический вывод.
8. Для доводов о доказывании найди нормативный носитель: презумпцию, распределение риска, закрытый перечень, недостижимый стандарт, запрет оценки обстоятельства или устойчивый автоматизм. Классифицируй факты, проверь актуальность законодательной предпосылки и не смешивай специальный доказываемый факт с усмотрением органа. Для burden lifecycle, rival explanations и double counting используй `../ksrf-complaint-facts-demands/references/evidence-inference-and-dependency-audit.md`; граф и ответ Legal AI являются только QA-артефактами.
   Если линия зависит от недостаточности процедуры или утверждаемого исправления дефекта следующей инстанцией, отдельно пройди `references/procedural-adequacy-and-cure.md`: подтверди российскую гарантию, применение нормы, полный маршрут и реальные powers/effect cure. Недоказанный cure или спор только о судебной ошибке даёт `insufficient_evidence -> abstain`.
9. Если оспаривается смысл, сформированный высшим судом, проведи аудит структурной целостности: прежние позиции, системные связи, право/привилегия, усмотрение/факт, общее/специальное правило и процессуальная защита. Удали недоказанные предположения о скрытых мотивах.
10. Смоделируй сильнейший отказ Секретариата и более узкое чтение нормы. Для каждой причины дай: подтверждение, ответ, требуемую правку и признак неустранимости.
11. Проведи `precedent-externality review`: смоделируй общий смысл не только удовлетворения, но и отказа; оцени последствия для заявителя и иных лиц; проверь более узкую формулу.
12. Если сработал триггер `FilingDecisionRecord`, проверь его отдельно от юридического verdict: цели и ожидаемую пользу для заявителя; неблагоприятный окончательный акт и внешний эффект; исполнение; расходы, время, приватность, безопасность и репутацию; альтернативы и сроки; более узкую или отложенную опцию; информированное решение заявителя и одобрение юриста. Символическая, историческая или системная цель не улучшает QA verdict и не компенсирует hard gate.
13. Не ставь `готово`, пока для principal и reserve не указан юридически допустимый результат и проверяемый маршрут его реализации после решения. Для диалогового результата требуй участников, предмет, временную защиту, срок, отчёт, контроль, эскалацию и российское полномочие. При сочетании индивидуального и системного результата проведи single-track red team по `../ksrf-complaint-facts-demands/references/remedy-design-matrix.md`; предполагаемый контроль исполнения не выдавай за полномочие без российского основания.
14. Сравни активные гипотезы по измерениям из `../ksrf-explore-arguments/references/evaluation-and-promotion.md`. Не сворачивай проверку в разрешающий scalar score.
15. После содержательных hard gates проведи отдельный style/trace pass по `../ksrf-argument-patterns/references/brief-trace-and-citation-qa.md`: проверь framing, adverse material, заголовки, цитаты и приложения, но не превращай редакторский проход в legal score, статус готовности или автоматическое переписывание. Затем выдай verdict и section-level rewrite plan. `готово` означает только переход к `ksrf-formal-filing-check` после явного решения человека.
16. Проверь, что при допустимом содержательном проходе заявителю представлены `ConstitutionalIssueOptions`, а `KSRFRouteRecommendation` выдана после admissibility и содержит основание, пользу, риски, альтернативы, сроки и условия пересмотра. Не допускай `GO_TO_KSRF`, пока каждый применимый hard gate не имеет `pass`, и не допускай `NO_GO_KSRF` только из-за недоступного после поиска акта: для этого есть `ABSTAIN_PENDING_RECORD`. При раннем `NO_GO_KSRF / ABSTAIN_PENDING_RECORD` issue options могут отсутствовать.
17. Для каждого утверждения о повторяемом судебном смысле, split, временной или межокружной динамике, системности либо «хаосе» практики потребуй файловый `approved_bounded_findings` из `ksrf-cassation-judicial-meaning`: `run_id`, совпадающие `plan_sha256`/`evidence_sha256`, `maximum_permitted_claim`, закрытые adverse/coverage gates, `validation-report.json` и `human-decision.json`. Если envelope отсутствует, устарел, не одобрен или тезис сильнее разрешённого предела, поставь `blocking empirical overclaim` и понизь формулировку до наблюдаемого корпуса, `hypothesis_under_test` или `insufficient_coverage`; число актов и риторика о неработающем законе этот gate не компенсируют. Проверка опциональна для тезисов, которые вообще не опираются на массовую кассационную практику, и не требует импорта кода соседнего скилла.

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
- `Precedent-externality review`;
- `FilingDecisionRecord review` при срабатывании триггера;
- `KSRFRouteRecommendation review` для каждого дела;
- `Remedy fit`;
- `Dimension comparison`;
- `Fix list и следующий скилл`.

## Ограничения

- Не ставь `готово` при `unknown/fail` по применению, исчерпанию или сроку.
- Не исправляй молча факты, цитаты, портфель или решение человека.
- Не считай число ссылок, pattern match или completeness score мерой юридической готовности.
- Не отклоняй новую линию только потому, что её нет в текущем реестре.
- Не выводи обязанность подать жалобу из символической, исторической, статистической или общественной цели и не используй такую цель для давления на заявителя.

## Справочники

- `../ksrf-complaint-cycle/references/offline-practice-core.md` — автономная refusal-модель и финальный контроль полного цикла.
- `../ksrf-complaint-cycle/references/uid-first-case-workflow.md` — UID-покрытие, единая матрица допустимости, варианты проблемы и go/no-go контракт.
- `../ksrf-complaint-cycle/references/strategic-complaint-design.md` — проверка фактического применения, внешнего эффекта решения и исполнимости результата.
- `../ksrf-complaint-cycle/references/source-authority-and-route.md` — маршрут и источники.
- `references/workflow-reference.md` — подробный checklist и rewrite map.
- `../ksrf-explore-arguments/references/artifact-contracts.md` и `../ksrf-explore-arguments/references/evaluation-and-promotion.md` — portfolio/critic contracts.
- `../ksrf-argument-patterns/references/*` — optional analogies, evidence maps, counterarguments и language checks.
- `../ksrf-argument-patterns/references/comparative-argument-coding.md` — наличие/вес довода и function-first transfer gate для иностранной мотивировки.
- `../ksrf-argument-patterns/references/constitutional-argument-architecture.md` — главный тезис, три уровня, attack ledger, competence/consequences matrices и red flags.
- `references/argument-quality-revision.md` — дельта к прежней позиции, пять quality gates, objections ledger и процедурно скорректированный review.
- `references/meta-argumentation-qa.md` — формально-логический, риторический и pragma-dialectical critic; trigger gates баланса, идентичности и эволюции.
- `references/procedural-adequacy-and-cure.md` — российский anchor/route gate, actual participation, error/cost split и проверяемый cure ledger без импорта сравнительного due-process теста.
- `../ksrf-complaint-facts-demands/references/evidence-inference-and-dependency-audit.md` — burden/presumption lifecycle, rival-explanation и dependency QA с adverse/abstain и запретом выдавать Legal AI за доказательство.
- `../ksrf-argument-patterns/references/legal-reasoning-model-branches.md` — QA competing interpretations, исключений, аналогии и hard-case routing без голосования школ.
- `../ksrf-argument-patterns/references/institutional-discourse-and-comparative-transfer.md` — objections/voice ledger и contextual transfer gate для иностранного материала.
- `../ksrf-rights-argument-builder/references/proportionality-and-lawmaking-workbook.md` — model-conflict, legislative-fact и intensity critic без импорта иностранного теста.
- `../ksrf-complaint-facts-demands/references/remedy-design-matrix.md` — двухконтурный remedy, single-track critic и competence gate.
- `../ksrf-argument-patterns/references/constitutionalist-authority-corpus.json` — аудит статуса автора, работы, маршрута и готовности методики.
- `../ksrf-argument-patterns/references/constitutional-methodology-reference-only-corpus.md` — 84 проверенные revise/comparative карточки как red-team и список границ переноса; не считать их human-approved поведением.
- `../ksrf-complaint-cycle/references/ksrf-defect-taxonomy.md` — vocabulary/anti-patterns.
- `../ksrf-complaint-cycle/references/sko-complaint-methods-2017-2026.md` — downstream simulation, полнота remedy, функции аргумента и сравнительная модель фильтрации дел.
- `../ksrf-cassation-judicial-meaning/SKILL.md` — опциональный файловый источник одобренных ограниченных выводов о кассационной практике и обязательный empirical gate, когда проект делает такой вывод.
