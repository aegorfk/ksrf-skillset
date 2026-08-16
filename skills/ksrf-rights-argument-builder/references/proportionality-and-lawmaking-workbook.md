# Соразмерность и законодательные факты: сравнительный workbook

Используй этот справочник для генерации и критики гипотез о правоограничении, фактических предпосылках закона и интенсивности проверки. Он не устанавливает обязательную для КС РФ последовательность теста.

## Обязательные gates

1. `official_russian_anchor_required`: каждый юридический вывод подтверждается Конституцией РФ, действующим законом, официальным актом КС РФ и материалами конкретного дела.
2. `model_conflict -> abstain`: модель `scope-before-justification` Barak/Weinrib запускается только как альтернативный stress-test наряду с циклической и четырёхстадийной моделями. Если выбор модели меняет объём права, бремя, факты или результат, не объявляй ни одну последовательность обязательной.
3. `method_not_burden_rule`: научная модель не переносит в российский процесс иностранное распределение бремени или стандарт доказывания.
4. `no_due-lawmaking-import`: дефект законодательной процедуры или мотивировки сам по себе не означает неконституционность без самостоятельного российского substantive anchor.
5. `no_structural-supervision-import`: последующий мониторинг — исследовательский план, а не новое полномочие КС РФ.

## 1. Паспорт модели

До применения теста зафиксируй:

| Поле | Содержание |
| --- | --- |
| `selected_model` | Какая последовательность используется и только для какой функции |
| `competing_model` | Какая альтернативная модель может изменить анализ |
| `account_type` | Как источник понимает proportionality: optimization/maximization, unconstrained moral reasoning, specification/limitation, trump-модель либо иной account |
| `legal_direction_gap` | На каком переходе отсутствует российская норма, правовая категория или компетенционная граница и анализ превращается в открытую моральную/политическую оценку |
| `scope_effect` | Как модель меняет объём защищаемого права |
| `burden_effect` | Меняет ли она фактическое или правовое бремя |
| `fact_effect` | Какие новые факты потребуются |
| `structural_uncertainty` | Какой диапазон решений оставляет сама правовая структура и какому российскому институту принадлежит выбор |
| `epistemic_uncertainty` | Какие нормативные или эмпирические предпосылки неизвестны, кому доступны знания и насколько надёжен прогноз |
| `outcome_effect` | Может ли выбор модели изменить вывод или remedy |
| `russian_anchor` | Официальная российская опора для каждого применяемого элемента |

Эти поля документируют сравнительный critic-pass и не образуют новый обязательный тест. Заполняй их только в той мере, в какой выбранная модель влияет на конкретный тезис. `Structural_uncertainty` не доказывает свободу усмотрения, а `epistemic_uncertainty` — deference: обе требуют отдельной официальной российской опоры.

При материальном расхождении верни параллельные результаты, `status=model_conflict`, `required_action=abstain` и `human_resolution_required=true`, а не синтетический «средний» тест.

## 2. Законность ограничения и действительная цель

### Цепочка полномочия

Проверь `ограничивающий акт -> делегирование -> закон -> конституционная компетенция`, а также опубликование, доступность, ясность и достаточную конкретность основания. Разрыв маркируй `authority_gap` и устраняй только первичным российским источником.

### Карточка цели

- `declared_purpose` — цель, прямо названная официальным источником;
- `purpose_at_adoption` — подтверждённая цель при принятии;
- `purpose_as_applied` — цель, которой объяснён эффект в деле;
- `current_objective_purpose` — сохраняется ли цель сейчас;
- `constitutional_link` — связь с конкретной конституционной ценностью;
- `post_hoc_risk` — не сконструирована ли удобная цель после спора;
- `alternative_purpose` — конкурирующее объяснение регулирования.

Не подменяй дефект цели недостатком пригодности или необходимостью. Авторские критерии Barak и Weinrib используй как вопросы critic-pass, а не как российское правило.

## 3. Пригодность, альтернатива и маржинальный баланс

### Карточка пригодности

Для связи `мера -> цель` потребуй:

- описанный механизм действия;
- измеримый результат и baseline;
- источник и метод данных;
- вероятность эффекта и временную актуальность;
- встречные данные и альтернативное объяснение;
- предел, за которым данные не поддерживают вывод.

Официальное утверждение без фактической основы оставляй как claim, а не как подтверждённый факт. Из сравнительной модели не выводи автоматическую обязанность органа нести бремя в российском процессе.

### Матрица менее ограничительной альтернативы

Альтернатива считается рабочей только при одновременном подтверждении:

1. `same_actual_goal` — достигает той же действительной цели;
2. `equal_or_better_effectiveness` — сопоставимо эффективна по проверяемому механизму;
3. `less_harm` — причиняет меньший вред по охвату, интенсивности, длительности и вероятности.

Отдельно проверь индивидуальную оценку вместо blanket restriction, изменение технологий, стоимость, вред третьим лицам и реализуемость. Стоимость и побочные эффекты не скрывай внутри заявления о «неэффективности» — вынеси их в финальный баланс.

### Маржинальный баланс

Сравни спорную меру с рабочей альтернативой:

- дополнительная польза меры и вероятность этой пользы;
- дополнительный вред праву;
- срочность и последствия недостижения цели;
- положение вреда в ядре или на периферии права;
- охват, интенсивность, длительность и обратимость вреда.

Не сравнивай абстрактную «важность государства» с абстрактной «важностью права». Если мера побеждает только потому, что цель объявлена важной, подними QA-флаг.

### Параллельные ветви модели

Не предполагай, что все источники описывают один и тот же тест. При наличии достаточного российского якоря можно запустить несколько critic-ветвей:

| Ветвь | Отдельный вопрос | Stop condition |
| --- | --- | --- |
| `barak_purpose_and_zone` | Есть ли допустимая цель и сохраняется ли несколько соразмерных решений | Цель создана post hoc либо текст не выдерживает предлагаемого смысла |
| `moller_justification` | Разведены ли prima facie interference и окончательное нарушение; исследован ли реалистичный спектр альтернатив | Широкий scope права выдан за автоматическое нарушение |
| `alexy_structural` | Обоснована ли каждая качественная классификация интенсивности и веса | Число заменило аргумент или создало ложную точность |
| `sieckmann_balance_permission` | Допустимо ли вообще переходить к балансированию для этого права и контекста | Возможен prima facie запрет балансирования без отдельного ответа |
| `ordinal_critic` | Достаточно ли обоснованного порядкового сравнения без арифметики | Несопоставимые факторы сведены в общий scalar score |
| `rios_parity` | Названы ли covering consideration и качественные различия; не находятся ли ценности в отношении parity | Нет общего основания сравнения либо parity выдана за автоматический выбор |
| `positive_obligation` | Как сравниваются бездействие, недостаточность и положительные альтернативы | Ресурсная или правовая осуществимость альтернативы не проверена |

Ветви не голосуют. Несовместимые результаты образуют `ModelConflictCard` и требуют `abstain` до решения юриста по актуальной российской доктрине.

### Gate сопоставимости и parity

До узкого балансирования заполни `covering_consideration`, `comparison_problem`, `quantitative_dimension`, `qualitative_dimension`, `parity_candidate`, `institution_with_authority` и `coherence_reason`. Различай `noncomparability`, `incommensurability`, `incomparability` и `vagueness`: это не синонимы. Parity означает возможную качественную сопоставимость без отношений «больше/меньше/равно» и служит диагнозом, а не алгоритмом выбора. Если принятие parity меняет исход Alexy/ordinal-ветви либо российское право не определяет уполномоченный институт, верни `model_conflict` или `human_resolution_required`.

### Реестр интенсивности и альтернатив

Для вреда отдельно фиксируй исходные факты и их доказательства:

- охват адресатов и особо затронутые группы;
- длительность, скорость, частоту и повторяемость;
- вероятность и эффективность воздействия;
- обратимость и остаточный риск;
- объективное воздействие и положение конкретного субъекта.

Категории `низкая`, `средняя`, `высокая` допустимы только после этой трассы и не являются измерением. Для каждой менее ограничительной или положительной альтернативы добавь законность, достижимость, стоимость, эффект, бремя третьих лиц и источник неопределённости. Фантазийная, незаконная либо ресурсно неоценённая альтернатива получает `not_viable`, а не искусственное преимущество.

## 4. Паспорт законодательного факта

Для каждого эмпирического тезиса используй `evidence-impact-method.md` и добавь:

| Поле | Что проверить |
| --- | --- |
| `claim` | Какой элемент теста зависит от факта |
| `source/period/population` | Источник, период и исследуемая совокупность |
| `denominator/method` | Знаменатель и способ получения результата |
| `comparability` | Сопоставима ли выборка с делом и действующей редакцией |
| `alternative_explanation` | Конкурирующая причинная версия |
| `adversarial_check` | Встречные данные или критика метода |
| `limit` | Максимально допустимый вывод |

Различай индивидуальные, содержательные законодательные, процедурные и процессуальные факты. Эмпирика не создаёт правовой критерий и не заменяет доказательство применения нормы.

## 5. Ex ante record и последующий контроль

### R1: что было известно при выборе меры

Запиши `goal`, `facts`, `forecast_method`, `alternatives`, `uncertainty`, `right/harm`, `review_intensity_query`, `margin_claim` и `monitoring_condition`. Пояснительная записка, слушания и impact assessment — доказательства отдельных предпосылок, но не презумпция конституционности или неконституционности.

Отсутствие общей мотивировки закона само по себе не создаёт дефект. Оно может быть релевантно, если российский источник требует конкретного факта, прогноза или критерия и пробел мешает проверить именно этот элемент.

### R2: что стало известно после применения

Активируй только при значимой неопределённости, сложности или динамичности фактов. Поля:

- `elapsed_time`;
- `monitor_owner` и его независимость;
- `indicators/method`;
- `forecast_vs_observed`;
- `new_facts/adverse_findings`;
- `revision_trigger`;
- `action_or_inaction`;
- `lawful_remedy_or_enforcement_route`.

Это research/QA plan. Без российского основания не превращай его в обязанность постоянного судебного надзора.

## 6. Интенсивность проверки как query field

Для critic-pass можно сравнить:

- `manifest/evident error`;
- `defensibility/plausibility`;
- `intensive factual review`.

Драйверы: значимость права и тяжесть вреда, предмет регулирования, сложность и динамичность, доступность знания, надёжность прогноза, институциональная компетенция. Итоговый уровень нельзя заявлять без официальной российской опоры.

Материальную оценку, эпистемическую неопределённость и институциональную компетенцию держи раздельно. Сложность вопроса не создаёт автоматическую deference, а важность права не создаёт автоматический строгий контроль. Если норма делегирует балансирование конечному правоприменителю или частному адресату, отдельно проверь: получателя делегации, перечень интересов, guiding criteria, участие затронутых групп, мотивировку, журналирование и маршрут пересмотра.

### Empirical eval warning

Не выводи «судебный активизм» из слова `пропорциональность`, широты доктрины или одного результата. Для такого вывода нужен отдельный evaluation corpus: заранее ограниченная по периоду и предмету полная выборка актов КС РФ, оспоренные акты нижних инстанций, фиксированный codebook (`argument_type`, `disposition`, `deference`, `burden_shift`, `procedural_review`, `individual_hardship`, `remedy`) и независимое двойное кодирование. Selection bias, неизвестная полнота или расхождение кодировщиков требуют `insufficient_evidence`; этот eval не является юридическим основанием жалобы.

## 7. Красные флаги

- расплывчатая общественная цель без конституционной связи;
- причинный тезис заменён формулой `разумные основания`;
- рабочая альтернатива не исследована;
- баланс допускает полное обнуление права;
- внутренняя согласованность закона выдана за самостоятельный конституционный эталон;
- `wrong but consistent`: вредное решение защищается одной последовательностью;
- законодательная `basic choice` сконструирована исследователем без официальных материалов;
- процессуальный идеал подменяет substantive defect;
- расчёт создаёт видимость точности при слабых данных;
- «активизм» выведен из доктринальной формулы без воспроизводимого корпусного кодирования;
- суду предлагается выбрать оптимальную политику вместо исключения конституционно неприемлемого варианта.

## Выход

- `ModelConflictCard`;
- `AuthorityAndPurposeCard`;
- `FitEvidenceCard`;
- `LessRestrictiveAlternativeMatrix`;
- `MarginalBalanceCard`;
- `LegislativeFactPassport[]`;
- `R1/R2 record`;
- `review_intensity_query` с российским authority status;
- adverse findings и более узкий remedy.

## Источники и locators

- Aharon Barak, *Proportionality: Constitutional Rights and Their Limitations*, Cambridge University Press, 2012: legality, PDF 131–138; purpose, PDF 267–308; rational connection, PDF 322–331; necessity, PDF 335–352; balance, PDF 362–374; trace and model, PDF 469–475. SHA-256: `169cfccb3934a3608ee66205a03d10858918ce5586249d642b0a6f6e2fcbf858`.
- Jacob Weinrib, *The Impasse of Constitutional Rights*, Cambridge University Press, 2025, DOI `10.1017/9781009010078`: system of rights, PDF 51–53; scope/purposive interpretation, PDF 62–74; purpose, means and final proportionality, PDF 92–105. SHA-256: `3f2daf4ce876cb20ea2b9af39083708bb4313b383246aad9ed3791819c0e9606`.
- Klaus Meßerschmidt, A. Daniel Oliver-Lalana (eds.), *Rational Lawmaking under Review*, Springer, 2016, DOI `10.1007/978-3-319-33217-8`: reasons, PDF 133–152 / pp. 129–148; consistency, PDF 175–177, 191–208, 224–230; legislative facts/intensity, PDF 243–255; post-legislative review, PDF 272–293; procedural review and critique, PDF 348–398. SHA-256: `c42a4851861ce27e4923aec3b2a626a8c7842d56a7b6d18e2642ae71d972a12e`.
- Aharon Barak, *The Judge in a Democracy*, Princeton University Press, 2006/2008: semantic range, PDF 150–158 / pp. 127–135; balancing and zone of proportional solutions, PDF 190–198, 277–282 / pp. 167–175, 254–259; comparative transfer, PDF 223–226 / pp. 200–203. SHA-256: `a366e88bef184e5dc95f4e69af9cc15c10f255f7c68422aaeb89f2c392b68069`.
- Aharon Barak, *Purposive Interpretation in Law*, Princeton University Press, 2005: purpose and semantic anchor, PDF 131–133, 169, 203–205, 391–405 / pp. 110–112, 148, 182–184, 370–384. SHA-256: `e73bae5e15d2071452fb2892809833561a0d56c7b731cabe2a2745dfce8e1d9a`.
- Kai Möller, *The Global Model of Constitutional Rights*, Oxford University Press, 2012: interference/violation, PDF 19–23 / pp. 1–5; balancing and alternatives, PDF 152–158, 196–222 / pp. 134–140, 178–204. SHA-256: `4ce68def7707fcc5796870f2ebefe48d9e1dfd0618fedd0cde87bceba45afb2f`.
- David Duarte, Jorge Silva Sampaio (eds.), *Proportionality in Law: An Analytical Perspective*, Springer, 2018: pre-balancing gates, PDF 31–32 / pp. 22–23; positive obligations, PDF 34–54 / pp. 25–45; intensity ledger, PDF 109–114 / pp. 101–106; fake precision critic, PDF 194–197 / pp. 188–191. SHA-256: `84a39743acab6c0e8eada4ab05f380dfcec2fc70a5e06ef08947069b056f1a80`.
- Jan-R. Sieckmann (ed.), *Proportionality, Balancing, and Rights: Robert Alexy's Theory of Constitutional Rights*, Springer, 2021: classifications behind numbers, PDF 12–20 / pp. 1–9; discretion and review, PDF 22–56 / pp. 11–45; gate against balancing, PDF 123–144 / pp. 113–134; epistemic uncertainty/deference, PDF 145–205 / pp. 135–195; delegated balancing, PDF 238–259 / pp. 231–252. SHA-256: `1725eeb4d7318341118ee2cfc2d08086e10493768d24e113677838b321156c15`.
- Piero Ríos Carrillo, “Proportionality, Comparability, and Parity,” *Legal Theory* 29 (2023) 257–288, DOI `10.1017/S1352325223000186`: comparison failures, PDF 9–14 / pp. 265–270; parity, PDF 25–27 / pp. 281–283; decision and authority implications, PDF 28–31 / pp. 284–287.
- Niels Petersen, *Proportionality and Judicial Activism*, Cambridge University Press, 2017, ISBN `978-1-107-17798-7`: doctrine versus observed activism, PDF 20–21 / pp. 8–9; sampling and coding, PDF 72–90 / pp. 60–78; findings, PDF 196–197 / pp. 184–185.
- Francisco J. Urbina, *A Critique of Proportionality and Balancing*, Cambridge University Press, 2017, ISBN `978-1-107-17506-8`: competing accounts — PDF 15–28 / pp. 1–14; commensurability — PDF 53–88 / pp. 39–74, особенно PDF 71–72 / pp. 57–58; limited guidance — PDF 152–161 / pp. 138–147; legally directed adjudication — PDF 164–210 / pp. 150–196; legally unaided adjudication — PDF 211–224 / pp. 197–210; differentiated legal categories — PDF 229–265 / pp. 215–251. SHA-256: `610cb57dc59d8e73b0a955e3faa9e42739110eb72edfb4cb968b85059f000bc6`.
- Grant Huscroft, Bradley W. Miller, Grégoire Webber (eds.), *Proportionality and the Rule of Law: Rights, Justification, Reasoning*, Cambridge University Press, first published 2014, present paperback 2015, ISBN `978-1-107-06407-2`, `978-1-107-64795-4`: model inventory — PDF 11–30 / pp. 1–20; conceptions — PDF 31–132 / pp. 21–122; rights theories — PDF 133–214 / pp. 123–204; justification, democracy and deference — PDF 215–320 / pp. 205–310; incommensurability — PDF 321–352 / pp. 311–342; legislating and neutrality — PDF 353–426 / pp. 343–416. Image-only scan; paraphrase OCR and visually verify any quotation. SHA-256: `31101b806ea3693360c3ffa107e2d62b4b35f8ff64921a766282635ad087a252`.
- Grégoire C. N. Webber, *The Negotiable Constitution: On the Limitation of Rights*, Cambridge University Press, 2009, ISBN `978-0-521-11123-2`: received approach — PDF 13–24 / pp. 1–12; constitution as activity — PDF 25–66 / pp. 13–54; limitation model — PDF 67–98 / pp. 55–86; critique of balancing — PDF 99–127 / pp. 87–115; constituting/specifying rights — PDF 128–159 / pp. 116–147; democratic limitation and justification — PDF 159–224 / pp. 147–212. SHA-256: `cb3ce83969fd82df69c3538b4572d7ea9a87a84d1fcf647259a5ddfd0c3d8378`.
- Matthias Klatt, Moritz Meister, *The Constitutional Structure of Proportionality*, Oxford University Press, 1st ed. 2012, ISBN `978-0-19-966246-3`: four stages and weight formula — PDF 26–32 / pp. 7–13; models of rights — PDF 34–63 / pp. 15–44; rule-of-law, calculation and incommensurability objections — PDF 64–91 / pp. 45–72; structural and epistemic discretion — PDF 94–103 / pp. 75–84; positive rights and omissions — PDF 104–127 / pp. 85–108; epistemic reliability and applications — PDF 128–184 / pp. 109–165. SHA-256: `e465120c6e231f437dcc98186250a8a16ce28d5775175a95e0f34a05bc16ffa9`.

Все источники — научные и сравнительные. Их locators позволяют проверить метод, но не заменяют официальный российский источник тезиса.
