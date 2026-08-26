# Равенство, позитивные обязанности и границы права

Используй этот справочник как `idea_only`-слой для генерации и QA гипотез по дискриминации, позитивным обязанностям, горизонтальному эффекту, достоинству и границе `scope -> interference -> justification`. Он не создаёт российский тест и не подтверждает допустимость жалобы.

## Содержание

- [Обязательные gates](#обязательные-gates)
- [Общий evidence contract](#общий-evidence-contract)
- [KSID-MF-14: равенство и intersectionality](#ksid-mf-14-равенство-и-intersectionality)
- [KSID-MF-15: позитивная обязанность](#ksid-mf-15-позитивная-обязанность)
- [KSID-MF-16: горизонтальный эффект](#ksid-mf-16-горизонтальный-эффект)
- [KSID-MF-17: достоинство и overlap](#ksid-mf-17-достоинство-и-overlap)
- [KSID-MF-18: граница scope и justification](#ksid-mf-18-граница-scope-и-justification)
- [Genuine-conflict gate: конфликт двух прав](#genuine-conflict-gate-конфликт-двух-прав)
- [Конфликты моделей](#конфликты-моделей)
- [Источники и точные locators](#источники-и-точные-locators)

## Обязательные gates

1. `idea_only`: MF-14–18 не являются реализованными функциями и не используются как production-оценка.
2. `official_russian_anchor_required`: каждый drafting-ready юридический вывод требует Конституцию РФ, действующую редакцию нормы, официальный акт КС РФ и подтверждённое применение нормы в деле.
3. Иностранная доктрина не доказывает российское право, полномочия КС РФ, факты дела или применение нормы к заявителю.
4. `method_not_burden_rule`: иностранная модель не переносит бремя, стандарт доказывания, cause of action или remedy.
5. `model_conflict -> abstain`: несовместимые ветви не голосуют и не усредняются.
6. `human_resolution_required`: юрист вручную выбирает ветвь, если от неё зависят объём права, бремя, результат или просительная формула.
7. Допустимые статусы: `pass`, `fail`, `insufficient_evidence`, `not_applicable`, `model_conflict`, `human_resolution_required`. Единого числового score нет.

До реализации требуется отдельный OpenSpec change, artifact contract, hard negatives, refusal/conflict cases, held-out evaluation, Langfuse/DeepEval, leakage review и human approval.

## Общий evidence contract

Собери официальную редакцию нормы на юридически значимые даты и полные акты первой, апелляционной, кассационной инстанций, ВС РФ и КС РФ. Для конвенционного тезиса добавь официальный HUDOC.

Минимальные поля:

| Поле | Требование |
| --- | --- |
| `case_id/court_level/act_date` | Идентификатор, инстанция, дата |
| `official_url/full_text_hash` | Проверяемый источник и версия текста |
| `norm_version` | Редакция нормы на значимые даты |
| `norm_application_mode` | `explicit`, `reasoning_linked_implicit`, `party_only`, `unclear` |
| `finding_source` | Каким актом установлен факт; allegation не равна finding |
| `reasoning_span/locator` | Точный фрагмент и страница/абзац |
| `holding/outcome/remedy` | Что решил суд и каким способом |
| `russian_anchor` | Официальная российская опора конкретного элемента |
| `adverse_authority/limit` | Контрматериал и максимальный допустимый вывод |
| `confidence/status` | Уверенность и один из разрешённых статусов |

Общий stop: нет полного текста; неизвестна редакция нормы; норма только приведена стороной; требуется переоценка доказательств; не подтверждены полномочия КС РФ; sensitive attribute выведен предположительно.

## KSID-MF-14: равенство и intersectionality

`equality_intersectionality_claim_decomposer`

### Workflow

1. Назови российскую гарантию равенства и применённую норму.
2. Зафиксируй признаки, группы, относительное неблагоприятное положение и механизм распределения вреда.
3. Классифицируй claim: `single_axis`, `multiple`, `additive_or_compound`, `embedded`, `intersectional`, `unclear`.
4. Отдельно классифицируй механизм: `direct`, `indirect`, `accommodation`, `harassment`, `affirmative_action`, `unclear`.
5. Для indirect claim проверь связь adverse effect с группой, размер/качество выборки и альтернативное объяснение. Корреляция не равна индивидуальной причинности.
6. Для intersectional claim проверь целостный, неаддитивный механизм; не раскладывай его автоматически на независимые признаки.
7. Согласуй comparator, justification, burden и remedy с выбранной классификацией.

### Поля и выход

`grounds_claimed`, `grounds_legally_anchored`, `affected_group`, `group_pattern_evidence`, `adverse_effect`, `claim_mode`, `mechanism`, `causal_interaction`, `comparator_set`, `duty_bearer_power`, `aim`, `alternative`, `burden`, `remedy_fit`.

Верни classification card, evidence gaps, competing classification, российский anchor и предел вывода. `Abstain`, если имеется лишь индивидуальная несправедливость, формальное перечисление признаков, неподтверждённая статистика либо система должна сама вывести чувствительный признак.

## KSID-MF-15: позитивная обязанность

`positive_obligation_trigger_scope_content_breach_ledger`

### Workflow

1. Назови российский источник обязанности и компетентный публичный субъект.
2. Выбери тип: расследование, нормативная рамка, процедура или конкретная operational measure.
3. Раздели `trigger`, `scope`, `content` и `breach`; существование права не доказывает конкретную меру.
4. Построй timeline фактического/вменённого знания без hindsight; укажи характер и непосредственность риска.
5. Отдельно проверь контроль, причинность и `real prospect` предотвращения вреда.
6. Сравни законные и осуществимые альтернативы, стоимость, вред третьим лицам и конкурирующие обязанности.
7. Только после этого проверяй нарушение и доступный КС РФ remedy.

### Поля и выход

`obligation_type`, `notice_event`, `actual_or_constructive_knowledge`, `risk_type`, `risk_time`, `actor_control`, `legal_competence`, `candidate_measure`, `causal_counterfactual`, `real_prospect`, `burden`, `third_party_risk`, `trigger_met`, `scope`, `content`, `breach_separate`.

Верни ledger по каждой кандидатной мере. `Abstain` при отсутствии российской обязанности/знания/контроля, чистом hindsight, спекулятивной причинности, незаконной или ресурсно неоценённой мере.

## KSID-MF-16: горизонтальный эффект

`horizontal_effect_route_mapper`

### Workflow

1. Классифицируй стороны и публичность каждого актора.
2. Выбери только как гипотезу маршрут: `vertical`, `direct_horizontal`, `indirect_horizontal`, `positive_protection`, `court_as_state_act`.
3. Для непрямого маршрута назови медиатора: закон, обязательный смысл, презумпцию, решение суда или бездействие государства.
4. Зафиксируй права обеих частных сторон, власть, ресурсы, контроль доступа к возможностям и стоимость обязанности.
5. Назови российский ordinary-law cause, применённую норму и допустимый remedy.
6. Проверь, не превращён ли частный вред без государственной связки в предмет нормоконтроля.

### Поля и выход

`public_or_private_actor`, `route`, `ordinary_law_cause`, `state_or_court_mediation`, `competing_private_right`, `power_resources`, `opportunity_gatekeeper`, `candidate_duty`, `applied_norm`, `remedy_route`.

Верни route map и отсутствующие звенья. Иностранная direct-horizontal модель никогда не выбирается по умолчанию. `Abstain`, если российский медиатор или применённая норма не установлены.

## KSID-MF-17: достоинство и overlap

`dignity_role_overlap_guard`

### Workflow

1. Назови точную позицию КС РФ по статье 21 Конституции РФ.
2. Классифицируй роль достоинства: `value`, `independent_right`, `interpretive_anchor`, `derivative_right_candidate`, `rhetorical_only`.
3. Конкретизируй вред: унижение, объективация, отрицание автономии или возможности формировать жизненный план.
4. Проверь overlap со специальным правом и запрети остаточную формулу, если специальная гарантия полностью покрывает тезис.
5. Выбери как competing models широкую относительную или узкую абсолютную архитектуру; не смешивай scope и justification.
6. Не создавай «дочернее право» или remedy без российского основания.

### Поля и выход

`dignity_role`, `operative_effect`, `specific_right_overlap`, `autonomy_harm`, `objectification`, `limitation_architecture`, `derivative_right_anchor`, `remedy_fit`.

Верни role/overlap card. `Abstain`, если достоинство лишь риторика, архитектуры дают разные результаты либо тезис требует нового права или полномочия КС РФ.

## KSID-MF-18: граница scope и justification

`scope_interference_justification_boundary_audit`

### Workflow

1. Отдельно запиши защищаемый интерес, основание попадания в scope, вмешательство и оправдание.
2. Классифицируй право как абсолютное или допускающее ограничение; для абсолютного права проверяй threshold, а не скрытое оправдание.
3. Сравни wide- и narrow-scope ветви и покажи, где возникает hidden balancing.
4. Не импортируй иностранное распределение бремени; запиши его лишь как research query.
5. Отдельно кодируй позитивную и процедурную обязанность, выведенную из материального права.
6. Для дискриминации различай scope другого права, более широкий ambit и самостоятельную гарантию.
7. Проверь институциональные последствия, но не превращай caseload в материальный критерий.

### Поля и выход

`protected_interest`, `scope_basis`, `interference`, `justification`, `absolute_or_limited`, `threshold`, `hidden_balancing`, `burden_query`, `positive_or_procedural_obligation`, `ambit`, `scope_expansion_precedent`, `institutional_cost`.

Верни две stage maps и boundary defects. Если выбор wide/narrow scope меняет бремя, результат или remedy без российского ответа, верни `model_conflict`.

## Genuine-conflict gate: конфликт двух прав

Используй модель Stijn Smet только как `idea_only`-маршрутизатор до балансирования. Она помогает отличить конфликт двух прав от спора `право -> публичный интерес`, но не задаёт российскую иерархию прав, бремя или remedy.

### Последовательность

1. **Оба российских якоря.** Для `right_a` и `right_b` назови действующие нормы и официальные позиции КС РФ. Иностранная квалификация либо ссылка стороны не создаёт второй якорь.
2. **Фактическая затронутость обоих прав.** Установи носителей, защищаемые интересы и факты отдельно по каждой стороне. Абстрактная возможность вреда и агрегированный публичный интерес недостаточны.
3. **Несовместимость обязанностей.** Восстанови `duty_a` и `duty_b` по российскому праву и покажи, почему их нельзя одновременно исполнить. Если спор разрешается через `scope`, специальную норму, компетенцию или отсутствие одной обязанности, это не остаточный конфликт прав.
4. **`defuse`.** Сначала проверь узкую фактическую или правовую квалификацию, которая снимает конфликт, не стирая одно из прав и не подменяя российский anchor иностранной категорией.
5. **`compromise`.** Проверь законное и практически осуществимое взаимное приспособление; отдельно запиши остаточный вред каждой стороне, стоимость и воздействие на третьих лиц.
6. **`residual_balance`.** Только для неустранённого остатка построй раздельные nets of reasons обеих сторон. Не превращай value, impact, core/periphery, дополнительные права, общий интерес, цель и ответственность из модели Smet в числовую шкалу или готовые российские критерии.
7. **Конфликт моделей.** Если выбор framing, критерия сравнения или модели прав меняет исход, верни `status=model_conflict`, `required_action=abstain` и передай вопрос юристу.

### Поля и stop conditions

`right_a_russian_anchor`, `right_b_russian_anchor`, `right_a_engaged`, `right_b_engaged`, `right_holders`, `duty_a`, `duty_b`, `duties_incompatible`, `public_interest_only`, `party_only_right`, `classification`, `defuse_route`, `compromise_feasibility`, `residual_harm_a`, `residual_harm_b`, `third_party_effect`, `framing_sensitivity`, `status`, `required_action`.

Нормализуй выход: `classification=not_genuine_conflict` и `status=not_applicable`, если конфликт снимается до балансирования; `status=insufficient_evidence` и `required_action=abstain`, если отсутствует хотя бы один российский якорь, второе право лишь названо стороной, обязанность спекулятивна или полный reasoning недоступен. Любой drafting-ready вывод и просительная формула требуют ручной проверки российского конституционалиста.

## Конфликты моделей

| Конфликт | Обязательная реакция |
| --- | --- |
| Alexy scalar/ordinal optimization vs Ríos parity | Запустить обе ветви; при разном результате `model_conflict` |
| Broad-relative dignity vs narrow-absolute dignity | Сначала MF-17 architecture gate |
| Wide scope vs narrow scope; blended vs bifurcated review | Две карты MF-18, без скрытого выбора |
| Khaitan group/correlation vs Atrey integral intersectionality | Разные режимы MF-14; не сводить intersectional claim к сумме |
| Direct vs indirect horizontal effect | MF-16 требует российского route и медиатора |
| Доктринальная широта vs фактический «активизм» | Не делать вывод без воспроизводимого корпусного кодирования |

## Источники и точные locators

`PDF` означает физическую страницу файла; `печат.` — страницу на полосе. У Barak и *Shaping Rights* текст извлечён локальным OCR, поэтому дословную цитату нужно визуально перепроверить.

1. Tarunabh Khaitan, *A Theory of Discrimination Law*, OUP, 1st ed. 2015, © T. Khaitan 2015, ISBN 978-0-19-876631-5: четыре условия — PDF 43–60 / печат. 25–42; architecture/duties — PDF 63–85 / 45–67; correlation — PDF 186–189 / 168–171; justification — PDF 198–209 / 180–191; gatekeepers — PDF 227–229 / 209–211.
2. Robert Alexy, *A Theory of Constitutional Rights*, trans. Julian Rivers, OUP, English ed. 2002, corrected paperback 2010, © Suhrkamp 1986, translation © 2002, ISBN 978-0-19-825821-6, 978-0-19-958423-9: norm reconstruction — PDF 87–91 / 31–35; rules/principles — PDF 103–110 / 47–54; proportionality — PDF 123–124 / 67–68; protection — PDF 356 / 300; horizontal effect — PDF 408–410 / 352–354; epistemic law — PDF 474–475 / 418–419.
3. Christina R. Bambrick, *Constitutionalizing the Private Sphere: A Comparative Inquiry*, CUP, 2024, DOI 10.1017/9781009293723: vertical/horizontal — PDF 18–19 / 4–5; direct/indirect — PDF 25–26 / 11–12; actor/duty calibration — PDF 33–38 / 19–24; context — PDF 158–176 / 144–162; positive/negative duty — PDF 244 / 230.
4. Janneke Gerards, *General Principles of the European Convention on Human Rights*, CUP, 2019, DOI 10.1017/9781108652926: rights typology — PDF 27–36 / 19–28; interpretation/common ground — PDF 55–64 / 47–56 и PDF 101–103 / 93–95; positive obligations — PDF 118–141 / 110–133; horizontal effect — PDF 153–167 / 145–159; intensity/procedure — PDF 175–176 / 167–168 и PDF 239–267 / 231–259.
5. Aharon Barak, *Human Dignity: The Constitutional Value and the Constitutional Right*, trans. Daniel Kayros, CUP, 2015, ISBN 978-1-107-09023-1, 978-1-107-46206-9: value/right/autonomy — PDF 7–8 / xviii–xix; broad-relative vs narrow-absolute — PDF 8–9 / xix–xx; mother/daughter rights и overlap — PDF 9–10 / xx–xxi; discretion critique — PDF 10–11 / xxi–xxii.
6. Vladislava Stoyanova, *Positive Obligations under the European Convention on Human Rights: Within and Beyond Boundaries*, OUP, 1st ed. 2023, DOI 10.1093/oso/9780192888044.001.0001: trigger/scope/content/types — PDF 39–40 / 18–19; knowledge/no hindsight/risk — PDF 42–65 / 21–44; causation — PDF 66–91 / 45–70; reasonableness/alternatives — PDF 94–142 / 73–121; investigation — PDF 144–188 / 123–167; substantive duties — PDF 192–238 / 171–217; extraterritorial normative preconditions — PDF 240–248 / 219–227.
7. Niels Petersen, *Proportionality and Judicial Activism*, CUP, 2017, ISBN 978-1-107-17798-7: doctrine vs observed activism — PDF 20–21 / 8–9; sampling/coding — PDF 72–90 / 60–78; argument codes — PDF 89–90 / 77–78; findings — PDF 196–197 / 184–185.
8. Piero Ríos Carrillo, “Proportionality, Comparability, and Parity,” *Legal Theory* 29 (2023) 257–288, DOI 10.1017/S1352325223000186, © 2024, CC BY 4.0: problem — PDF 1–3 / журн. 257–259; four comparison failures — PDF 9–14 / 265–270; parity — PDF 25–27 / 281–283; decision/authority implications — PDF 28–31 / 284–287.
9. Sandra Fredman, *Comparative Human Rights Law*, OUP, 1st ed., impression 1, 2018, ISBN 978-0-19-968941-5, 978-0-19-968940-8: deliberative resource — PDF 42–43 / 5–6; context/import hazards — PDF 43–46 / 6–9; convergence/divergence and adverse uses — PDF 49–53 / 12–16; legitimacy/competence — PDF 116–151 / 79–114; interpretation — PDF 152–189 / 115–152.
10. Shreya Atrey, *Intersectional Discrimination*, OUP, 1st ed., impression 1, 2019, DOI 10.1093/oso/9780198848950.001.0001: five-part framework — PDF 60–77 / 37–54; category continuum — PDF 101–161 / 78–138; claim workflow — PDF 163–230 / 140–207; comparators — PDF 196–202 / 173–179; anti-universalization — PDF 235–237 / 212–214.
11. Eva Brems, Janneke Gerards (eds.), *Shaping Rights in the ECHR*, CUP, first published 2013, ISBN 978-1-107-04322-0: scope/interference/justification — PDF 11–13 / 1–3; wide/narrow scope и institutions — PDF 14–19 / 4–9; positive/procedural obligations — PDF 19–20 / 9–10; absolute-right threshold — PDF 22 / 12; Article 14 ambit — PDF 23–24 / 13–14.
12. Stijn Smet, *Resolving Conflicts between Human Rights: The Judge's Dilemma*, Routledge, 2017, ISBN 978-1-138-65801-1, 978-1-315-62101-2: постановка конфликта — PDF 13–17 / печат. 1–5; определение, converse-situation и conflicting-duties tests — PDF 56–77 / 44–65; `defuse -> compromise -> balance` — PDF 78–95 / 66–83; несоизмеримость и framing — PDF 97–150 / 85–138; nets of reasons и семь критериев — PDF 153–195 / 141–183; сильная несоизмеримость — PDF 215–235 / 203–223.

Все locators позволяют проверить метод, но не заменяют российский authority ledger или официальный HUDOC.
