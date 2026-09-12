# Прецедент, аналогия и юридическое оправдание: comparative QA workbook

## Содержание

- [Hard gates](#hard-gates)
- [1. Toulmin и внешнее оправдание](#1-toulmin-и-внешнее-оправдание)
- [2. Четыре типа обоснования](#2-четыре-типа-обоснования)
- [3. Precedent questionnaire](#3-precedent-questionnaire)
- [4. Две конфликтующие ветви аналогии](#4-две-конфликтующие-ветви-аналогии)
- [5. Defeasible argument graph](#5-defeasible-argument-graph)
- [6. Где формализация останавливается](#6-где-формализация-останавливается)
- [7. Data/eval sidecars, а не новые правовые правила](#7-dataeval-sidecars-а-не-новые-правовые-правила)
- [Выход](#выход)
- [Граница runtime](#граница-runtime)


Используй этот справочник для реконструкции судебного довода, нескольких возможных readings позиции и defeasible argument graph. Это научная методика. Common-law категории не устанавливают силу российских актов, а формальная логика не доказывает полноту права или фактов.

## Hard gates

1. Сначала российский статус акта, норма/редакция, полный текст и точный locator; затем теория precedent.
2. Держи separately internal validity и external justification: логически корректный вывод может опираться на ложную, устаревшую или неприменимую посылку.
3. Аналогия создаёт candidate, а не authority. Relevance должна иметь проверяемое правовое основание.
4. Rule-only и analogy-as-reason образуют конфликтующие модели самостоятельной роли аналогии; они не голосуют. Материальное расхождение даёт `model_conflict -> abstain`.
5. Sceptically justified и credulously defensible — разные статусы. Не превращай защищаемую ветвь в установленный вывод.
6. Style, persuasion и formal validity не компенсируют применение, admissibility, provenance или remedy.

## 1. Toulmin и внешнее оправдание

Для каждого существенного тезиса заполни:

claim → grounds → warrant → backing → qualifier → rebuttal.

Затем спроси:

- установлен ли каждый fact ground;
- является ли warrant нормой, интерпретацией, аналогией или policy premise;
- какой authority и locator подтверждает warrant;
- ограничивает ли qualifier вывод;
- отвечает ли аргумент на strongest rebuttal;
- не скрыта ли нормотворческая посылка как «очевидная».

Для hard case отдельно проверь consequences, consistency и coherence. Эти поля не складываются в общий score.

## 2. Четыре типа обоснования

Разведи:

- linguistic;
- systemic;
- precedent/analogy;
- teleological-evaluative.

Каждый тип получает собственный source, scope, counterargument и competence limit. Тип не определяет вес автоматически.

Universalization pass: сформулируй правило, которое решение предполагает для materially similar cases; затем проверь boundary и undesirable cases. Если широкая формула ломается, сузь правило с объяснением, а не скрывай контрпример.

### 2A. Interpretive argument record

**Input → transform → output:** возьми exact proposition, полный контекст, speaker, применимую редакцию нормы и locators всех материалов → реконструируй каждый переход отдельно и не смешивай тип аргумента с видом материала или его authority → `InterpretiveArgumentRecord`:

| Поле | Значение |
| --- | --- |
| `argument_type` | `linguistic`, `systemic`, `teleological_evaluative`, `intentional_transcategorical`, `mixed`, `unclassified` |
| `material_type` | `enacted_text`, `related_norm`, `official_history`, `judicial_act`, `doctrine`, `social_or_empirical_fact`, `party_submission`, `unknown` |
| `second_order_priority` | `none`, `claimed`, `officially_anchored`, `conflicted`; отдельно `priority_rule`, source и locator |
| `institutional_context` | суд/орган, иерархия, стадия, полномочие, способ отбора дела, форма решения и отношение к проверяемому акту |
| `trace` | premises → warrant → conclusion, qualifier, counterargument, редакция и time scope |

`argument_type` описывает функцию довода, а `material_type` — то, на чём он построен; ни одно поле само по себе не задаёт вес. Аргумент из намерения хранится `intentional_transcategorical`, когда он пересекает linguistic/systemic/purpose categories; при смешанной или неясной реконструкции не форсируй категорию.

**Adverse/refute pass:** найди довод того же типа в пользу противоположного чтения; проверь допустимость, официальный статус и полноту материала; отдели формулу стороны от мотивировки суда; попытайся опровергнуть заявленную priority более специальной, поздней или иерархически старшей официальной нормой. Историческая сравнительная частота не является priority rule.

`abstain_interpretive_record`: полный контекст, speaker, редакция либо российская collision rule не установлены; одна посылка допускает две несовместимые реконструкции; institutional context меняет возможный эффект. Такие записи остаются discovery/critic и требуют ручного выбора юриста.

## 3. Precedent questionnaire

Перед извлечением позиции зафиксируй:

- суд, иерархию, состав и окончательность;
- способ отбора дела и publication completeness;
- существенные факты и issue;
- exact proposition и speaker;
- holding/ratio candidate, reasons, principle и dicta;
- formal bindingness, defeasible/outweighable force, further support или illustrative value;
- одиночный акт, line of cases, conflicting line и synthesized line;
- later treatment: follow, distinguish, narrow, expand, explicit/silent overrule;
- изменение нормы и иные later-law события.

Binary binding/non-binding недостаточно. Российская authority role определяется российскими источниками, а поля ratio/dicta служат только QA.

## 4. Две конфликтующие ветви аналогии

### Analogy-as-reason

Сравни source/target cases, competing source cases и классификации; меняй по одному факту через hypotheticals; обоснуй relevance отраслевым правовым знанием; покажи competing analogy.

### Rule-only red team

Потребуй явную authoritative rule, empirical premise либо normative/moral premise, которая делает общий признак релевантным. Спроси, не маскирует ли аналогия свободное rule creation.

Выходы ветвей хранятся отдельно. Если они приводят к разной границе права, исключению или remedy, нужен human_resolution_required.

## 5. Defeasible argument graph

Храни раздельно:

- facts и sources;
- rules;
- exceptions;
- arguments;
- rebutting/undermining/undercutting attacks;
- conflict/defeat relation;
- priority source;
- procedural admissibility/preservation;
- strategic omission or concession только при источнике.

Priority нельзя придумывать из удобства. Для российского вывода она требует действующего collision rule или иной официальной опоры.

### Тип атаки и её адресат

**Input → transform → output:** для каждого adverse довода зафиксируй точную proposition, target node, source/locator, speaker, стадию и authority → спроси, отрицает ли он вывод, разрывает ли переход или лишь задаёт правило предпочтения → `AttackRecord` с `attack_type`, `target_node`, `attacking_node`, `effect`, `priority_source` и `resolution_status`.

- `rebut`: поддерживает несовместимый вывод или исключение к выводу;
- `undermine`: атакует существование, истинность, допустимость или актуальность premise;
- `undercut`: принимает premise для целей анализа, но атакует warrant или связь premise → conclusion, не доказывая противоположный итог;
- `preference`: обосновывает относительный приоритет двух иначе защищаемых ветвей только через проверенную официальную collision/priority rule.

**Adverse/refute pass:** попробуй переклассифицировать `rebut` как более узкий `undermine` или `undercut`; проверь, действительно ли `preference` имеет официальный источник и применима к этой редакции, стадии и органу; ищи ответную атаку и независимую ветвь, переживающую исходную атаку. Не своди число доводов или ссылок к весу.

Для пары прецедентов выполни `dominance_check`: если новая мера одновременно не эффективнее для той же цели и более обременительна для того же права, противоположный результат требует явного различающего признака или изменения применимого правила. Направления обоих сравнений подтверждаются отдельно; dominance не вычисляется из придуманных весов и не заменяет российскую authority role.

`abstain_attack`: target не определён, источник передан пересказом, priority лишь доктринальная/иностранная либо rebut, undermine и undercut ведут к разным правовым последствиям. До ручной верификации граф может показывать конфликт, но не объявлять победившую ветвь.

Статусы:

- sceptically_justified: вывод выдерживает все допустимые ветви;
- credulously_defensible: существует минимум одна защищаемая ветвь;
- conflict_unresolved;
- premise_missing;
- source_or_procedure_blocked.

## 6. Где формализация останавливается

Формальная модель эксплицирует скрытые переходы и конфликты, но не решает автоматически:

- полноту набора норм и исключений;
- истинность фактов;
- юридическую классификацию open-textured term;
- authority и компетенцию;
- процессуальную допустимость;
- выбор между несколькими разумными правилами.

При этих пробелах ответ — abstain или human review.

## 7. Data/eval sidecars, а не новые правовые правила

### Response-chain corpus

Для тезиса «существенный довод был сохранён и рассмотрен» связывай первую, апелляционную и кассационную инстанции. Поля: довод, документ и стадия заявления, ответ explicit/implicit/not addressed/immaterial, locator, связь с исходом, основание отмены. Без процессуального документа статус preservation остаётся unknown.

### Precedent-force drift

От seed-позиции КС РФ/ВС РФ строй citation graph всех доступных последующих актов. Извлекай добавленные/опущенные условия, follow/distinguish/narrow/expand, редакцию нормы и adverse distinctions. Это eval для authority ledger, не доказательство силы через число ссылок.

### Analogy pairset

Нужны source act, target act, shared/different facts, relevance rule, competing analogy, speaker, outcome и later treatment. Embedding similarity — discovery only. Held-out набор обязан включать supporting, boundary и adverse pairs.

### Rule/exception provenance

Храни base rule, explicit/implicit exception, authority for priority, trigger facts, competing arguments, version и time scope. Исключение, выведенное только из результата, остаётся candidate.

### Four-layer trace

Разделяй logical support, dialectical defeat, procedural preservation и strategic choice. Стратегический мотив стороны нельзя домысливать при отсутствии документа.

Все corpus-планы используют EvidenceAcquisitionPlan из ksrf-practice-authority-builder и заканчиваются insufficient_coverage при неизвестной полноте.

## Выход

- ToulminJustificationCard;
- InternalExternalJustificationTrace;
- InterpretationTypeMatrix;
- InterpretiveArgumentRecord[];
- UniversalizationBoundarySet;
- PrecedentQuestionnaireRecord;
- ParallelAnalogyBranches;
- DefeasibleArgumentGraph;
- AttackRecord[];
- model_conflict, missing_premise, source_gap и procedural_gap.

## Граница runtime

Workbook самодостаточен; история разработки и academic provenance хранятся вне пользовательской установки. Ни одна сравнительная модель не делает российский акт binding, не доказывает состав фактов и не разрешает конфликт ветвей без юриста.
