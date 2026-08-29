---
name: ksrf-echr-argumentation
description: Скилл исследует официальную практику ЕСПЧ и превращает её в проверяемые findings для конституционной жалобы или обращения в ЕСПЧ. Он применяется в исследовательском профиле для поиска альтернативной гипотезы, позитивного обязательства, effective remedy, пропорциональности и процессуальных гарантий, сохраняя отдельный российский нормативный якорь и пределы переноса.
---

# КСРФ — ЕСПЧ: адаптивный исследовательский слой

## Capability boundary

Этот skill относится к `research` профилю из `../ksrf-complaint-cycle/references/setup-profiles-and-capabilities.md`. Его отсутствие не блокирует basic KSRF analysis. Local HUDOC/embedding — discovery; filing claim требует официальный HUDOC anchor, application number/date, precise holding/paragraphs, transfer limit и отдельный российский официальный конституционный anchor.

## Назначение

Практика ЕСПЧ может породить, поддержать, ослабить или ограничить гипотезу, но не подменяет самостоятельный российский конституционный вопрос. Не требуй, чтобы материал обслуживал уже выбранный тест: сначала выясни, меняет ли он саму постановку механизма, обязанности или remedy.

## Источники

Сначала прочитай `../ksrf-complaint-cycle/references/offline-practice-core.md` как автономный российский baseline. Затем прочитай `references/official-sources.md`. Если доступен локальный проверенный корпус HUDOC, перед его использованием прочитай `references/local-hudoc-corpus.md`: TXT/JSONL ускоряют исследование, но не меняют статус официального акта и не отменяют проверку источника. Для поиска по локальной SQLite/FTS5-проекции дополнительно прочитай `references/local-hudoc-knowledge-base.md`: это discovery-интерфейс с точными локаторами и `promotion_eligible=false`, а не источник готовых правил. Для проверки поведения на реальных source-backed примерах используй `references/verified-hudoc-pilot-fixture.md`; это regression fixture, а не самостоятельный источник права или готовый аргумент. Для route-indexed сравнительных вопросов и transfer limits можно открыть `../ksrf-argument-patterns/references/constitutional-methodology-reference-only-corpus.md`; его карточки не заменяют HUDOC или российский официальный якорь. Для позитивной обязанности, indirect horizontal effect, Article 14 ambit и границы `scope -> interference -> justification` открой `../ksrf-rights-argument-builder/references/equality-positive-obligations-and-right-boundaries.md`; его MF-14–18 являются только `idea_only` research/QA cards. Используй HUDOC, ECHR-KS и официальные ресурсы Совета Европы как первичные источники; проверяй актуальность в момент работы. Различай решения Суда, admissibility decisions, communicated cases, позиции сторон, summaries и materials of a specific case.

Если включён локальный hybrid FTS+dense индекс, используй его только через version-checked resolver из `references/local-hudoc-knowledge-base.md`. Dense similarity и RRF расширяют discovery, но не доказывают позицию Суда и не сокращают lifecycle проверки.

## Рабочий процесс

0. Если переданы материалы российского дела, сначала собери `CaseFile` и `AutonomousIntakeRecord` по `../ksrf-complaint-cycle/references/ksrf-tool-layer.md`. Сам выведи кандидатов нормы, применения, вреда и права и проверь российскую норму по официальному источнику; не требуй от пользователя готового российского профиля.
1. Зафиксируй отдельно:
   - российский профиль: норма, судебное применение, вред и возможный remedy;
   - конвенционный профиль: факты, статья, victim status, исчерпание, срок, допустимость и сатисфакция.
2. Выбери исследовательскую функцию: candidate theory, supporting standard, counterexample, minimum guarantee, positive obligation, effective remedy, execution, balance или procedural safeguard. Для positive obligation раздельно заполни `trigger`, `scope`, `content` и `breach`; для scope-вопроса не смешивай применимость, вмешательство и оправдание. При несовместимых моделях верни `model_conflict`, не синтетический тест.
3. Построй многоязычную матрицу поиска по понятиям, фактам, государствам, периоду и типу документа. Начни с актуального guide/key cases, затем проверь первоисточники и admissibility boundary cases.
4. Для каждого акта создай `ResearchFinding` по `../ksrf-explore-arguments/references/artifact-contracts.md`: официальный anchor, paragraphs, thesis, relation к гипотезам, factual/legal differences, verification status и transfer limit. На уровне точного предложения обязательно и раздельно зафиксируй `source_actor`, `source_function`, `source_form` и `court_treatment`: для submission `source_form=reproduced_in_public_act`, а `court_treatment` имеет фактическое значение `accepted|rejected|qualified|not_addressed|unclear`; для majority reasoning `source_form=public_act` и `court_treatment=not_applicable`. Роль всего параграфа не доказывает, кто произнёс смешанную фразу. Довод заявителя является приёмом стороны, но не позицией Суда, пока majority reasoning прямо его не принимает.
5. Не приписывай Суду аргументы стороны. Не выдавай legal summary за мотивировку и communicated case за итоговое решение.
6. Не повышай `candidate` напрямую до инструкции skill. Последовательность обязательна: `candidate -> verified_case_finding -> cross_case_reusable -> skill_update_approved`. Единичный акт может остаться только `case_example_only` и не проходит в `cross_case_reusable`; два findings по разным приёмам также не образуют один reusable pattern.
7. Проведи двойное отображение:
   - в KSRF portfolio: какой российский механизм или вопрос материал открывает/проверяет и чего не доказывает;
   - в ECHR route: как он работает для применимости, допустимости, существа и remedy.
   Для KSRF заполни fail-closed `KSRFTransferPacket`: `challenged_norm_or_judicial_meaning`, `domestic_application`, `constitutional_rights_and_official_anchors`, `defect_mechanism`, `individual_harm`, `test_family_and_steps`, отдельные `less_restrictive_alternative`/`procedural_safeguards`/`positive_obligation_or_remedy`, `russian_normative_anchors`, `fourth_instance_boundary`, `adverse_and_distinguishing` и отдельный воспроизводимый `adverse_search`. Для positive obligation разделяй `trigger/scope/content/breach`; при конфликте моделей возвращай `model_conflict`. Неизвестное пометь `unknown`, а не достраивай.
7.1. Повторяемый приём заявителя веди отдельно как `applicant_pleading_move`: минимум два независимых дела, public-act reproduction с exact locator, фактический reproduction mode и реакция Суда, а также documented adverse/currentness/temporal/transfer review. Узкое исключение из Russian-anchor gate действует только при одновременных `authority_status=non_authority`, `reuse_target=research_checklist_only` и `substantive_rule_changed=false`, после отдельной ручной проверки. При отсутствии любого из трёх значений российский официальный якорь снова обязателен; такой приём не может создавать или менять материально-правовое правило скилла.
8. Ищи adverse cases и различия фактов. Если материал меняет principal/reserve selection, верни finding в `ksrf-explore-arguments`; если лишь иллюстрирует уже доказанный тезис, не перегружай жалобу.
9. Перед выдачей проверь ссылки по официальному тексту, а процессуальные требования — по актуальным Rules of Court, Practice Directions и Admissibility Guide.

## Результат

Для каждого finding верни:

- `Исследовательская функция`;
- `Официальный акт, статус и paragraphs`;
- обязательные `source_actor`, `source_function`, `source_form` и `court_treatment` для точного предложения, отдельно от paragraph-level role;
- `Проверяемый тезис источника`, сформулированный не шире подтверждённой позиции указанного actor;
- `Relation to KSRF hypothesis`;
- `KSRFTransferPacket`: норма/судебный смысл -> механизм дефекта -> конституционное право и вред -> тест/альтернатива/гарантии/remedy -> граница четвёртой инстанции;
- `Российский нормативный якорь, который всё ещё нужен`;
- `Различия и предел переноса`;
- `Adverse authority`;
- `Влияние на portfolio/remedy`.

## Особые правила

- Для дел против России отдельно проверяй временную юрисдикцию и актуальный правовой эффект.
- Недоступность Telegram, юридических медиа или локального project corpus не блокирует исследование: методика и российские guardrails находятся во встроенном автономном ядре.
- Не обещай массовый доступ к закрытым case files и не собирай лишние персональные данные.
- Не превращай отсутствие дела ЕСПЧ в отрицательный вывод о российской гипотезе.
- Case-scoped materials не переносятся в другое дело без sanitization и approval.
