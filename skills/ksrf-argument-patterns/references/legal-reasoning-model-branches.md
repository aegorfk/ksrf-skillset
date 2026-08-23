# Ветви юридического рассуждения: правила, принципы, аналогия и цель

Используй этот справочник для генерации и критики вариантов толкования, аналогий и исключений. Это сравнительная научная методика, а не российское право и не обязательная теория толкования КС РФ.

## Жёсткие gates

1. `official_russian_anchor_required`: итоговый тезис о смысле нормы, статусе акта, бремени, исключении или компетенции подтверждается актуальным официальным российским источником.
2. `parallel_models_not_vote`: Scalia, Dworkin, Sunstein, Schauer, La Torre и Barak образуют конкурирующие ветви. Известность автора и число совпавших ветвей не определяют результат.
3. `model_conflict -> abstain`: если выбор ветви меняет смысл нормы, объём права, допустимость исключения или вывод, сохрани расхождение и передай выбор юристу.
4. `no_automatic_override`: расхождение буквального результата и предполагаемой цели не даёт полномочия отступить от правила.
5. `authority_before_similarity`: тематическая или векторная близость не превращает dictum, иностранное решение или вторичный источник в применимую позицию.
6. `foreign_method_only`: frame/baseline audit и role-классификация reasonableness служат critic/discovery. Они не устанавливают российский смысл нормы, стандарт проверки, практику или полномочие.
7. `foreign_philosophy_never_invalidates`: иностранная философия права может выявить конфликт правовой определённости, равенства/справедливости и цели, но никогда не возвращает `invalid`, `disapply` или полномочие отступить от российского закона.

## 1. Паспорт интерпретации

Для спорного положения заполни:

| Поле | Что установить |
| --- | --- |
| `norm_text` | Официальный текст, редакция и дата |
| `semantic_range` | Какие значения выдерживает текст и системный контекст |
| `semantic_level` | `concrete`, `abstract` или `disputed` |
| `subjective_purpose` | Подтверждённая цель конкретного правотворца |
| `objective_purpose` | Системная цель, выведенная из права, а не психологии автора |
| `purpose_evidence` | История, связанные нормы, официальная практика и предел каждого источника |
| `claimed_exception` | Какое исключение предлагается и кто вправе его признать |
| `competing_readings` | Минимум одно добросовестное конкурирующее прочтение |
| `russian_anchor` | Российский официальный источник для каждого drafting-ready вывода |

Цель не создаёт значение за пределами семантического диапазона. Если диапазон или уровень абстракции спорны, построй отдельные textual, abstract-principle и purposive ветви.

## 2. Правило, основание и исключение

Сравни четыре результата:

| Поле | Содержание |
| --- | --- |
| `literal_result` | Что следует из закреплённой генерализации |
| `justification_result` | Что следовало бы только из доказанного основания правила |
| `known_exception` | Есть ли официально признанное исключение |
| `authority_to_depart` | Вправе ли конкретный орган отступить либо сформировать исключение |

Отдельно отметь:

- `over_inclusive`: правило охватывает случай, не поддерживаемый его доказанным основанием;
- `under_inclusive`: правило не охватывает случай, который основание, возможно, поддерживает;
- `rule_error`: цена применения генерализации;
- `decision_maker_error`: цена свободного усмотрения;
- `insufficient_evidence`: цель, частота или тяжесть ошибок не подтверждены.

Расхождение само по себе лишь ставит вопрос. Без российского полномочия результат — `no_authority_to_override`, а не автоматическое исключение.

## 3. Правила и принципы как параллельные режимы

- В `rule_mode` проверь текст, официальные исключения и all-or-nothing effect конкретного правила.
- В `principle_mode` храни направление довода, конкурирующие основания и источник веса; не превращай принцип в жёсткий `if/then`.
- В `institutional_mode` проверь, кто несёт риск ошибки и кто вправе учитывать исключение.

Дихотомия rules/principles спорна. Если режимы дают разные итоги, не компилируй их в общий score.

## 3A. LegalValueConflictLedger и ExtremeInjusticeClaimGuard

### LegalValueConflictLedger

**Input → transform → output:** спорное толкование, норма и заявленный результат → раздельно проследи `positive_source_and_version`, legal certainty, equality/justice, purposiveness/public benefit, фактические предпосылки, конкурирующие ветви толкования и competent decision-maker → `LegalValueConflictLedger` с authority/evidence gaps. Это critic-pass ценностного конфликта, а не формула приоритета и не российский тест действительности.

Не своди ценности в scalar score. Для каждой ветви сохрани `claim`, `official_russian_anchor`, `facts`, `counterweight`, `adverse_authority`, `semantic_limit`, `competent_actor`, `permitted_route`, `currentness` и `residual_uncertainty`. Обычная несправедливость, нецелесообразность или несогласие с policy не отменяют положительное право.

### ExtremeInjusticeClaimGuard

**Input → transform → output:** draft, который связывает крайнюю несправедливость с недействительностью или неприменением → потребуй точную действующую российскую норму и официальный акт КС РФ, отдельно проверь equality anchor, доказательства тяжести и, если заявлен, умысла, semantic range, уполномоченного decision-maker, разрешённый route, legal-certainty objection, более узкое официальное толкование и adverse cases → один из статусов `foreign_philosophy_only`, `blocked_missing_russian_authority` или `ready_for_human_critic_review`.

Guard **никогда** не выдаёт `invalid`, `law_ceases_to_be_law`, `disapply`, `court_may_ignore_statute`, готовую допустимость или remedy. Даже наличие российского якоря переводит материал только на ручную правовую проверку; оно не делегирует философской модели вывод по делу.

**Confirm/refute/stop:** drafting-ready юридический элемент может быть подтверждён только действующими Конституцией РФ, ФКЗ/законом, официальным актом КС РФ и record конкретного дела. Claim ослабляют официальный narrower construction, ordinary unjust-but-valid cases, недоказанная intentional inequality, иной equality rationale, последующая редакция и competence rejection. Верни `blocked_missing_russian_authority`, если draft перескакивает от «несправедливо» к «недействительно», предлагает обычному суду игнорировать закон, либо неизвестны severity, equality effect, actor или route. Любое внешнее использование утверждает юрист-конституционалист.

## 4. Аналогия, holding и различение

Для каждого акта заполни:

`court/status/date -> proposition -> exact locator -> holding_or_dicta -> binding_scope -> shared_features -> different_features -> relevance_rule -> counteranalogy`.

Holding — только положение, необходимое для исхода в проверенном контексте. Любые два дела похожи и различаются по некоторым признакам; юридическую значимость признака объясняет правило релевантности, а не embedding similarity.

Верни `analogy_not_ready`, если не установлены факты обоих дел, официальный статус, точное положение либо различие способно изменить обосновывающий принцип.

## 5. Лестница абстракции и минимализм

Построй минимум три формулировки тезиса:

1. узкая, привязанная к подтверждённым фактам и нормативному механизму;
2. средняя, охватывающая существенно сходные случаи;
3. широкая принципиальная.

Для каждой покажи, что она решает, какие вопросы оставляет открытыми и где появляются hard negatives. Узкая формула — кандидат, а не презумптивно верный ответ. Эскалируй уровень, если минимализм не разрешает заявленный правовой вопрос, маскирует принципиальное противоречие или воспроизводит доказанный вред.

### 5A. Frame/baseline sensitivity audit

**Input → transform → output:** проверенный текст и редакция российской нормы, факты с locators, исходная рамка и заявленный baseline → меняй по одной оси, не меняя доказательственную базу, и повторяй inference trace → `FrameSensitivityAudit` с полями `axis`, `original_frame`, `alternative_frame`, `russian_basis`, `result_changed`, `causal_step`, `independent_ground` и `status`.

Проверь как минимум пять осей:

- узкий/широкий временной интервал;
- единая/сегментированная транзакция или последовательность действий;
- действие/бездействие и соответствующий субъект обязанности;
- узкая/средняя/широкая формулировка из лестницы абстракции;
- baseline: подтверждённое правом исходное состояние, правомерный `but-for` сценарий либо официальный comparator. Нельзя подменять baseline бытовым ожиданием или желательным результатом.

**Adverse/refute pass:** построй сильнейшую альтернативную рамку оппонента; проверь, сохраняется ли вывод при ней; ищи самостоятельное основание, которое делает смену рамки нематериальной; отмечай, если рамка встречается только в позиции стороны либо отвергнута судом. Если результат одинаков или его независимо поддерживает проверенное основание, claim о frame sensitivity опровергнут или ослаблен.

`abstain_frame`: нет официальной российской опоры для baseline, неполон текст акта, неизвестна редакция нормы, рамка требует домысла о скрытой цели либо смена нескольких осей не позволяет установить причинный шаг. Материальная смена результата всегда получает `human_resolution_required`; audit не выбирает «правильную» рамку автоматически.

### 5B. Ролевой классификатор reasonableness

**Input → transform → output:** каждое точное употребление термина разумности или функционального эквивалента с `speaker`, locator, стадией и российским authority → классифицируй роль, не выводя её из одного слова → `ReasonablenessRoleRecord`:

| Ось | Допустимые значения |
| --- | --- |
| `order` | `first_order_conduct`, `second_order_review`, `mixed`, `unknown` |
| `decision_mode` | `threshold_or_sufficiency`, `optimization_or_balancing`, `mixed`, `unknown` |
| `dimension` | `procedural`, `substantive`, `mixed`, `unknown` |
| `function` | `direct_criterion`, `equality_comparator`, `discretion_control`, `proportionality_component`, `other`, `unknown` |
| `support` | факторы, доказательства, официальный источник, точный locator и применимая редакция |

Reasonableness не является синонимом proportionality: связь допустима только когда её прямо задаёт применимый российский источник. Не переносить между делами роли `conduct standard`, `review intensity`, `equality comparator` и `discretion control` без отдельной опоры.

**Adverse/refute pass:** ищи то же слово в иной роли, официальный тест с иными элементами, контрпример, где требование выполнено без balancing, и источник, который относит формулу лишь к стороне или к описанию фактов. При конкурирующих классификациях сохрани обе с основаниями.

`abstain_reasonableness_role`: не установлен speaker, неясно first-/second-order употребление, отсутствует официальный российский тест или модели дают разные последствия. Юрист вручную подтверждает роль и допустимый эффект; сравнительная литература не создаёт стандарт проверки.

## 6. Hard-case router

Если текст, система и практика не дают единственного вывода, выпусти параллельные конструкции:

- `public_meaning/textual`;
- `abstract_principle`;
- `purposive`;
- `narrow_analogy/minimalist`;
- `rule_error_vs_discretion`;
- `fit_plus_principle`.

Для каждой нужны `claim`, `evidence`, `counterargument`, `institutional_limit`, `adverse_effect` и `russian_anchor_status`. При двух разумных несовместимых ветвях результат — `human_resolution_required`.

## 7. Application, justification и policy

Не смешивай:

1. применение установленной нормы к доказанным фактам;
2. обоснование действительности или смысла нормативной посылки;
3. прогноз и оценку policy-эффекта.

Реконструкция должна показывать каждый использованный текст и добавленную связующую посылку. Привычный topos, согласие аудитории или полезный эффект не делают вывод истинным и не позволяют растворить индивидуальное право в коллективной цели.

## Выход

- `InterpretationPassport`;
- `RuleJustificationDivergenceMatrix`;
- параллельные `RulePrincipleBranch[]`;
- `AuthorityHoldingAnalogyLedger`;
- `AbstractionLadder`;
- `FrameSensitivityAudit`;
- `ReasonablenessRoleRecord[]`;
- `LegalValueConflictLedger`;
- `ExtremeInjusticeClaimGuard` только со статусами critic/blocked/human-review;
- `HardCaseBranchSet`;
- `application/justification/policy` trace;
- `model_conflict`, `missing_evidence` и вопросы для ручного решения.

## Источники и locators

- Antonin Scalia, *A Matter of Interpretation: Federal Courts and the Law*, Princeton University Press, 1997: текст и намерение, PDF 31, 41–42 / печ. с. 17, 27–28; абстрактная гарантия в комментарии Ronald Dworkin и ответе Scalia, PDF 131–140, 158–160 / с. 117–126, 144–146. SHA-256: `4ff2ec7de10554a694f3ea57df534c3ff8989a23f595e1619170d6bfab69273a`.
- Cass R. Sunstein, *Legal Reasoning and Political Conflict*, Oxford University Press, 1996: уровень абстракции и минимализм, PDF 50–52, 67–71 / с. 37–39, 54–58; аналогия, PDF 75–80, 85 / с. 62–67, 72. SHA-256: `a77026092903f32010be99d28e04825353b87b9436fc6d6943f3668a4a27cba1`.
- Frederick Schauer, *Playing by the Rules*, Clarendon Press, 1991: under/over-inclusion, PDF 47–50, 93–104 / с. 31–34, 77–88; rule error и institutional allocation, PDF 165–166, 174–175 / с. 149–150, 158–159. SHA-256: `93cc3f09acd5bc68e25383895d93d8fce81d509abc646eee01334927930e65de`.
- Ronald Dworkin, *Taking Rights Seriously*, 1977/1978, использованное переиздание 1996: rules/principles, PDF 42–44 / с. 24–26; hard cases, PDF 99–100, 105, 131 / с. 81–82, 87, 113. SHA-256: `eb0e1e0cdf1ce46e65b97813816879ff27bd62b3121a782e95755be346ea968f`.
- Frederick Schauer, *Thinking Like a Lawyer*, Harvard University Press, 2009: holding/dicta/analogy, PDF 71–74, 84, 102–113 / с. 54–57, 67, 85–96; fact, burden и deference, PDF 229, 236–246 / с. 212, 219–229. SHA-256: `a322bc1144709ed336848a4372e4514e6fcec59b7790f5765f52ee075c0cf860`.
- Massimo La Torre, *Constitutionalism and Legal Reasoning*, Springer, 2007: reconstruction и предел риторики, PDF 60, 64–66 / с. 45, 49–51; application/justification/policy, PDF 179, 183 / с. 164, 168. SHA-256: `886ad28be13638fbfca38b19237c8b977fd3b725484086df12f13afd74d81085`.
- Aharon Barak, *Purposive Interpretation in Law*, Princeton University Press, 2005: purpose и semantic anchor, PDF 131–133, 169, 203–205, 391–405 / с. 110–112, 148, 182–184, 370–384. SHA-256: `e73bae5e15d2071452fb2892809833561a0d56c7b731cabe2a2745dfce8e1d9a`.
- Pierre Schlag, Amy J. Griffin, *How to Do Things with Legal Doctrine*, University of Chicago Press, 2020: frames, печ. с. 31–54 / PDF 40–63; baselines, с. 55–72 / PDF 64–81; legal distinctions, с. 73–99 / PDF 82–108; rules/standards, с. 100–118 / PDF 109–127; regime conflicts, с. 119–137 / PDF 128–146; contexts of interpretation, с. 138–157 / PDF 147–166. У файла отсутствует пригодный текстовый слой; locators сверены визуально и по OCR и используются только для critic-прохода.
- Giorgio Bongiovanni, Giovanni Sartor, Chiara Valentini (eds.), *Reasonableness and Law*, Springer, 2009: вводная карта значений, печ. с. xi–xvii / PDF 11–17; Robert Alexy, с. 5–15 / PDF 20–30; Giovanni Sartor, с. 17–68 / PDF 31–82; Alec Stone Sweet и Jud Mathews, с. 173–214 / PDF 182–223; Andrea Morrone, с. 215–242 / PDF 224–250; Ariel Porat, с. 243–254 / PDF 251–260. Из-за пропущенных пустых страниц нет единого стабильного offset; это неоднородные сравнительные модели, а не единый тест.
- Gustav Radbruch, *Философия права*, пер. Ю. М. Юмашева, Международные отношения, 2004, ISBN `5-7133-1197-X`; исходная Studienausgabe под ред. Ralf Dreier и Stanley L. Paulson, C. F. Müller, 1999: антиномии justice/purposiveness/legal certainty и validity — печ. с. 86–101; логика — 127–140; Rechtsstaat — 198–204; *Five Minutes* и statutory injustice/supra-statutory law — 225–239. Источник — legacy `.doc`, SHA-256 `cde4619d8f8214c4053fbd4fdf8953871d4154c13459e0671ace9c81d1487fc8`; для inspection использован производный PDF с картой `derived PDF = print + 1`, соответственно 87–102, 128–141, 199–205 и 226–240. Производный PDF не является новым authority. Статус — `foreign_legal_philosophy_critic_only`: формула Радбруха не устанавливает российский тест недействительности, неприменения, компетенции, допустимости или remedy.

Все источники — `secondary_comparative_methodology`. Их locator проверяет авторский тезис, но не подтверждает российское право, полномочие КС РФ или исход дела.
