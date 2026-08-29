# Аудит доказательственного вывода и зависимостей

## Содержание

- [Непреодолимые границы](#непреодолимые-границы)
- [Общий выход](#общий-выход)
- [1. Жизненный цикл бремени и презумпции](#1-жизненный-цикл-бремени-и-презумпции)
- [2. Конкурирующие объяснения: story + argument graph](#2-конкурирующие-объяснения-story-argument-graph)
- [3. Dependency DAG и запрет двойного счёта](#3-dependency-dag-и-запрет-двойного-счёта)
- [4. Red-team верности Legal-AI объяснения и нормативной утечки](#4-red-team-верности-legal-ai-объяснения-и-нормативной-утечки)
- [Минимальный выпускной контроль](#минимальный-выпускной-контроль)
- [Библиография и проверенные локаторы](#библиография-и-проверенные-локаторы)


Используй этот справочник, когда фактическая часть жалобы зависит от распределения бремени, презумпции, конкурирующих объяснений, причинной или информационной зависимости доказательств либо от вывода Legal AI. Цель — показать воспроизводимый нормативный или процедурный дефект, не подменяя КС РФ судом факта.

## Непреодолимые границы

- Все перечисленные ниже зарубежные книги — только `method`, `critic` или `eval`. Они не доказывают российское право, полномочия или допустимость жалобы в КС РФ, факты дела, допустимость доказательства, применённость нормы либо устойчивую российскую практику.
- Для каждого юридически значимого шага нужен действующий официальный российский носитель: точная норма и редакция, официальный акт КС РФ/ВС РФ либо иной допустимый первичный источник. Сходство с иностранной моделью не заменяет этот якорь.
- Для каждого фактического узла нужен `evidence_ref`: документ, лист/абзац/таймкод и происхождение. Пересказ суда или модели помечай как производный источник.
- Не проси КС РФ заново оценить достоверность, достаточность или вес конкретных доказательств. Переводи проблему в воспроизводимый критерий, презумпцию, распределение риска, процедуру, запрет либо правовой эффект спорной нормы.
- Допустимые статусы: `pass`, `fail`, `insufficient_evidence`, `not_applicable`, `model_conflict`, `human_resolution_required`. Не своди их к общему числу и не превращай неизвестность в отрицательный вывод.
- `drafting_ready=true` допустим только при одновременно подтверждённых российском якоре, доказательственных локаторах, связи с применённой нормой, границе полномочий КС РФ и ручной проверке. Иначе `required_action=abstain`.

## Общий выход

Каждый блок возвращает:

```yaml
block_id: burden_lifecycle | rival_explanation | dependency_dag | ai_fidelity
status: pass | fail | insufficient_evidence | not_applicable | model_conflict | human_resolution_required
proposition_id: string
finding: string
finding_codes: []
evidence_refs: []
russian_anchors: []
adverse_material: []
unresolved_gaps: []
ksrf_bridge: string | null
requires_fact_reassessment: true | false
required_action: continue | cure | abstain | human_review
human_reviews:
  - role: lawyer | evidence_expert | evaluation_expert
    reviewer: string | null
    scope: string
    result: pending | approved | rejected
    review_ref: string | null
drafting_ready: true | false
```

Если два метода дают несовместимые выводы, сохрани обе ветви, поставь `model_conflict`, `required_action=abstain` и `human_resolution_required`; не выбирай удобную ветвь автоматически.

Своди блоки без арифметического score. Для всех применимых блоков используй приоритет `model_conflict → human_resolution_required → fail → insufficient_evidence → pass`; если все блоки `not_applicable`, итог тоже `not_applicable`. `drafting_ready=true` возможен только когда каждый применимый блок имеет `status=pass`, все обязательные записи в `human_reviews` имеют `result=approved`, а `unresolved_gaps` пусты; при любом ином результате — `drafting_ready=false`.

## 1. Жизненный цикл бремени и презумпции

**Задача:** восстановить, кто, что, на какой стадии и на основании какого российского носителя должен был утверждать или доказывать. Не называй «переходом бремени» простое неблагоприятное последствие недоказанности.

### Input → transform → output

| Input | Transform | Output |
|---|---|---|
| Официальная норма в применимой редакции; акты всех пройденных стадий; заявления, возражения и ходатайства сторон; proposition/evidence ledger | Разведи бремя утверждения, представления материала и риск окончательной недоказанности; затем проследи стадии `initial_allocation → trigger → presumption → production_or_shift → rebuttal → resolution` | Карта жизненного цикла с владельцем на каждой стадии, точным носителем, сработавшим условием, способом опровержения, реакцией суда и незакрытым разрывом |

### Обязательные поля

- `case_id`, `proposition_id`, `court_stage`, `procedural_document`, `document_date`, `document_locator`;
- `norm_source`, `norm_version`, `carrier_type` (`enacted_norm`, `official_interpretation`, `case_specific_reasoning`), `norm_locator`;
- `burden_holder`, `burden_kind`, `initial_allocation`, `trigger_fact`, `trigger_evidence_ref`;
- `presumed_proposition`, `production_or_shift`, `rebuttal_route`, `rebuttal_material_refs`;
- `standard_or_test`, `objection_preserved`, `preservation_ref`, `court_response`, `court_response_ref`, `outcome_link`.

### Проверка по стадиям

1. **Initial allocation:** выпиши точный тезис и исходного носителя риска; не переноси англоязычную терминологию без российского соответствия.
2. **Trigger:** отдели юридическое условие презумпции от факта, который должен его активировать; дай локатор обоим.
3. **Presumption:** установи её содержание и юридический эффект. Молчание решения не создаёт презумпцию.
4. **Production or shift:** укажи, изменился ли только объём представления материала или риск окончательной недоказанности. Если носитель этого не говорит, сохрани неопределённость.
5. **Rebuttal:** перечисли допустимый способ опровержения и фактически представленный материал, включая неблагоприятный.
6. **Resolution:** сопоставь довод стороны и мотивированный ответ каждой инстанции; отдельно отметь, был ли дефект сохранён для последующей стадии.

### Adverse/refute

Ищи дела без презумпции, иную процессуальную форму, признанный или бесспорный факт, прямой отказ вышестоящего суда от предполагаемого перехода и сопоставимые дела с иным распределением. Гипотезу о системном дефекте опровергают официальный носитель противоположного правила и полная мотивировка, показывающая, что спор касается только оценки конкретного материала.

### Stop/abstain и human gate

- `insufficient_evidence` и `abstain`, если нет официального текста/редакции нормы, полного акта, соответствующего заявления стороны или точного локатора.
- Не восстанавливай переход бремени только из проигрыша стороны; не считай молчание суда подтверждением; не генерализуй `case_specific_reasoning` без российского корпуса сопоставимых актов.
- `objection_preserved=false` само по себе не доказывает ни допустимость, ни недопустимость жалобы. Добавь `preservation_gap` в `finding_codes`; если нет точного официального российского основания рассматривать вопрос вопреки пробелу и ручного подтверждения, поставь `status=insufficient_evidence`, `required_action=abstain`.
- `requires_fact_reassessment=true`, если вывод требует решить, какому свидетелю верить или достаточно ли конкретного доказательства; такой вывод не идёт в требование к КС РФ.
- Юрист вручную подтверждает вид бремени, нормативный носитель, стадию, сохранность возражения и конституционную значимость. Отсутствующие источник или record сохраняют `status=insufficient_evidence`: ручное мнение их не восполняет. Если источники полны, но это подтверждение ещё не дано, поставь `status=human_resolution_required`.

## 2. Конкурирующие объяснения: story + argument graph

**Задача:** проверить целостность фактической истории и силу каждого вывода, не превращая правдоподобный рассказ в установленный факт.

### Input → transform → output

| Input | Transform | Output |
|---|---|---|
| Хронология событий, первичные материалы и их происхождение, фактические тезисы судов, основная и минимум одна реально возможная альтернативная гипотеза | Построй отдельно story graph событий и argument graph выводов; свяжи каждый event/edge с evidence anchor, пометь поддержку, атаку, пробел, обобщение и зависимость; проверь обе гипотезы одним стандартом | Матрица конкурирующих объяснений, покрытие якорями, необъяснённые противоречия, tunnel-vision warning и флаг необходимости переоценки фактов |

### Обязательные поля

- `hypothesis_id`, `hypothesis_role` (`primary`, `rival`), `proposition_id`, `legal_materiality`;
- `event_id`, `actor`, `time`, `action`, `event_order`, `edge_type`;
- `evidence_id`, `evidence_ref`, `source_role` (`primary`, `derivative`, `judicial_summary`), `provenance`;
- `generalization`, `generalization_source`, `inference_type`, `support_or_attack`, `strength_basis`;
- `dependency_group`, `gap`, `contradiction`, `counterevidence_refs`;
- `raised_at_stage`, `preservation_ref`, `court_response_ref`, `ksrf_relevance`.

### Операционные правила

1. Сначала зафиксируй нейтральную хронологию; только затем добавляй причинные и намеренные связи.
2. Story edge без `evidence_ref` — гипотеза, а не факт. Повтор одного утверждения несколькими производными документами не повышает его независимую подтверждённость.
3. Формулируй strongest plausible rival только из материалов дела. Не изобретай событие, мотив или источник ради симметрии.
4. Для каждого ключевого вывода запиши правило перехода от evidence к proposition и контрпример, при котором переход не работает.
5. В `ksrf_bridge` оставляй только вопрос о нормативном критерии/процедуре и его правовом эффекте; фактический победитель остаётся неопределённым.

### Adverse/refute

Проверяй бесспорность факта, чисто правовой характер спора, отсутствие первичного якоря у rival, юридическую незначимость различия и прямой мотивированный ответ суда на альтернативу. Rival опровергнут только материалом с локатором или несовместимостью с подтверждённой хронологией, а не тем, что он менее удобен основной версии.

### Stop/abstain и human gate

- `abstain`, если ключевой event основан лишь на пересказе, rival не привязан к материалам дела либо довод не был заявлен и его нельзя проверить по record.
- При несовместимых, но одинаково привязанных версиях — `model_conflict`, обе ветви и ручное разрешение; не ранжируй достоверность автоматически.
- Если остаётся вопрос о доверии, весе или достаточности конкретного доказательства, ставь `requires_fact_reassessment=true` и не используй его как самостоятельный довод КС РФ.
- Юрист решает, обнаружен ли нормативный/процедурный дефект или лишь возможная ошибка в фактах, и подтверждает формулировку `ksrf_bridge`.

## 3. Dependency DAG и запрет двойного счёта

**Задача:** установить, сколько действительно независимых путей поддержки имеет тезис и не маскируют ли копии, общий источник или общий процесс одну и ту же информацию.

### Input → transform → output

| Input | Transform | Output |
|---|---|---|
| Evidence IDs, первичные источники, цепочки получения и копирования, даты, авторы/сборщики, экспертные входы, поддерживаемый тезис | Построй ориентированный provenance DAG; выдели `copied_from`, `derived_from`, `shared_process`, `common_source`, `common_cause`, `unknown`; сверни связанные узлы в independent-support groups; проверь альтернативную общую причину | Группы независимой поддержки, предупреждения о double count, неизвестные рёбра происхождения, explaining-away candidates и перечень недостающих первичных материалов |

### Обязательные поля

- `evidence_id`, `proposition_id`, `origin_id`, `origin_type`, `evidence_ref`;
- `collector`, `timestamp`, `acquisition_method`, `source_chain`, `derived_from`;
- `dependency_type`, `dependency_group`, `common_cause_candidate`, `independence_basis`;
- `reliability_source`, `counterevidence_refs`, `unknown_provenance_edge`, `materiality`.

### Операционные правила

1. Один первичный источник, процитированный в трёх документах, даёт одну группу поддержки, а не три независимых подтверждения.
2. Разные носители одного события могут быть независимы только при доказанно разных способах получения и первичных источниках.
3. Совпадающие формулировки, метаданные, время получения и единый сборщик — сигналы зависимости, но не окончательное доказательство; сохрани основание и степень неопределённости.
4. Для двух сходящихся источников проверь общий процесс, координацию, заимствование и общую причину. Затем проверь genuinely independent acquisition как опровержение зависимости.
5. Не складывай «вес» доказательств численно без валидированной модели, заранее заданной шкалы и корпуса; DAG показывает структуру, а не вероятность истинности.

### Adverse/refute

Обязательные отрицательные образцы: действительно независимые источники, один источник в нескольких физических проявлениях и противоречащий первичный материал. Зависимость подтверждается общей первичкой, доказанным копированием, совместным получением либо установленной общей причиной; опровергается разными первичными источниками и независимыми цепочками получения.

### Stop/abstain и human gate

- `insufficient_evidence`, если происхождение ключевого узла неизвестно, доступен только судебный пересказ или связь требует недоступной технической экспертизы.
- Не заполняй неизвестное ребро предполагаемым источником. Не объявляй документы независимыми только из-за разных авторов/дат.
- Если свёртка меняет юридически значимую картину, до получения первички — `required_action=abstain`.
- Эксперт подтверждает техническую зависимость; юрист — её процессуальную допустимость и значимость. Оба решения фиксируются отдельно.

## 4. Red-team верности Legal-AI объяснения и нормативной утечки

**Задача:** проверить, объясняет ли система собственный вывод на доступных на момент решения источниках или лишь рационализирует результат, утечку outcome/identity либо устаревшее право.

### Input → transform → output

| Input | Transform | Output |
|---|---|---|
| Модель/provider/version, prompt и retriever/index, dataset и split/cutoff, входные акты и редакции права, retrieved spans, prediction и claimed reasons, trace и human corrections | Прогони temporal/outcome leakage check, source-entailment, ablation, counterfactual, OOD/subgroup и law-drift tests; отдели описательную точность от нормативной приемлемости | Для всех найденных результатов заполни `finding_codes`: `faithful`, `unsupported_reason`, `temporal_leakage`, `outcome_leakage`, `normative_feedback_risk`, `drift`, `insufficient_observability`; общий `status` остаётся из закрытого списка выше; никаких drafting-ready выводов по умолчанию |

### Обязательные поля

- `model`, `provider`, `model_version`, `prompt_version`, `retriever_version`, `index_version`;
- `dataset_id`, `split`, `cutoff`, `input_act_ids`, `input_timestamp`, `law_version`;
- `feature_id`, `feature_available_at_cutoff`, `retrieved_source`, `retrieved_locator`;
- `prediction`, `claimed_reason`, `entailment_result`, `ablation_result`, `counterfactual_result`;
- `ood_or_subgroup`, `drift_check`, `human_correction`, `trace_id`, `reviewer`.

### Adverse/refute red-team

1. **Temporal/outcome leakage:** удали номер/суд/исход, позднейшие акты и метаданные после cutoff; изменение вывода без правового основания — красный флаг.
2. **Fidelity:** убери признак, названный главным основанием. Если результат не меняется и нет объяснения устойчивости, claimed reason не подтверждён.
3. **Counterfactual:** замени юридически значимый факт при прочих равных; неизменность или нелогичный скачок требует `human_resolution_required`.
4. **Source entailment:** каждое нормативное утверждение должно следовать из точного официального российского фрагмента в применимой редакции. Retrieval similarity — только discovery, не авторитет.
5. **Normative feedback:** проверь, не превращает ли модель частую прошлую практику, неравенство или ошибку в рекомендуемое правило.
6. **Adverse set:** изменённое право, редкая категория, противоположный исход при близких фактах, отменённый акт, неполная инстанционная цепочка и позднейший акт, попавший в признаки.

### Stop/abstain и human gate

- Добавь `insufficient_observability` в `finding_codes`, поставь `status=insufficient_evidence` и `required_action=abstain`, если неизвестны dataset/cutoff, версия модели или права, признаки, retrieved spans либо trace; уверенный текст не лечит непрозрачность.
- Любой из кодов `outcome_leakage`, `temporal_leakage`, `unsupported_reason`, `normative_feedback_risk`, `drift` в `finding_codes` даёт `status=fail` и блокирует использование объяснения в жалобе. Оно остаётся red-team находкой, пока тезис не восстановлен из первичных российских источников.
- Расхождение между объяснением модели и российским источником — `model_conflict`, не автоматический выбор одной стороны.
- Юрист подтверждает действующее право, применённость нормы и уместность для КС РФ; специалист по оценке подтверждает split, leakage/ablation и воспроизводимый trace. До внедрения нужны отдельный OpenSpec change, Langfuse-трассировка, DeepEval/held-out проверки и явное человеческое одобрение.

## Минимальный выпускной контроль

| Проверка | PASS | Иначе |
|---|---|---|
| Российский якорь | Официальный источник, точная редакция и локатор | `insufficient_evidence → abstain` |
| Evidence anchor | Каждый материальный узел имеет первичный или явно производный `evidence_ref` | `cure` либо `abstain` |
| Adverse/refute | Неблагоприятный материал искался и отражён | `human_review` |
| Зависимости | Копии и общие причины не посчитаны независимо | `finding_codes=[dependency_warning]`; `status=insufficient_evidence`; пересборка |
| Граница КС РФ | Довод касается нормативного критерия/эффекта, а не перевзвешивания фактов | `requires_fact_reassessment=true → abstain` |
| Модельный конфликт | Все несовместимые ветви сохранены | `model_conflict → human_resolution_required` |
| Человек | Юрист подписал российский якорь и `ksrf_bridge`; профильный эксперт — технический вывод | `drafting_ready=false` |

## Библиография и проверенные локаторы

Формат локаторов: `печатная страница / PDF-страница`. Диапазоны относятся к проверенному файлу/изданию; при иной оцифровке PDF-offset нужно сверить заново.

1. Floris J. Bex, *Arguments, Stories and Criminal Evidence: A Formal Hybrid Theory*, Law and Philosophy Library, vol. 92, Springer, 2011. ISBN 978-94-007-0139-7; eISBN 978-94-007-0140-3; DOI 10.1007/978-94-007-0140-3. Локаторы: 20–31/30–41; 34–77/44–87; 83–100/93–110; 132–160/142–170; 176–225/186–235; 240–262/250–272.
2. Terence Anderson, William Twining, *Analysis of Evidence: How to Do Things with Facts*, appendix by Philip Dawid, Weidenfeld and Nicolson, first edition, 1991. ISBN 0-297-82099-0; 0-297-82100-8. Это первое издание 1991 г., не позднейшее Cambridge edition. Локаторы: 47–104/83–140; 105–165/141–201; 257–328/293–364; 329–384/365–420.
3. Douglas Walton, *Argumentation Methods for Artificial Intelligence in Law*, Springer-Verlag Berlin Heidelberg, 2005. ISBN-10 3-540-25187-1; ISBN-13 978-3-540-25187-3. Локаторы: 2–16/17–31; 75–110/90–125; 115–141/130–156; 143–169/158–184; 173–211/188–226; 213–248/228–263.
4. Douglas Walton, Chris Reed, Fabrizio Macagno, *Argumentation Schemes*, Cambridge University Press, 2008. ISBN 978-0-521-89790-7; 978-0-521-72374-9. Локаторы: 7–40/17–50; 43–80/53–90; 87–120/97–130; 163–188/173–198; 220–271/230–281; 308–346/318–356.
5. Jan De Bruyne, Cedric Vanleenhove (eds.), *Artificial Intelligence and the Law*, Intersentia, 2021. ISBN 978-1-83970-103-0; PDF ISBN 978-1-83970-104-7; D/2021/7849/18. Локаторы: 10/43; 73–98/106–131; 104–111/137–144; 113–119/146–152; 123–148/156–181.
6. Kevin D. Ashley, *Artificial Intelligence and Legal Analytics: New Tools for Law Practice in the Digital Age*, Cambridge University Press, 2017. DOI 10.1017/9781316761380; ISBN 978-1-107-17150-3; 978-1-316-62281-0. Локаторы: 15–23/40–48; 73–104/98–129; 107–125/132–150; 127–164/152–189; 285–308/310–333; 350–390/375–415.
7. Douglas Walton, *Burden of Proof, Presumption and Argumentation*, Cambridge University Press, 2014. ISBN 978-1-107-04662-7; 978-1-107-67882-8. Локаторы: 49–83/62–96; 85–118/98–131; 122–142/135–155; 145–175/158–188.
8. H. L. A. Hart, A. M. Honoré, *Causation in the Law*, Clarendon Press/Oxford University Press, first published 1959; проверенный файл — lithographic reprint 1962 from corrected sheets of the first edition, не второе издание. Локаторы: 24–57/60–93; 58–78/94–114; 103–122/139–158; 126–170/162–206; 188–229/224–265; 230–260/266–296.
9. Jordi Ferrer Beltrán, Carmen Vázquez (eds.), *Evidential Legal Reasoning: Crossing Civil Law and Common Law Traditions*, Cambridge University Press, first published 2022. DOI 10.1017/9781009032049; ISBN 978-1-316-51699-7; 978-1-009-03204-9. Локаторы: 13–33/31–51; 125–137/143–155; 138–170/156–188; 217–247/235–265; 361–426/379–444.
10. David A. Lagnado, *Explaining the Evidence: How the Mind Investigates the World*, Cambridge University Press, 2022. DOI 10.1017/9780511794520; ISBN 978-1-107-00600-3; 978-0-521-18481-6. Локаторы: 32–73/54–95; 74–111/96–133; 112–155/134–177; 156–185/178–207; 186–209/208–231; 210–264/232–286.
11. Henry Prakken, Giovanni Sartor (eds.), *Logical Models of Legal Argumentation*, Kluwer/Springer, 1997; reprinted from *Artificial Intelligence and Law*, vol. 4, nos. 3–4 (1996). ISBN 978-94-010-6390-6; eISBN 978-94-011-5668-4; DOI 10.1007/978-94-011-5668-4. Локаторы книжной пагинации: 1–6/4–9; 7–42/10–45; 43–118/46–121; 119–140/122–143; 141–174/144–177; 175–211/178–214. В файле также напечатана исходная журнальная пагинация.
12. Christian Dahlman, Alex Stein, Giovanni Tuzet (eds.), *Philosophical Foundations of Evidence Law*, Oxford University Press, first edition, 2021. ISBN 978-0-19-885930-7; DOI 10.1093/oso/9780198859307.001.0001. Локаторы: 53–68/62–77; 108–122/117–131; 183–200/192–209; 201–250/210–259; 301–316/310–325; 349–410/358–419.
13. L. Karl Branting, *Reasoning with Rules and Precedents: A Computational Model of Legal Analysis*, Kluwer, 2000. ISBN 978-90-481-5374-9; eISBN 978-94-017-2848-5; DOI 10.1007/978-94-017-2848-5. Локаторы: 9–26/19–36; 27–61/37–71; 83–110/93–120; 111–134/121–144; 135–143/145–153.
14. Jaap C. Hage, *Reasoning with Rules: An Essay on Legal Reasoning and Its Underlying Logic*, Law and Philosophy Library, vol. 27, Kluwer, 1997; проверенный файл — softcover reprint of the hardcover first edition 1997. ISBN 978-90-481-4773-1; eISBN 978-94-015-8873-7; DOI 10.1007/978-94-015-8873-7. Локаторы: 1–9/14–22; 11–45/24–58; 78–105/91–118; 106–112/119–125; 113–123/126–136; 124–128/137–141.
