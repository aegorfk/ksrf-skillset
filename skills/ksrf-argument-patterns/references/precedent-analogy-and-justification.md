# Прецедент, аналогия и юридическое оправдание: comparative QA workbook

Используй этот справочник для реконструкции судебного довода, нескольких возможных readings позиции и defeasible argument graph. Это научная методика. Common-law категории не устанавливают силу российских актов, а формальная логика не доказывает полноту права или фактов.

## Hard gates

1. Сначала российский статус акта, норма/редакция, полный текст и точный locator; затем теория precedent.
2. Держи separately internal validity и external justification: логически корректный вывод может опираться на ложную, устаревшую или неприменимую посылку.
3. Аналогия создаёт candidate, а не authority. Relevance должна иметь проверяемое правовое основание.
4. Александр/Шервин и Weinreb образуют конфликтующие модели самостоятельной роли аналогии; они не голосуют. Материальное расхождение даёт model_conflict → abstain.
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
- rebutting/undercutting attacks;
- conflict/defeat relation;
- priority source;
- procedural admissibility/preservation;
- strategic omission or concession только при источнике.

Priority нельзя придумывать из удобства. Для российского вывода она требует действующего collision rule или иной официальной опоры.

### Тип атаки и её адресат

**Input → transform → output:** для каждого adverse довода зафиксируй точную proposition, target node, source/locator, speaker, стадию и authority → спроси, отрицает ли он вывод, разрывает ли переход или лишь задаёт правило предпочтения → `AttackRecord` с `attack_type`, `target_node`, `attacking_node`, `effect`, `priority_source` и `resolution_status`.

- `rebut`: поддерживает несовместимый вывод или исключение к выводу;
- `undercut`: атакует warrant, достоверность, применимость либо связь premise → conclusion, не доказывая противоположный итог;
- `preference`: обосновывает относительный приоритет двух иначе защищаемых ветвей только через проверенную официальную collision/priority rule.

**Adverse/refute pass:** попробуй переклассифицировать `rebut` как более узкий `undercut`; проверь, действительно ли `preference` имеет официальный источник и применима к этой редакции, стадии и органу; ищи ответную атаку и независимую ветвь, переживающую исходную атаку. Не своди число доводов или ссылок к весу.

`abstain_attack`: target не определён, источник передан пересказом, priority лишь доктринальная/иностранная либо rebut и undercut ведут к разным правовым последствиям. До ручной верификации граф может показывать конфликт, но не объявлять победившую ветвь.

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

## Источники и locators

- Eveline T. Feteris, *Fundamentals of Legal Argumentation*, 2nd ed., Springer, 2017: clear/hard cases и defeasibility, печ. с. 1–19 / PDF 18–36; conflict representation, с. 33–40 / PDF 50–57; Toulmin, с. 49–59 / PDF 66–76; argument schemes и critical questions, с. 225–249 / PDF 242–266. Первое издание: Kluwer, 1999, Toulmin с. 40–46 / PDF 50–56, MacCormick с. 73–88 / PDF 83–98, Alexy с. 102–114 / PDF 112–124; оно используется только для historical delta.
- Neil MacCormick, *Rhetoric and the Rule of Law*, OUP, 2005: persuasion и rational justification, печ. с. 17–24 / PDF 32–39; universalization, с. 78–93, 147–151 / PDF 93–108, 162–166; interpretation matrix, с. 124–139 / PDF 139–154; ratio reconstruction, с. 143–161 / PDF 158–176; coherence, consequences и defeasibility, с. 190–204, 239–253 / PDF 205–219, 254–268.
- Neil Duxbury, *The Nature and Authority of Precedent*, CUP, 2008: precedent/analogy/example, печ. с. 1–11 / PDF 14–24; defeasible precedent, с. 58–108 / PDF 71–121; competing ratio, с. 67–90 / PDF 80–103; distinguishing/overruling, с. 111–149 / PDF 124–162.
- D. Neil MacCormick, Robert S. Summers (eds.), *Interpreting Precedents*, Ashgate 1997, Routledge reissue 2016: empirical questionnaire, печ. с. 551–561 / PDF 564–574; institutional metadata, с. 437–460 / PDF 450–473; degrees of force, с. 461–480 / PDF 474–493; facts/ratio/reasons/lines, с. 503–518 / PDF 516–531; departure, с. 519–530 / PDF 532–543. Reissue 2016 не является вторым изданием; country reports отражают главным образом 1996–1997 годы.
- Larry Alexander, Emily Sherwin, *Demystifying Legal Reasoning*, CUP, 2008: empirical/moral reasoning и authoritative deduction, печ. с. 31–63 / PDF 37–69; rule-only critic аналогии, с. 64–103 / PDF 70–109; application/lawmaking distinction, с. 104–130 / PDF 110–136; interpretation/construction, с. 131–219 / PDF 137–225.
- Lloyd L. Weinreb, *Legal Reason: The Use of Analogy in Legal Argument*, CUP, 2005: paired cases, печ. с. 41–64 / PDF 51–74; gap нормы и факта, с. 80–92 / PDF 90–102; relevance, с. 130–133 / PDF 140–143; one-fact hypotheticals, с. 142–144 / PDF 152–154; residual uncertainty, с. 149–152 / PDF 159–162.
- Henry Prakken, *Logical Tools for Modelling Legal Argument*, Kluwer, 1997: предел формализации, печ. с. 15–31 / PDF 26–42; rules/exceptions/open texture, с. 33–60 / PDF 44–71; argument/defeat graph, с. 141–177 / PDF 152–188; sceptical/credulous outcomes, с. 179–200 / PDF 190–211; priority и четыре слоя, с. 203–218, 249–274 / PDF 214–229, 260–285.
- Richard Bellamy, Jeff King (eds.), *The Cambridge Handbook of Constitutional Theory*, CUP, 2025: concept/conceptions и thin/thick models, печ. с. 7–10 / PDF 30–33; value → modality → institution trace, с. 9–10 / PDF 32–33; rule/principle и legal/nonlegal axes, с. 10–13 / PDF 33–36; competing chapters on review/interpretation/proportionality/courts, с. 343–396, 848–866 / PDF 366–419, 871–889.
- D. Neil MacCormick, Robert S. Summers (eds.), *Interpreting Statutes: A Comparative Study*, Dartmouth, 1991: introduction, печ. с. 1–8 / PDF 19–26; method and rational reconstruction, с. 9–28 / PDF 27–46; comparative analysis, с. 461–510 / PDF 479–528; interpretation and justification, с. 511–544 / PDF 529–562; comparative questionnaire, с. 545–551 / PDF 563–569. Материал отражает системы и практику на историческом срезе до 1991 года; реконструируется публичное обоснование, а не скрытый мотив судьи.
- Douglas Walton, Fabrizio Macagno, Giovanni Sartor, *Statutory Interpretation: Pragmatics and Argumentation*, Cambridge University Press, 2021: understanding/interpretation/construction, печ. с. 27–34 / PDF 43–50; problem-solving framework, с. 55–92 / PDF 71–108; ambiguity, с. 97–149 / PDF 113–165; maxims and presumptions, с. 157–197 / PDF 173–213; argumentation schemes, с. 205–271 / PDF 221–287; classification, attacks and formalization, с. 280–327 / PDF 296–343.
- Neil MacCormick, *Legal Reasoning and Legal Theory*, Clarendon Press, 1978; Oxford University Press reprint, 2003: deductive justification, печ. с. 19–52 / PDF 43–76; presuppositions, с. 53–72 / PDF 77–96; formal justice, с. 73–99 / PDF 97–123; second-order justification, с. 100–128 / PDF 124–152; consequences, с. 129–151 / PDF 153–175; coherence, principle, analogy and interpretation, с. 152–228 / PDF 176–252. Это исторический фундаментальный слой; предисловие 2003 года уточняет и пересматривает часть формулировок, а более поздняя *Rhetoric and the Rule of Law* остаётся основным рабочим развитием.

Все источники подтверждают только метод. Они не делают российский акт binding, не доказывают состав фактов и не разрешают конфликт ветвей без юриста.
