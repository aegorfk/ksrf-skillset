# Проверенный сравнительный и red-team корпус конституционной методологии

Срез: **2026-08-15**. В этом файле — 84 source/legal-reviewed карточки, которые не прошли в поведенческие правила: `revise` или `comparative_only`.

## Содержание

- [Статус использования](#статус-использования)
- [Индекс по маршрутам](#индекс-по-маршрутам)
- [Карточки](#карточки)

## Статус использования

**Не является новой обязательной инструкцией.** Используй карточки только для генерации вариантов, контрпримеров, вопросов проверки и границ переноса. Российское право, компетенцию, допустимость и средство защиты каждый раз подтверждай актуальными официальными источниками. Ни одна запись ниже не имеет human approval и не разрешает promotion.

Текст намеренно не воспроизводит длинные цитаты. Для аудита даны работа, точный locator, source-review и legal-review; дословную цитату открывай в effective card и первичном источнике.

## Индекс по маршрутам

| KSRF skill | Карточек | Card IDs |
| --- | ---: | --- |
| `ksrf-argument-patterns` | 59 | [`cmc-khabrieva-interpretive-stages-06`](#cmc-khabrieva-interpretive-stages-06), [`cmc-khabrieva-interpretive-boundary-07`](#cmc-khabrieva-interpretive-boundary-07), [`cmc-kokotov-trust-functions-01`](#cmc-kokotov-trust-functions-01), [`cmc-kokotov-trust-context-02`](#cmc-kokotov-trust-context-02), [`cmc-kokotov-trust-aspects-03`](#cmc-kokotov-trust-aspects-03), [`cmc-sunstein-interpretive-choice-01`](#cmc-sunstein-interpretive-choice-01), [`cmc-sunstein-interpretive-boundary-02`](#cmc-sunstein-interpretive-boundary-02), [`cmc-sunstein-formalism-qa-03`](#cmc-sunstein-formalism-qa-03), [`cmc-barak-four-components-01`](#cmc-barak-four-components-01), [`cmc-barak-scope-before-justification-02`](#cmc-barak-scope-before-justification-02), [`cmc-barak-interpretive-balancing-03`](#cmc-barak-interpretive-balancing-03), [`cmc-barak-justification-culture-04`](#cmc-barak-justification-culture-04), [`cmc-barak-conflicting-rights-level-05`](#cmc-barak-conflicting-rights-level-05), [`cmc-dworkin-preexisting-rights-01`](#cmc-dworkin-preexisting-rights-01), [`cmc-dworkin-principle-policy-02`](#cmc-dworkin-principle-policy-02), [`cmc-dworkin-history-morality-03`](#cmc-dworkin-history-morality-03), [`cmc-dworkin-precedent-gravity-04`](#cmc-dworkin-precedent-gravity-04), [`cmc-dworkin-coherent-justification-05`](#cmc-dworkin-coherent-justification-05), [`cmc-dworkin-institutional-mistakes-06`](#cmc-dworkin-institutional-mistakes-06), [`cmc-dworkin-judicial-humility-07`](#cmc-dworkin-judicial-humility-07), [`cmc-bondar-multidimensional-constitutionalism-01`](#cmc-bondar-multidimensional-constitutionalism-01), [`cmc-bondar-constitutional-realism-02`](#cmc-bondar-constitutional-realism-02), [`cmc-bondar-methodological-pluralism-03`](#cmc-bondar-methodological-pluralism-03), [`cmc-bondar-living-constitutionalism-04`](#cmc-bondar-living-constitutionalism-04), [`cmc-bondar-judicial-constitutionalism-conditions-06`](#cmc-bondar-judicial-constitutionalism-conditions-06), [`cmc-bondar-sociocultural-context-08`](#cmc-bondar-sociocultural-context-08), [`cmc-joint-social-right-definiteness-01`](#cmc-joint-social-right-definiteness-01), [`cmc-joint-social-program-not-right-02`](#cmc-joint-social-program-not-right-02), [`cmc-joint-social-resource-revision-03`](#cmc-joint-social-resource-revision-03), [`cmc-joint-social-rights-heterogeneity-04`](#cmc-joint-social-rights-heterogeneity-04), [`cmc-vitruk-echr-nonautomatic-use-01`](#cmc-vitruk-echr-nonautomatic-use-01), [`cmc-vitruk-effect-execution-distinction-02`](#cmc-vitruk-effect-execution-distinction-02), [`cmc-brezhnev-combined-dispute-test-01`](#cmc-brezhnev-combined-dispute-test-01), [`cmc-varlamova-conceptual-baseline-01`](#cmc-varlamova-conceptual-baseline-01), [`cmc-varlamova-rights-guarantee-fit-02`](#cmc-varlamova-rights-guarantee-fit-02), [`cmc-kryazhkov-ideal-empirical-institution-01`](#cmc-kryazhkov-ideal-empirical-institution-01), [`cmc-kryazhkov-nonhierarchical-competence-02`](#cmc-kryazhkov-nonhierarchical-competence-02), [`cmc-gritsenko-comparative-reception-gate-01`](#cmc-gritsenko-comparative-reception-gate-01), [`cmc-gritsenko-contextual-option-generation-02`](#cmc-gritsenko-contextual-option-generation-02), [`cmc-kumm-comella-institutional-doctrines-01`](#cmc-kumm-comella-institutional-doctrines-01), [`cmc-kumm-comella-normative-issues-hidden-02`](#cmc-kumm-comella-normative-issues-hidden-02), [`cmc-kumm-comella-function-before-transfer-03`](#cmc-kumm-comella-function-before-transfer-03), [`cmc-schauer-precedent-not-analogy-01`](#cmc-schauer-precedent-not-analogy-01), [`cmc-schauer-source-choice-test-02`](#cmc-schauer-source-choice-test-02), [`cmc-schauer-second-order-values-03`](#cmc-schauer-second-order-values-03), [`cmc-sajo-self-defense-paradox-01`](#cmc-sajo-self-defense-paradox-01), [`cmc-sajo-anti-abuse-conditions-02`](#cmc-sajo-anti-abuse-conditions-02), [`cmc-sajo-context-minimum-impairment-03`](#cmc-sajo-context-minimum-impairment-03), [`cmc-garlicki-integrated-interpretation-01`](#cmc-garlicki-integrated-interpretation-01), [`cmc-garlicki-systemic-tension-02`](#cmc-garlicki-systemic-tension-02), [`cmc-garlicki-dialogue-persuasion-04`](#cmc-garlicki-dialogue-persuasion-04), [`cmc-scalia-rules-equality-predictability-01`](#cmc-scalia-rules-equality-predictability-01), [`cmc-scalia-rules-constrain-judges-02`](#cmc-scalia-rules-constrain-judges-02), [`cmc-scalia-rules-limit-03`](#cmc-scalia-rules-limit-03), [`cmc-habermas-cooriginal-autonomy-01`](#cmc-habermas-cooriginal-autonomy-01), [`cmc-habermas-constitution-project-02`](#cmc-habermas-constitution-project-02), [`cmc-habermas-rights-two-stages-03`](#cmc-habermas-rights-two-stages-03), [`cmc-kelsen-general-annulment-01`](#cmc-kelsen-general-annulment-01), [`cmc-kelsen-indirect-review-public-interest-03`](#cmc-kelsen-indirect-review-public-interest-03) |
| `ksrf-case-triage` | 9 | [`cmc-morshchakova-remedy-complementarity-02`](#cmc-morshchakova-remedy-complementarity-02), [`cmc-morshchakova-procedural-fairness-03`](#cmc-morshchakova-procedural-fairness-03), [`cmc-joint-social-right-definiteness-01`](#cmc-joint-social-right-definiteness-01), [`cmc-joint-social-program-not-right-02`](#cmc-joint-social-program-not-right-02), [`cmc-joint-social-resource-revision-03`](#cmc-joint-social-resource-revision-03), [`cmc-joint-social-rights-heterogeneity-04`](#cmc-joint-social-rights-heterogeneity-04), [`cmc-brezhnev-combined-dispute-test-01`](#cmc-brezhnev-combined-dispute-test-01), [`cmc-kelsen-general-annulment-01`](#cmc-kelsen-general-annulment-01), [`cmc-kelsen-indirect-review-public-interest-03`](#cmc-kelsen-indirect-review-public-interest-03) |
| `ksrf-complaint-cycle` | 1 | [`cmc-mityukov-multifactor-execution-02`](#cmc-mityukov-multifactor-execution-02) |
| `ksrf-complaint-qa` | 21 | [`cmc-sunstein-interpretive-choice-01`](#cmc-sunstein-interpretive-choice-01), [`cmc-sunstein-interpretive-boundary-02`](#cmc-sunstein-interpretive-boundary-02), [`cmc-sunstein-formalism-qa-03`](#cmc-sunstein-formalism-qa-03), [`cmc-joint-social-right-definiteness-01`](#cmc-joint-social-right-definiteness-01), [`cmc-joint-social-program-not-right-02`](#cmc-joint-social-program-not-right-02), [`cmc-joint-social-resource-revision-03`](#cmc-joint-social-resource-revision-03), [`cmc-joint-social-rights-heterogeneity-04`](#cmc-joint-social-rights-heterogeneity-04), [`cmc-luebbe-wolff-universal-core-01`](#cmc-luebbe-wolff-universal-core-01), [`cmc-luebbe-wolff-rights-corridor-02`](#cmc-luebbe-wolff-rights-corridor-02), [`cmc-moller-four-stage-test-01`](#cmc-moller-four-stage-test-01), [`cmc-moller-all-relevant-factors-02`](#cmc-moller-all-relevant-factors-02), [`cmc-moller-structured-ethical-reasoning-03`](#cmc-moller-structured-ethical-reasoning-03), [`cmc-schauer-precedent-not-analogy-01`](#cmc-schauer-precedent-not-analogy-01), [`cmc-schauer-source-choice-test-02`](#cmc-schauer-source-choice-test-02), [`cmc-schauer-second-order-values-03`](#cmc-schauer-second-order-values-03), [`cmc-sajo-self-defense-paradox-01`](#cmc-sajo-self-defense-paradox-01), [`cmc-sajo-anti-abuse-conditions-02`](#cmc-sajo-anti-abuse-conditions-02), [`cmc-sajo-context-minimum-impairment-03`](#cmc-sajo-context-minimum-impairment-03), [`cmc-scalia-rules-equality-predictability-01`](#cmc-scalia-rules-equality-predictability-01), [`cmc-scalia-rules-constrain-judges-02`](#cmc-scalia-rules-constrain-judges-02), [`cmc-scalia-rules-limit-03`](#cmc-scalia-rules-limit-03) |
| `ksrf-decision-execution` | 9 | [`cmc-bondar-multidimensional-constitutionalism-01`](#cmc-bondar-multidimensional-constitutionalism-01), [`cmc-bondar-constitutional-realism-02`](#cmc-bondar-constitutional-realism-02), [`cmc-bondar-methodological-pluralism-03`](#cmc-bondar-methodological-pluralism-03), [`cmc-bondar-living-constitutionalism-04`](#cmc-bondar-living-constitutionalism-04), [`cmc-bondar-judicial-constitutionalism-conditions-06`](#cmc-bondar-judicial-constitutionalism-conditions-06), [`cmc-bondar-sociocultural-context-08`](#cmc-bondar-sociocultural-context-08), [`cmc-dzhagaryan-act-specific-quality-01`](#cmc-dzhagaryan-act-specific-quality-01), [`cmc-kryazhkov-ideal-empirical-institution-01`](#cmc-kryazhkov-ideal-empirical-institution-01), [`cmc-mityukov-multifactor-execution-02`](#cmc-mityukov-multifactor-execution-02) |
| `ksrf-echr-argumentation` | 17 | [`cmc-morshchakova-remedy-complementarity-02`](#cmc-morshchakova-remedy-complementarity-02), [`cmc-morshchakova-procedural-fairness-03`](#cmc-morshchakova-procedural-fairness-03), [`cmc-jackson-sequenced-proportionality-01`](#cmc-jackson-sequenced-proportionality-01), [`cmc-jackson-transparent-reasons-02`](#cmc-jackson-transparent-reasons-02), [`cmc-jackson-institutional-bridge-03`](#cmc-jackson-institutional-bridge-03), [`cmc-jackson-disproportion-process-failure-04`](#cmc-jackson-disproportion-process-failure-04), [`cmc-jackson-nonmetric-judgment-05`](#cmc-jackson-nonmetric-judgment-05), [`cmc-jackson-boundaries-text-rights-06`](#cmc-jackson-boundaries-text-rights-06), [`cmc-vitruk-echr-nonautomatic-use-01`](#cmc-vitruk-echr-nonautomatic-use-01), [`cmc-vitruk-effect-execution-distinction-02`](#cmc-vitruk-effect-execution-distinction-02), [`cmc-gritsenko-comparative-reception-gate-01`](#cmc-gritsenko-comparative-reception-gate-01), [`cmc-gritsenko-contextual-option-generation-02`](#cmc-gritsenko-contextual-option-generation-02), [`cmc-vaipan-cyclic-proportionality-01`](#cmc-vaipan-cyclic-proportionality-01), [`cmc-vaipan-proportionality-open-challenge-02`](#cmc-vaipan-proportionality-open-challenge-02), [`cmc-garlicki-integrated-interpretation-01`](#cmc-garlicki-integrated-interpretation-01), [`cmc-garlicki-systemic-tension-02`](#cmc-garlicki-systemic-tension-02), [`cmc-garlicki-dialogue-persuasion-04`](#cmc-garlicki-dialogue-persuasion-04) |
| `ksrf-formal-filing-check` | 4 | [`cmc-joint-social-right-definiteness-01`](#cmc-joint-social-right-definiteness-01), [`cmc-joint-social-program-not-right-02`](#cmc-joint-social-program-not-right-02), [`cmc-joint-social-resource-revision-03`](#cmc-joint-social-resource-revision-03), [`cmc-joint-social-rights-heterogeneity-04`](#cmc-joint-social-rights-heterogeneity-04) |
| `ksrf-rights-argument-builder` | 51 | [`cmc-kokotov-trust-functions-01`](#cmc-kokotov-trust-functions-01), [`cmc-kokotov-trust-context-02`](#cmc-kokotov-trust-context-02), [`cmc-kokotov-trust-aspects-03`](#cmc-kokotov-trust-aspects-03), [`cmc-barak-four-components-01`](#cmc-barak-four-components-01), [`cmc-barak-scope-before-justification-02`](#cmc-barak-scope-before-justification-02), [`cmc-barak-interpretive-balancing-03`](#cmc-barak-interpretive-balancing-03), [`cmc-barak-justification-culture-04`](#cmc-barak-justification-culture-04), [`cmc-barak-conflicting-rights-level-05`](#cmc-barak-conflicting-rights-level-05), [`cmc-jackson-sequenced-proportionality-01`](#cmc-jackson-sequenced-proportionality-01), [`cmc-jackson-transparent-reasons-02`](#cmc-jackson-transparent-reasons-02), [`cmc-jackson-institutional-bridge-03`](#cmc-jackson-institutional-bridge-03), [`cmc-jackson-disproportion-process-failure-04`](#cmc-jackson-disproportion-process-failure-04), [`cmc-jackson-nonmetric-judgment-05`](#cmc-jackson-nonmetric-judgment-05), [`cmc-jackson-boundaries-text-rights-06`](#cmc-jackson-boundaries-text-rights-06), [`cmc-dworkin-preexisting-rights-01`](#cmc-dworkin-preexisting-rights-01), [`cmc-dworkin-principle-policy-02`](#cmc-dworkin-principle-policy-02), [`cmc-dworkin-history-morality-03`](#cmc-dworkin-history-morality-03), [`cmc-dworkin-precedent-gravity-04`](#cmc-dworkin-precedent-gravity-04), [`cmc-dworkin-coherent-justification-05`](#cmc-dworkin-coherent-justification-05), [`cmc-dworkin-institutional-mistakes-06`](#cmc-dworkin-institutional-mistakes-06), [`cmc-dworkin-judicial-humility-07`](#cmc-dworkin-judicial-humility-07), [`cmc-bondar-multidimensional-constitutionalism-01`](#cmc-bondar-multidimensional-constitutionalism-01), [`cmc-bondar-constitutional-realism-02`](#cmc-bondar-constitutional-realism-02), [`cmc-bondar-methodological-pluralism-03`](#cmc-bondar-methodological-pluralism-03), [`cmc-bondar-living-constitutionalism-04`](#cmc-bondar-living-constitutionalism-04), [`cmc-bondar-judicial-constitutionalism-conditions-06`](#cmc-bondar-judicial-constitutionalism-conditions-06), [`cmc-bondar-sociocultural-context-08`](#cmc-bondar-sociocultural-context-08), [`cmc-troitskaya-four-stage-test-01`](#cmc-troitskaya-four-stage-test-01), [`cmc-troitskaya-zero-stage-scope-02`](#cmc-troitskaya-zero-stage-scope-02), [`cmc-troitskaya-cautious-right-limits-03`](#cmc-troitskaya-cautious-right-limits-03), [`cmc-troitskaya-absolute-right-04`](#cmc-troitskaya-absolute-right-04), [`cmc-troitskaya-three-zones-qa-05`](#cmc-troitskaya-three-zones-qa-05), [`cmc-varlamova-conceptual-baseline-01`](#cmc-varlamova-conceptual-baseline-01), [`cmc-varlamova-rights-guarantee-fit-02`](#cmc-varlamova-rights-guarantee-fit-02), [`cmc-lapaeva-conventional-standards-audit-02`](#cmc-lapaeva-conventional-standards-audit-02), [`cmc-dzhagaryan-act-specific-quality-01`](#cmc-dzhagaryan-act-specific-quality-01), [`cmc-vaipan-cyclic-proportionality-01`](#cmc-vaipan-cyclic-proportionality-01), [`cmc-vaipan-proportionality-open-challenge-02`](#cmc-vaipan-proportionality-open-challenge-02), [`cmc-luebbe-wolff-universal-core-01`](#cmc-luebbe-wolff-universal-core-01), [`cmc-luebbe-wolff-rights-corridor-02`](#cmc-luebbe-wolff-rights-corridor-02), [`cmc-alexy-balancing-stages-01`](#cmc-alexy-balancing-stages-01), [`cmc-alexy-reasoned-representation-02`](#cmc-alexy-reasoned-representation-02), [`cmc-moller-four-stage-test-01`](#cmc-moller-four-stage-test-01), [`cmc-moller-all-relevant-factors-02`](#cmc-moller-all-relevant-factors-02), [`cmc-moller-structured-ethical-reasoning-03`](#cmc-moller-structured-ethical-reasoning-03), [`cmc-kumm-comella-institutional-doctrines-01`](#cmc-kumm-comella-institutional-doctrines-01), [`cmc-kumm-comella-normative-issues-hidden-02`](#cmc-kumm-comella-normative-issues-hidden-02), [`cmc-kumm-comella-function-before-transfer-03`](#cmc-kumm-comella-function-before-transfer-03), [`cmc-habermas-cooriginal-autonomy-01`](#cmc-habermas-cooriginal-autonomy-01), [`cmc-habermas-constitution-project-02`](#cmc-habermas-constitution-project-02), [`cmc-habermas-rights-two-stages-03`](#cmc-habermas-rights-two-stages-03) |

## Карточки

<a id="cmc-khabrieva-interpretive-stages-06"></a>
### `cmc-khabrieva-interpretive-stages-06` — Талия Ярулловна Хабриева

- **Работа и locator:** Избранные труды. Том 2: Правовая охрана Конституции (извлечение); печат. 163–164; PDF 165–166; раздел Правовая охрана Конституции, гл. VI, § 3.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Интерпретационный меморандум должен иметь три отдельных доказательных слоя: концепция, юридическая конструкция и фактическое действие.
- **Когда полезна:** Стороны предлагают конкурирующие толкования нормы или её смысл изменился в практике.
- **Предусловия:** Доступны текст и история нормы.; Есть материалы применения и контекст регулируемых отношений.
- **Остановиться или воздержаться:** Фактическое действие нормы утверждается без материалов практики.; Конкурирующая позиция скрыта или представлена карикатурно.
- **Оговорки источника:** Автор отличает эти материальные стадии от процессуальных стадий производства.; Термин «идеология» используется как выявление концептуальных позиций и аргументов.
- **Источник не доказывает:** Историческая воля законодателя всегда имеет решающее значение.; Любой из трёх блоков сам по себе достаточен для итогового толкования.
- **Фальсификаторы и пределы переноса:** Официальный обязательный смысл может ограничивать пространство доктринальной интерпретации.; Новые социальные обстоятельства не разрешают переписать ясный текст без правового основания.
- **Контрпример:** Вывод о смысле нормы основан только на словарном значении одного слова и игнорирует систему и практику.
- **Не использовать для:** Не подменять толкование политическим предпочтением.; Не считать социальный эффект самостоятельным источником полномочий.
- **Российская правовая граница:** Российский закон прямо поддерживает системное сопоставление текста, толкований и практики, то есть часть предлагаемого метода. Он не закрепляет автономную стадию концептуальной реконструкции или социально-эмпирической оценки и не требует фиксированной последовательности. Пределы: Трехчастная схема остается авторской организацией материала, а не обязательным тестом российского права.; Фактическое действие нормы должно подтверждаться репрезентативными материалами и не позволяет переписать ясный текст.; Предмет и допустимость конкретного дела определяются отдельно.
- **Маршруты:** ksrf-argument-patterns.
- **Provenance:** source review `source-review-a-cmc-khabrieva-interpretive-stages-06`; legal review `legal-anchor-a-r1-006`; source SHA-256 `5a704506bb62e4c3aa92a86ff01e2ffcce3ca3dd4517e091a14fa77dadb581ce`.

<a id="cmc-khabrieva-interpretive-boundary-07"></a>
### `cmc-khabrieva-interpretive-boundary-07` — Талия Ярулловна Хабриева

- **Работа и locator:** Избранные труды. Том 2: Правовая охрана Конституции (извлечение); печат. 165–166; PDF 167–168; раздел Правовая охрана Конституции, гл. VI, § 4.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Каждый интерпретационный вывод следует проверять на текстовую и системную опору и отдельно отмечать добавленные компилятором нормативные посылки.
- **Когда полезна:** Предлагаемое толкование заметно расширяет обязанность, запрет или полномочие по сравнению с текстом.
- **Предусловия:** Зафиксирован текст нормы.; Явно названы используемые цели, принципы и системные связи.
- **Остановиться или воздержаться:** Вывод не имеет идентифицируемой опоры в правовом материале.; Для результата требуется создать новое полномочие или обязанность.
- **Оговорки источника:** Автор допускает особые свойства нормативного толкования Конституции, но сохраняет запрет подмены законодателя.; Граница между раскрытием и созданием смысла может быть спорной.
- **Источник не доказывает:** Целевое толкование всегда недопустимо.; Любое развитие смысла старого текста является созданием новой нормы.
- **Фальсификаторы и пределы переноса:** Общий и абстрактный текст неизбежно оставляет пространство конкретизации.; Официальная практика может признать динамическое толкование допустимым в конкретных пределах.
- **Контрпример:** Из общей цели защиты порядка выводится новый состав запрета, которого нет ни в тексте, ни в системных связях нормы.
- **Не использовать для:** Не запрещать телеологическое толкование как таковое.; Не выдавать собственную рекомендацию за смысл источника.
- **Российская правовая граница:** Перенос квалифицирован: ст. 74 1-ФКЗ задает источники реконструкции примененного смысла, а точный фрагмент 12-П показывает одну предметно ограниченную зону законодательного выбора. 12-П касается налоговой ответственности, поэтому его нельзя превращать в универсальную границу всякого толкования; card остается revise-only QA rule. Пределы: Нельзя выводить из метода запрет КС РФ на обязательную конституционно-правовую конкретизацию нормы.; Телеологический аргумент не является сам по себе недопустимым по действующему праву.; Любой вывод о подмене законодателя требует проверки конкретной компетенции и решения.
- **Маршруты:** ksrf-argument-patterns.
- **Provenance:** source review `source-review-a-cmc-khabrieva-interpretive-boundary-07`; legal review `legal-anchor-a-r1-007-r2`; source SHA-256 `5a704506bb62e4c3aa92a86ff01e2ffcce3ca3dd4517e091a14fa77dadb581ce`.

<a id="cmc-morshchakova-remedy-complementarity-02"></a>
### `cmc-morshchakova-remedy-complementarity-02` — Тамара Георгиевна Морщакова

- **Работа и locator:** Конституционная защита прав и свобод граждан судами Российской Федерации; печат. 124–125; PDF 125–126; раздел О взаимодополняемости уровней судебной защиты.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Стратегию защиты нужно строить по функциям средств и точкам их подключения, показывая, какой дефект способен исправить каждый уровень.
- **Когда полезна:** В деле участвуют несколько судебных уровней или рассматривается наднациональный аргумент.
- **Предусловия:** Известна процессуальная история дела.; Определены дефекты и возможные способы их устранения.
- **Остановиться или воздержаться:** Последовательность строится по статье 2004 года без актуальной правовой проверки.; Неизвестны сроки или процессуальный статус дела.
- **Оговорки источника:** Институциональная карта статьи отражает устройство 2004 года.; Последовательность средств определяется актуальным процессуальным правом.
- **Источник не доказывает:** Все уровни защиты доступны в каждом конкретном деле.; Обращение к одной юрисдикции автоматически исчерпывает остальные средства.
- **Фальсификаторы и пределы переноса:** Некоторые средства могут быть взаимоисключающими или недоступными.; Изменение международных обязательств может радикально менять карту.
- **Контрпример:** Два последующих обращения повторяют один и тот же довод в органы, которые не вправе устранить выявленный нормативный дефект.
- **Не использовать для:** Не обещать доступ к наднациональной юрисдикции.; Не создавать искусственные этапы исчерпания.
- **Российская правовая граница:** Официальное право подтверждает множественность средств и конкретные правила исчерпания, но не устанавливает единую универсальную систему «взаимодополняемости» всех юрисдикций. Карта пригодна после полной пересборки по актуальным процессуальным нормам. Пределы: Не каждое доступное средство обязательно к исчерпанию; критерий зависит от соответствующего производства.; Межгосударственное обращение возможно только в соответствии с действующим для Российской Федерации международным договором.; Сроки, параллельность и взаимоисключение средств проверяются по отраслевому процессуальному закону, а не по статье 2004 года.
- **Маршруты:** ksrf-case-triage; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-a-cmc-morshchakova-remedy-complementarity-02`; legal review `legal-anchor-a-r1-009-r2`; source SHA-256 `8ea8b5deefec7f3325fe45cbbcbd2d01a0ad6e1bf3d6ad0319b3bc4ae73605c4`.

<a id="cmc-morshchakova-procedural-fairness-03"></a>
### `cmc-morshchakova-procedural-fairness-03` — Тамара Георгиевна Морщакова

- **Работа и locator:** Конституционная защита прав и свобод граждан судами Российской Федерации; печат. 125–126; PDF 126–127; раздел О процессуальной справедливости.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** В анализе дела нужно вести отдельную линию процессуального вреда, не растворяя её в споре о правильности материального результата.
- **Когда полезна:** Заявитель получил неблагоприятное решение и указывает на отсутствие равенства, независимости, беспристрастности или возможности быть услышанным.
- **Предусловия:** Есть процессуальная хронология и судебные акты.; Назван конкретный процедурный дефект.
- **Остановиться или воздержаться:** Претензия сводится к несогласию с оценкой доказательств.; Не установлена применимая официальная гарантия.
- **Оговорки источника:** Самостоятельная ценность процедуральной справедливости сначала представлена как положение немецкой теории, которое автор использует в собственном рассуждении.; Статья связывает содержание процессуальной справедливости с международными стандартами своего времени.; Не каждое процессуальное нарушение достигает конституционного уровня.
- **Источник не доказывает:** Материально правильное решение всегда подлежит отмене при любом процедурном дефекте.; Доктрина сама устанавливает конкретный набор обязательных гарантий.
- **Фальсификаторы и пределы переноса:** Несущественная техническая ошибка без воздействия на возможность защиты может не образовать конституционного вреда.; Официальный стандарт может требовать доказать дополнительные условия.
- **Контрпример:** Опечатка в промежуточном уведомлении исправлена до заседания и не ограничила участие стороны.
- **Не использовать для:** Не обещать отмену решения за любой дефект.; Не смешивать процессуальную справедливость с желаемым исходом.
- **Российская правовая граница:** Конституция подтверждает самостоятельную ценность конкретных процессуальных гарантий и позволяет отделять процедурную линию от материального исхода. Однако официальный стандарт зависит от названной гарантии, существенности дефекта и отраслевого средства, поэтому универсальная матрица лишь организационная. Пределы: Техническая ошибка без реального ограничения гарантии не становится автоматически конституционным вредом.; В жалобе в КС РФ требуется нормативный дефект или устойчивый нормативный смысл, а не только нарушение процедуры в единичном деле.; Способ исправления определяется соответствующим процессуальным кодексом и компетенцией суда.
- **Маршруты:** ksrf-case-triage; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-a-r1-03`; legal review `legal-anchor-a-r1-010-r2`; source SHA-256 `8ea8b5deefec7f3325fe45cbbcbd2d01a0ad6e1bf3d6ad0319b3bc4ae73605c4`.

<a id="cmc-kokotov-trust-functions-01"></a>
### `cmc-kokotov-trust-functions-01` — Александр Николаевич Кокотов

- **Работа и locator:** Конституционный принцип доверия в практике Конституционного Суда Российской Федерации; печат. 100; PDF 102; раздел Доверие как конституционный принцип.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Аргумент о доверии следует разложить по заявленной функции: идеал, цель, метод регулирования или критерий оценки, а затем связать выбранную функцию с конкретным дефектом нормы.
- **Когда полезна:** В материалах дела заявляется подрыв доверия к закону или действиям государства.
- **Предусловия:** Определено конкретное регулирование, повлиявшее на положение заявителя.; Описано, какое отношение доверия и каким образом затронуто.
- **Остановиться или воздержаться:** Невозможно назвать конкретную функцию принципа доверия.; Аргумент основан только на общем падении общественного доверия без связи с делом.
- **Оговорки источника:** Автор помечает функциональную классификацию оговоркой «как видится».; Тезис относится к отношениям, основанным на доверии и недоверии.
- **Источник не доказывает:** Классификация сама по себе не устанавливает самостоятельное основание допустимости жалобы в КС РФ.; Она не доказывает, что любое снижение доверия означает неконституционность нормы.
- **Фальсификаторы и пределы переноса:** Если правовое ожидание заявителя не подтверждено материалами дела, аргумент о доверии ослабевает.; Отсутствие конкретного дефекта нормы не компенсируется ссылкой на социальный эффект.
- **Контрпример:** Непопулярное решение органа власти может снижать доверие, но это само по себе не выявляет дефект примененной нормы.
- **Не использовать для:** Не превращать доверие в самостоятельное гарантированное право.; Не объявлять неконституционным любое неблагоприятное изменение.
- **Российская правовая граница:** Российская практика закрепляет более узкое юридическое содержание доверия — стабильность, предсказуемость, защиту прав и адаптацию. Она не превращает четыре функции Кокотова в обязательный тест, поэтому использовать можно лишь с переводом каждой категории в конкретный официальный критерий. Пределы: Четыре функции — доктринальная классификация, не источник компетенции или самостоятельного средства защиты.; Доверие не заменяет доказательство нарушения конкретного права или дефекта нормы.; Для правила следует оставить только официально подтвержденные элементы: определенность, стабильность, предсказуемость, защита приобретенных прав и переходные гарантии.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-a-cmc-kokotov-trust-functions-01`; legal review `legal-anchor-a-r1-012-r2`; source SHA-256 `1a644fa7525956619feacc7aa47fb08c92b865b600d6e298a5132f25cc295262`.

<a id="cmc-kokotov-trust-context-02"></a>
### `cmc-kokotov-trust-context-02` — Александр Николаевич Кокотов

- **Работа и locator:** Конституционный принцип доверия в практике Конституционного Суда Российской Федерации; печат. 100–101; PDF 102–103; раздел Доверие как конституционный принцип.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При доводе о доверии нужно показать механизм, по которому норма или устойчивая практика меняет отношения граждан и власти, и не ограничиваться декларацией о негативном общественном фоне.
- **Когда полезна:** Довод заявителя опирается на подрыв доверия, легитимности или устойчивости правопорядка.
- **Предусловия:** Есть конкретный нормативный механизм или устойчивая практика.; Определена затронутая группа и отношение с публичной властью.
- **Остановиться или воздержаться:** Социальный эффект выводится без фактов или механизма.; Аргумент не связан с правовым положением заявителя.
- **Оговорки источника:** Автор говорит об общностном доверии и макросоциальном контексте, а не о непосредственном измерении индивидуального права.; Отдельное решение может быть значимо как отрицательный прецедент или элемент накопленной тенденции.
- **Источник не доказывает:** Тезис не дает способа количественно измерить изменение доверия.; Он не доказывает причинную связь между одной нормой и общесоциальным недоверием.
- **Фальсификаторы и пределы переноса:** Разовая ошибка без нормативного или повторяемого основания не подтверждает макросоциальный вывод.; Контрданные о стабильном и предсказуемом применении требуют сузить тезис.
- **Контрпример:** Единичная задержка ответа органа неудобна заявителю, но без повторяемости и нормативной причины не доказывает подрыв общностного доверия.
- **Не использовать для:** Не заменять юридический анализ социологическим утверждением.; Не приписывать обществу единое недоверие без доказательств.
- **Российская правовая граница:** Официальный anchor поддерживает требование показать воздействие регулирования на юридически значимые ожидания конкретных участников. Более широкий макросоциальный и психологический контекст Кокотова не является самостоятельным действующим тестом и требует доказательств. Пределы: Недоверие как настроение общества не заменяет нормативный дефект и нарушение права заявителя.; Разовая ошибка без устойчивого нормативного смысла не подтверждает изменение отношений граждан и власти.; Макросоциальные последствия должны подтверждаться надежными данными и оставаться вспомогательными.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-a-cmc-kokotov-trust-context-02`; legal review `legal-anchor-a-r1-013-r2`; source SHA-256 `1a644fa7525956619feacc7aa47fb08c92b865b600d6e298a5132f25cc295262`.

<a id="cmc-kokotov-trust-aspects-03"></a>
### `cmc-kokotov-trust-aspects-03` — Александр Николаевич Кокотов

- **Работа и locator:** Конституционный принцип доверия в практике Конституционного Суда Российской Федерации; печат. 103; PDF 105; раздел Содержание конституционного принципа доверия.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Перед формулированием довода нужно классифицировать объект доверия и не смешивать доверие к закону, к публичной власти и к отдельному институту.
- **Когда полезна:** В проекте жалобы используется общий тезис о нарушении принципа доверия.
- **Предусловия:** Известно, чьи ожидания затронуты.; Определен адресат или объект доверия.
- **Остановиться или воздержаться:** Объект доверия нельзя определить из материалов дела.; Разные аспекты сведены в одну формулу без самостоятельных фактов.
- **Оговорки источника:** Это авторская систематизация проанализированной им практики к 2014 году.; Выбор аспекта зависит от особенностей дела и стратегии его анализа.
- **Источник не доказывает:** Перечень не подтвержден как исчерпывающая актуальная классификация КС РФ.; Совпадение слов «доверие» в деле не доказывает применимость каждого аспекта.
- **Фальсификаторы и пределы переноса:** Доверие к конкретному должностному лицу не тождественно доверию к закону или институту.; Факты, относящиеся только к частному субъекту, не подтверждают взаимное доверие граждан и публичной власти.
- **Контрпример:** Спор с коммерческим контрагентом не становится доводом о доверии к публичной власти лишь потому, что его разрешал государственный суд.
- **Не использовать для:** Не смешивать уровни доверия.; Не расширять предмет жалобы через риторическую классификацию.
- **Российская правовая граница:** Официальные решения подтверждают несколько различимых объектов доверия и тем самым поддерживают аналитическое разведение фактов. Они не закрепляют предложенный перечень как исчерпывающую юридическую таксономию и не дают одинаковых последствий для каждого аспекта. Пределы: Доверие к конкретному должностному лицу или частной организации не тождественно доверию к закону и действиям государства.; Таксономия не является самостоятельным основанием допустимости жалобы.; Для каждого объекта требуется показать связь с конкретной нормой, правом и юридически значимым ожиданием.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-a-cmc-kokotov-trust-aspects-03`; legal review `legal-anchor-a-r1-014-r2`; source SHA-256 `1a644fa7525956619feacc7aa47fb08c92b865b600d6e298a5132f25cc295262`.

<a id="cmc-sunstein-interpretive-choice-01"></a>
### `cmc-sunstein-interpretive-choice-01` — Cass R. Sunstein

- **Работа и locator:** Formalism in Constitutional Theory; печат. 1; PDF 2; раздел Abstract and opening paragraph.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** When several readings remain textually plausible, the analysis should disclose the external normative and institutional criteria used to choose among them and compare their consequences.
- **Когда полезна:** Two or more textually plausible readings of a constitutional or statutory provision remain.
- **Предусловия:** Each candidate reading has a defensible textual basis.; Relevant institutional consequences can be identified without inventing facts.
- **Остановиться или воздержаться:** Only one reading is textually plausible.; The preferred reading requires disregarding the text or inventing predicted effects.
- **Оговорки источника:** The claim concerns a choice among interpretations that are already plausible.; The source is framed within constitutional theory associated chiefly with the United States.
- **Источник не доказывает:** The claim does not identify one universally correct interpretive method.; It does not authorize ignoring the constitutional text or institutional limits.
- **Фальсификаторы и пределы переноса:** A reading that lacks textual plausibility fails before consequential comparison.; Material adverse institutional effects may defeat a reading favored on a single value.
- **Контрпример:** A morally attractive outcome cannot qualify as interpretation if the proposed reading has no connection to the text.
- **Не использовать для:** Do not conceal value choices behind definitions.; Do not turn consequence assessment into free-standing moral adjudication.
- **Российская правовая граница:** Российские официальные источники требуют работы с текстом, системой и практикой, но не закрепляют предложенный Санстейном consequentialist-метакритерий. Метод допустим только как прозрачная сравнительная техника, если он не подменяет Конституцию, закон и обязательные позиции КС РФ. Пределы: Благоприятные последствия не делают текстуально или юридически невозможное толкование допустимым.; Внешние ценности должны иметь российскую официальную правовую опору.; Сравнительная техника не определяет компетенцию, допустимость или средство защиты.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-a-cmc-sunstein-interpretive-choice-01`; legal review `legal-anchor-a-r1-016`; source SHA-256 `d80ef044af0c82f38be81cc9f8efe2bd76aad3d017ec1a89f0187dee5430a304`.

<a id="cmc-sunstein-interpretive-boundary-02"></a>
### `cmc-sunstein-interpretive-boundary-02` — Cass R. Sunstein

- **Работа и locator:** Formalism in Constitutional Theory; печат. 1; PDF 2; раздел Opening paragraph.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Interpretive QA should use two separate gates: first exclude candidates detached from the text, then compare the remaining plausible candidates on substantive grounds.
- **Когда полезна:** A proposed argument is defended either as the only possible interpretation or as justified solely by desirable outcomes.
- **Предусловия:** The relevant text and candidate reading are stated.; The analyst can identify the proposed link between them.
- **Остановиться или воздержаться:** The relevant text has not been identified.; The candidate is only a preferred moral outcome without an interpretive bridge.
- **Оговорки источника:** The source gives illustrative exclusion examples rather than a complete boundary test.; The claim preserves textual constraint while rejecting a uniquely definition-driven method.
- **Источник не доказывает:** It does not show that every text-connected moral reading is valid.; It does not provide the Russian legal criteria for acceptable constitutional interpretation.
- **Фальсификаторы и пределы переноса:** A demonstrated absence of textual connection falsifies the candidate as interpretation under the source's example.; Passing the boundary test does not establish correctness or legal acceptance.
- **Контрпример:** An argument that substitutes an abstract theory of justice for the constitutional words fails the first gate even if its desired result is attractive.
- **Не использовать для:** Do not equate textual connection with legal validity.; Do not use the boundary test to choose automatically among plausible readings.
- **Российская правовая граница:** Официальная опора уже: она требует учитывать буквальный и системный смысл, поэтому полностью оторванная от текста конструкция не может опираться на статью 74. Но закон не объявляет прохождение этого порога доказательством правдоподобия и не предписывает второй сравнительный этап. Пределы: Двухступенчатая архитектура остается сравнительной доктриной.; Связь с текстом — необходимый элемент анализа, но не единственное условие правильности.; Официальное толкование и сложившаяся практика могут ограничить круг правдоподобных чтений.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-a-cmc-sunstein-interpretive-boundary-02`; legal review `legal-anchor-a-r1-017-r2`; source SHA-256 `d80ef044af0c82f38be81cc9f8efe2bd76aad3d017ec1a89f0187dee5430a304`.

<a id="cmc-sunstein-formalism-qa-03"></a>
### `cmc-sunstein-formalism-qa-03` — Cass R. Sunstein

- **Работа и locator:** Formalism in Constitutional Theory; печат. 2–3; PDF 3–4; раздел Discussion of formalism and final substantive paragraph.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Argument review should flag definitional shortcuts that declare a competing plausible reading to be ‘not interpretation’ without engaging its text, reasons and consequences.
- **Когда полезна:** An argument claims victory from the definition of ‘interpretation’ or an equivalent label.
- **Предусловия:** A competing reading is textually plausible.; The draft relies on a definitional exclusion rather than substantive comparison.
- **Остановиться или воздержаться:** The competing position plainly ignores the text and is outside interpretation.; The draft already supplies substantive comparative reasons.
- **Оговорки источника:** The criticism concerns genuinely contested choices among plausible interpretive accounts.; It does not reject ordinary, actual or plain meaning as such; the source expressly brackets that separate topic.
- **Источник не доказывает:** It does not prove that linguistic meaning is irrelevant.; It does not establish that consequential or moral reasoning always defeats intended meaning.
- **Фальсификаторы и пределы переноса:** A genuine semantic boundary can justify exclusion without full normative comparison.; The critique fails if no plausible competing reading exists.
- **Контрпример:** Rejecting a backward reading of the text as a joke is a boundary judgment, not the contested formalist shortcut criticized by the author.
- **Не использовать для:** Do not ban semantic analysis.; Do not assume all proposed readings deserve equal consideration.
- **Российская правовая граница:** Статья 74 поддерживает многоаспектный анализ, но не закрепляет антиформалистическую доктрину Санстейна. Техника может выявлять неполноту довода, однако результат должен основываться на российских нормах и официальных позициях. Пределы: Наличие дефиниционного аргумента не означает его ошибочности: иногда спор действительно решается текстовой границей.; Оценка институциональных последствий не может преодолеть обязательный текст или позицию КС РФ.; Метод не устанавливает юридический результат и остается сравнительным QA.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-a-r1-04`; legal review `legal-anchor-a-r1-018`; source SHA-256 `d80ef044af0c82f38be81cc9f8efe2bd76aad3d017ec1a89f0187dee5430a304`.

<a id="cmc-barak-four-components-01"></a>
### `cmc-barak-four-components-01` — Aharon Barak

- **Работа и locator:** Proportionality: Constitutional Rights and Their Limitations — official excerpt; печат. 3; PDF 3; раздел Introduction; definition and four sub-components of proportionality.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** A proportionality argument should address each component separately and identify the evidence, burden and failure point instead of using ‘disproportionate’ as a conclusion.
- **Когда полезна:** A law or its applied normative meaning limits an identified constitutional right.
- **Предусловия:** The protected right and limitation have been identified.; A claimed purpose and supporting materials are available.
- **Остановиться или воздержаться:** No constitutional right or concrete limitation has been identified.; The excerpt is used as if it supplied the current Russian legal test without official verification.
- **Оговорки источника:** The formulation concerns a legal limitation of a constitutional right in a constitutional democracy.; The excerpt states the components but refers detailed treatment to chapters outside the excerpt.
- **Источник не доказывает:** The four-part formulation does not establish that Russian law adopts Barak's exact test.; It does not supply facts proving that a particular restriction fails any component.
- **Фальсификаторы и пределы переноса:** A measure may pass early components and still fail final balancing.; An alternative that is less restrictive but materially less effective does not by itself establish failure of necessity.
- **Контрпример:** A legitimate public purpose does not cure a measure that lacks rational connection or has an equally effective, substantially less restrictive alternative.
- **Не использовать для:** Do not collapse all components into intuitive fairness.; Do not infer constitutional invalidity from doctrine alone.
- **Российская правовая граница:** Российский стандарт функционально совпадает по цели, адекватности, необходимости и чрезмерности, поэтому есть более узкий anchor. Но официальный источник не делает четыре элемента Барака единой обязательной последовательностью и не формулирует универсальный самостоятельный less-restrictive-alternative test. Пределы: Четырехкомпонентная последовательность — сравнительная доктринальная форма, а не дословный российский тест.; Менее ограничительная альтернатива должна быть юридически допустимой и сопоставимо эффективной; ее отдельная обязательность зависит от официальной практики по конкретному праву.; Некоторые права имеют специальные или категорические пределы и не проходят обычное балансирование.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-argument-patterns.
- **Provenance:** source review `source-review-a-cmc-barak-four-components-01`; legal review `legal-anchor-a-r1-019-r2`; source SHA-256 `fe66c66c028c9273665a558f63c727d42fc65be62d461ec99a2bb1f9fa2698d0`.

<a id="cmc-barak-scope-before-justification-02"></a>
### `cmc-barak-scope-before-justification-02` — Aharon Barak

- **Работа и locator:** Proportionality: Constitutional Rights and Their Limitations — official excerpt; печат. 7–9; PDF 7–9; раздел Introduction; methodological distinction between scope and justification.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** The analysis should first define the right's scope and interference without importing justificatory interests, then test those interests transparently at the limitation stage.
- **Когда полезна:** A draft narrows a claimed right at the definition stage because of public interest or another person's right.
- **Предусловия:** The claimed constitutional right and protected conduct are specified.; The competing interest is identified separately.
- **Остановиться или воздержаться:** The claimed interest has no plausible connection to a protected right.; Russian official doctrine requires a different stage structure that has not been reconciled.
- **Оговорки источника:** This is Barak's proposed analytical architecture, not a neutral description of every constitutional system.; The excerpt distinguishes stages but leaves detailed parameters to chapters outside it.
- **Источник не доказывает:** It does not establish that every asserted interest falls within a Russian constitutional right.; It does not mean that public interests and other rights are irrelevant to the final analysis.
- **Фальсификаторы и пределы переноса:** A broad initial scope does not predetermine that the limitation is unjustified.; A genuine definitional boundary of the right is not necessarily hidden balancing.
- **Контрпример:** The existence of a public-order concern should not silently erase conduct from the right's scope; it should be tested as a justification for limiting the right.
- **Не использовать для:** Do not declare rights absolute.; Do not postpone every textual boundary to proportionality.
- **Российская правовая граница:** Конституция различает права и их ограничения, но структура конкретного права может включать текстовые и системные границы, а часть 3 статьи 17 прямо учитывает права других лиц. Поэтому широкая scope-first архитектура Барака не подтверждена как общий российский стандарт. Пределы: Структура и границы каждого российского права определяются его текстом и официальной практикой.; Конкурирующие права иногда релевантны уже для определения защищаемого содержания.; Широкая исходная сфера не доказывает наличие нарушения, компетенцию КС РФ или средство защиты.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-argument-patterns.
- **Provenance:** source review `source-review-a-cmc-barak-scope-before-justification-02`; legal review `legal-anchor-a-r1-020`; source SHA-256 `fe66c66c028c9273665a558f63c727d42fc65be62d461ec99a2bb1f9fa2698d0`.

<a id="cmc-barak-interpretive-balancing-03"></a>
### `cmc-barak-interpretive-balancing-03` — Aharon Barak

- **Работа и locator:** Proportionality: Constitutional Rights and Their Limitations — official excerpt; печат. 3–4; PDF 3–4; раздел Introduction; interpretive balancing distinguished from full proportionality.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Every use of balancing should identify whether it selects a legal meaning or tests constitutional validity; the analyst should not substitute the one-element interpretive exercise for the full limitation test.
- **Когда полезна:** A draft uses ‘balancing’ or ‘proportionality’ without specifying whether it concerns meaning or validity.
- **Предусловия:** The disputed legal text and claimed right are identified.; The requested conclusion about meaning or validity is stated.
- **Остановиться или воздержаться:** The draft does not identify the requested legal consequence.; Balancing is invoked without competing principles or a limitation.
- **Оговорки источника:** The distinction is illustrated through interpretation of governmental authority and statutory purpose.; Detailed treatment of interpretive balancing is outside the official excerpt.
- **Источник не доказывает:** Interpretive balancing alone does not establish that a law is constitutionally valid or invalid.; The distinction does not establish the Russian rules for choosing a conforming interpretation.
- **Фальсификаторы и пределы переноса:** A plausible interpretive balance cannot excuse skipping a required validity component.; If only meaning is disputed, a conclusion of invalidity exceeds the method.
- **Контрпример:** Choosing the narrower meaning of a licensing power through balance is not by itself a holding that the enabling law is unconstitutional.
- **Не использовать для:** Do not equate all balancing with proportionality review.; Do not conflate interpretation with remedy.
- **Российская правовая граница:** Российское право действительно разводит установление нормативного смысла и оценку допустимости ограничения, что поддерживает главный QA-сигнал. Но предложенная терминология и тезис о «только балансировании» при интерпретации остаются доктриной Барака. Пределы: Не всякое толкование включает баланс конституционных ценностей.; Установленный смысл может предшествовать проверке статьи 55, но точная структура зависит от права и предмета дела.; Интерпретационный вывод сам по себе не доказывает неконституционность или доступное средство.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-argument-patterns.
- **Provenance:** source review `source-review-a-cmc-barak-interpretive-balancing-03`; legal review `legal-anchor-a-r1-021-r2`; source SHA-256 `fe66c66c028c9273665a558f63c727d42fc65be62d461ec99a2bb1f9fa2698d0`.

<a id="cmc-barak-justification-culture-04"></a>
### `cmc-barak-justification-culture-04` — Aharon Barak

- **Работа и locator:** Proportionality: Constitutional Rights and Their Limitations — official excerpt; печат. 4; PDF 4; раздел Introduction; rights-protective nature of proportionality.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** A limitation analysis should demand an articulated purpose, evidence and reasons for each inferential step, with unresolved gaps recorded rather than cured by deference or intuition.
- **Когда полезна:** A public authority relies on a generalized interest or unexplained assertion to justify a limitation.
- **Предусловия:** The limitation and asserted justification are available.; The record permits identification of evidence and inferential steps.
- **Остановиться или воздержаться:** The authority's reasons or evidentiary record are unavailable.; The analyst cannot verify the applicable Russian allocation of burdens.
- **Оговорки источника:** The source does not claim that rights are absolute; it addresses justified limitations.; The official excerpt does not develop the full culture-of-justification account referenced in a footnote.
- **Источник не доказывает:** The claim does not determine who bears each burden under Russian law.; It does not make every imperfect explanation constitutionally fatal.
- **Фальсификаторы и пределы переноса:** Complete reason-giving does not guarantee that the measure is proportionate.; A sparse written explanation may not reflect the entire legally relevant record.
- **Контрпример:** Invoking ‘public safety’ without evidence of connection, alternatives or rights impact does not complete a proportionality analysis.
- **Не использовать для:** Do not presume invalidity from brevity alone.; Do not replace evidence with abstract rights rhetoric.
- **Российская правовая граница:** Официальный anchor требует содержательного оправдания ограничения, поэтому требование фиксировать цель и пробелы имеет российскую опору. Более сильная «культура обоснования» Барака — универсальное распределение доказательств по каждой стадии — официально не установлена. Пределы: Полнота письменного объяснения не исчерпывает весь юридически значимый материал дела.; Необъясненный пробел требует проверки, но не всегда автоматически влечет неконституционность.; Бремя доказывания и допустимые материалы зависят от конкретного производства и права.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-argument-patterns.
- **Provenance:** source review `source-review-a-cmc-barak-justification-culture-04`; legal review `legal-anchor-a-r1-022-r2`; source SHA-256 `fe66c66c028c9273665a558f63c727d42fc65be62d461ec99a2bb1f9fa2698d0`.

<a id="cmc-barak-conflicting-rights-level-05"></a>
### `cmc-barak-conflicting-rights-level-05` — Aharon Barak

- **Работа и locator:** Proportionality: Constitutional Rights and Their Limitations — official excerpt; печат. 6; PDF 6; раздел Introduction; stated departures from Robert Alexy's approach.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** When two rights conflict, preserve each candidate scope and analyze the limiting statutory or applied rule separately, while flagging that this architecture is a contestable foreign-doctrine choice.
- **Когда полезна:** A draft resolves a conflict by redefining one right out of existence at the scope stage.
- **Предусловия:** Both claimed rights have plausible constitutional grounding.; A statutory, common-law or applied rule mediating the conflict is identified.
- **Остановиться или воздержаться:** One claimed right lacks plausible constitutional grounding.; No mediating legal rule or applied normative meaning can be identified.; The method is presented as settled Russian law without official verification.
- **Оговорки источника:** Barak presents this as his own departure from his account of Alexy's position.; Alexy's primary text was not independently reviewed in this extraction.
- **Источник не доказывает:** The excerpt does not establish that Barak accurately or completely characterizes Alexy's theory.; The position does not establish the Russian doctrinal level at which conflicts of rights are resolved.
- **Фальсификаторы и пределы переноса:** An official Russian doctrine that defines the right with internal limits may require a different architecture.; Independent review of Alexy's primary work may qualify the stated contrast.
- **Контрпример:** Protecting one person's right does not automatically erase the other's protected scope; the mediating restriction may instead require justification.
- **Не использовать для:** Do not invent a conflict where rights operate in different factual domains.; Do not treat Barak's account of Alexy as Alexy's verified position.
- **Российская правовая граница:** Части 3 статьи 17 и 3 статьи 55 требуют учитывать права других лиц и допустимые ограничения, но не выбирают архитектуру Барака против иных теорий. Официальное толкование конкретного права может включать внутренние текстовые и системные пределы. Пределы: Метод является спорным сравнительным выбором и не может приписываться российской официальной доктрине.; Структура каждого права проверяется по его тексту и позициям КС РФ.; Отсутствие отдельной подконституционной нормы не доказывает автоматически отсутствие границы права или нарушение.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-argument-patterns.
- **Provenance:** source review `source-review-a-r1-05`; legal review `legal-anchor-a-r1-023`; source SHA-256 `fe66c66c028c9273665a558f63c727d42fc65be62d461ec99a2bb1f9fa2698d0`.

<a id="cmc-jackson-sequenced-proportionality-01"></a>
### `cmc-jackson-sequenced-proportionality-01` — Vicki C. Jackson

- **Работа и locator:** Constitutional Law in an Age of Proportionality; печат. 3099–3100; PDF 6–7; раздел Introduction: structured proportionality.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Строить аргумент о несоразмерности по ступеням, не смешивая цель, средство и конечное взвешивание.
- **Когда полезна:** Оспариваемая норма ограничивает защищаемое право.
- **Предусловия:** Определены норма, вмешательство и защищаемый интерес.
- **Остановиться или воздержаться:** Неизвестны цель ограничения или фактические эффекты нормы.
- **Оговорки источника:** Описана прежде всего канадская модель.; До финального баланса доходят только подлинные конфликты.
- **Источник не доказывает:** Тезис не доказывает, что эта схема уже является обязательным тестом КС РФ.
- **Фальсификаторы и пределы переноса:** Если право не допускает балансирования, нужен иной тест.
- **Контрпример:** Абсолютный запрет нельзя оправдывать итоговым перевесом пользы.
- **Не использовать для:** Механически импортировать канадскую доктрину.
- **Российская правовая граница:** Содержательные компоненты в значительной мере совпадают, поэтому по ним есть более узкий российский anchor. Последовательность и разделение пригодности, необходимости и узкого баланса остаются сравнительной структурой, полезной для прозрачности, но не обязательной формулой во всех делах. Пределы: Последовательность Джексон не должна выдаваться за дословный тест КС РФ.; Некоторые права или запреты требуют специального анализа без обычного финального баланса.; Для жалобы отдельно проверяются применение нормативного акта, исчерпание и связь ограничения с правом заявителя.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-b-cmc-jackson-sequenced-proportionality-01`; legal review `legal-anchor-a-r1-024-r2`; source SHA-256 `00f54613bd51fc7f29cc6d25f02f542fe9ebf18aa16dc63b5db48abff4ec882c`.

<a id="cmc-jackson-transparent-reasons-02"></a>
### `cmc-jackson-transparent-reasons-02` — Vicki C. Jackson

- **Работа и locator:** Constitutional Law in an Age of Proportionality; печат. 3142–3143; PDF 49–50; раздел III.C.1.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Представлять довод как проверяемую матрицу стадий и явно отмечать спорный переход, доказательство и контрдовод.
- **Когда полезна:** Довод сведен к общей фразе о балансе интересов.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Невозможно восстановить, какой факт подтверждает конкретную стадию.
- **Оговорки источника:** Преимущество зависит от фактического соблюдения единой структуры.; Автор допускает, что при конкуренции методологий выигрыш в единообразии может не реализоваться.
- **Источник не доказывает:** Тезис не доказывает правильность результата только потому, что решение структурировано.
- **Фальсификаторы и пределы переноса:** Структура не компенсирует ложные факты или неверное толкование нормы.
- **Контрпример:** Красиво разбитый на стадии довод остается слабым, если цель и эффекты ничем не подтверждены.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальное право поддерживает прозрачное reason-giving, но лишь в более узкой форме требований к решению КС РФ. Предложенная матрица — полезный QA-формат автора, а не обязательная правовая форма довода или судебного акта. Пределы: Статья 75 регулирует содержание решения КС РФ, а не устанавливает форму жалобы или меморандума.; Структура не исправляет ложные факты, нерелевантные источники или неверный правовой тест.; Количество стадий и их названия должны соответствовать официальному стандарту конкретного права.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-b-cmc-jackson-transparent-reasons-02`; legal review `legal-anchor-a-r1-025-r2`; source SHA-256 `00f54613bd51fc7f29cc6d25f02f542fe9ebf18aa16dc63b5db48abff4ec882c`.

<a id="cmc-jackson-institutional-bridge-03"></a>
### `cmc-jackson-institutional-bridge-03` — Vicki C. Jackson

- **Работа и locator:** Constitutional Law in an Age of Proportionality; печат. 3144–3146; PDF 51–53; раздел III.C.2.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Проверять не только формулу нормы, но и доступные законодателю материалы о цели, прогнозе и альтернативах.
- **Когда полезна:** Ограничение защищается ссылкой на усмотрение законодателя без раскрытия причин.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Отсутствуют материалы, позволяющие отличить прогноз от последующего оправдания.
- **Оговорки источника:** При эмпирической или нормативной неопределенности возможна зона усмотрения законодателя.; Интенсивность судебной проверки может различаться по стадиям.
- **Источник не доказывает:** Тезис не превращает суд в первичного разработчика государственной политики.
- **Фальсификаторы и пределы переноса:** Метод не предписывает суду выбирать оптимальную политику вместо законодателя.
- **Контрпример:** Наличие альтернативы не опровергает меру автоматически, если ее равная эффективность не показана.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Российский anchor поддерживает контроль цели, адекватности и необходимости даже при законодательном усмотрении. Он не создает универсальной процессуальной обязанности законодателя публиковать прогноз и перебор альтернатив, поэтому исследование материалов остается доказательственной техникой. Пределы: Отсутствие в материалах обсуждения альтернатив не тождественно автоматически неконституционности нормы.; Суд не выбирает оптимальную политику вместо законодателя, а проверяет конституционные пределы.; Нужно отличать материалы, существовавшие при принятии нормы, от последующего оправдания, но российский общий тест этого различия прямо не формулирует.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-b-cmc-jackson-institutional-bridge-03`; legal review `legal-anchor-a-r1-026-r2`; source SHA-256 `00f54613bd51fc7f29cc6d25f02f542fe9ebf18aa16dc63b5db48abff4ec882c`.

<a id="cmc-jackson-disproportion-process-failure-04"></a>
### `cmc-jackson-disproportion-process-failure-04` — Vicki C. Jackson

- **Работа и locator:** Constitutional Law in an Age of Proportionality; печат. 3151–3152; PDF 58–59; раздел III.C.4.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Использовать диспропорцию как триггер запроса к материалам принятия нормы и распределению ее бремени.
- **Когда полезна:** Нейтральная норма концентрирует тяжесть на слабопредставленной группе.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Нет надежных данных о последствиях или сопоставимых группах.
- **Оговорки источника:** Диспропорция является сигналом для усиленной проверки, а не самостоятельным доказательством мотива.; Профилактические правила способны оправданно порождать отдельные диспропорции.
- **Источник не доказывает:** Тезис не доказывает дискриминационный умысел одним статистическим разрывом.
- **Фальсификаторы и пределы переноса:** Корреляция должна проверяться альтернативными объяснениями.
- **Контрпример:** Неравный эффект обоснован точной целью и не мог быть снижен без разрушения защитной меры.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальная опора уже: она требует выявить различие и проверить его конституционную оправданность. Причину в виде дефекта политического процесса российское право автоматически не презюмирует, поэтому вывод о недоучете группы остается проверяемой гипотезой. Пределы: Сначала нужны надежные данные, релевантно сопоставимые группы и юридически значимое различие.; Корреляция не доказывает предубеждение или недопредставленность; проверяются альтернативные объяснения.; Для жалобы в КС РФ неравный эффект должен быть связан с примененным нормативным актом или устойчивым смыслом.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-b-cmc-jackson-disproportion-process-failure-04`; legal review `legal-anchor-a-r1-027-r2`; source SHA-256 `00f54613bd51fc7f29cc6d25f02f542fe9ebf18aa16dc63b5db48abff4ec882c`.

<a id="cmc-jackson-nonmetric-judgment-05"></a>
### `cmc-jackson-nonmetric-judgment-05` — Vicki C. Jackson

- **Работа и locator:** Constitutional Law in an Age of Proportionality; печат. 3156–3157; PDF 63–64; раздел IV.A.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Заменять псевдоарифметику сравнением конкретной тяжести вреда, важности цели и контекстных причин приоритета.
- **Когда полезна:** В аргументе заявлен «перевес», но не объяснено, почему он следует из обстоятельств.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Не доказаны интенсивность вреда или вклад меры в достижение цели.
- **Оговорки источника:** Отсутствие общей метрики не устраняет обязанность рационально объяснить выбор.; Финальная стадия остается оценочной и допускает разумные разногласия.
- **Источник не доказывает:** Тезис не разрешает присваивать правам произвольные числовые веса.
- **Фальсификаторы и пределы переноса:** Финальный баланс не должен маскировать непригодность либо наличие равной менее обременительной меры.
- **Контрпример:** Сильная абстрактная цель не перевешивает автоматически минимально доказанную пользу меры.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Российский стандарт действительно требует содержательного баланса и оценки чрезмерности, а не арифметической операции. Однако тезис о том, что финальный баланс всегда проводится только после двух отдельных стадий, остается сравнительной организацией. Пределы: Баланс не должен скрывать отсутствие допустимой цели или связи меры с ней.; Интенсивность вреда и фактическая польза требуют доказательств, а не оценочных эпитетов.; Специальный официальный тест конкретного права имеет приоритет над общей схемой.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-b-cmc-jackson-nonmetric-judgment-05`; legal review `legal-anchor-a-r1-028-r2`; source SHA-256 `00f54613bd51fc7f29cc6d25f02f542fe9ebf18aa16dc63b5db48abff4ec882c`.

<a id="cmc-jackson-boundaries-text-rights-06"></a>
### `cmc-jackson-boundaries-text-rights-06` — Vicki C. Jackson

- **Работа и locator:** Constitutional Law in an Age of Proportionality; печат. 3166–3168, 3193–3194; PDF 73–75, 100–101; раздел V and Conclusion.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Сначала квалифицировать структуру права и роль категорического запрета, затем выбирать между тестом на уровне случая и тестом на уровне правила.
- **Когда полезна:** Пропорциональность предлагается применить к любому праву автоматически.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Не исследованы текст и официальная практика конкретного права.
- **Оговорки источника:** Даже категорические правила могут проектироваться с учетом пропорциональности на уровне правила.; Автор предлагает умеренное, а не всеобщее расширение метода.
- **Источник не доказывает:** Тезис не доказывает превосходство правил над стандартами во всех категориях дел.
- **Фальсификаторы и пределы переноса:** Сравнительная доктрина не определяет структуру российского права без официальной сверки.
- **Контрпример:** Запрет пыток нельзя превращать в обычный баланс пользы и вреда.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальные нормы подтверждают необходимость сначала определить структуру и специальные пределы права: Конституция различает, в частности, неотступаемые при чрезвычайном положении гарантии. Сравнительная идея о выборе rule-level или case-level теста шире российской опоры. Пределы: Часть 3 статьи 56 относится к чрезвычайному положению и не превращает перечисленные права в абсолютно неограничимые во всех иных контекстах.; История и сравнительная доктрина не заменяют официальный российский текст и позиции КС РФ.; Выбор теста проводится отдельно для конкретного права, нормы и вида вмешательства.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-b-cmc-jackson-boundaries-text-rights-06`; legal review `legal-anchor-a-r1-029-r2`; source SHA-256 `00f54613bd51fc7f29cc6d25f02f542fe9ebf18aa16dc63b5db48abff4ec882c`.

<a id="cmc-dworkin-preexisting-rights-01"></a>
### `cmc-dworkin-preexisting-rights-01` — Ronald Dworkin

- **Работа и locator:** Hard Cases, chapter 4 of Taking Rights Seriously; печат. 81; PDF 3; раздел I. Introduction; OCR page-03.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Формулировать трудный вопрос как спор о наилучшем обосновании права стороны, а не как просьбу суда создать новое исключение.
- **Когда полезна:** Нет прямой нормы или полностью совпадающего прецедента.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Фактические требования стороны не определены.
- **Оговорки источника:** Тезис не обещает демонстрируемого единственного ответа по алгоритму.; Речь идет о нормативной теории adjudication, а не эмпирическом описании всех судей.
- **Источник не доказывает:** Тезис не доказывает конкретное право заявителя без реконструкции институциональной практики.
- **Фальсификаторы и пределы переноса:** Поиск права не заменяет требования допустимости и компетенции суда.
- **Контрпример:** Просьба установить новую льготу по целесообразности является политикой, а не обнаружением права.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Российский суд обязан правовым источникам и не может произвольно создавать компетенцию или ретроактивную обязанность, но это не подтверждает философский тезис о едином предсуществующем праве стороны. Метод пригоден как честная сравнительная постановка сложного вопроса. Пределы: Отсутствие прямого правила или совпадающего прецедента не освобождает от правил компетенции, допустимости и источников права.; Принципиальное обоснование не может преодолеть ясную обязательную норму или решение КС РФ.; Возможность разумного разногласия не доказывает право заявителя или требуемое средство.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-dworkin-preexisting-rights-01`; legal review `legal-anchor-a-r1-030`; source SHA-256 `b7fa25cd543ce87b72af45fa5211536fb51e38e3979c1ca410a66a1f33e6c8f9`.

<a id="cmc-dworkin-principle-policy-02"></a>
### `cmc-dworkin-principle-policy-02` — Ronald Dworkin

- **Работа и locator:** Hard Cases, chapter 4 of Taking Rights Seriously; печат. 82–85; PDF 4–7; раздел II.A; OCR pages 04–07.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Маркировать каждое основание как право стороны либо коллективную цель и не выдавать второе за доказательство первого.
- **Когда полезна:** Публичная польза предъявляется как достаточное основание отказа в субъективном праве.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Основания решения восстановлены лишь предположительно.
- **Оговорки источника:** Законодательство может правомерно опираться и на политику, и на принципы.; Один результат иногда допускает разные типы обоснования, которые нужно различать по функции.
- **Источник не доказывает:** Тезис не объявляет коллективные цели юридически нерелевантными при любой проверке ограничения.
- **Фальсификаторы и пределы переноса:** Классификация требует контекста и не определяется отдельным словом.
- **Контрпример:** Экономия бюджета как цель сама по себе не устанавливает отсутствие права заявителя.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Российское право требует правовой опоры и соразмерности публичного интереса, но не закрепляет философскую дихотомию Дворкина. Маркировка может делать аргумент прозрачнее, однако юридический результат определяется текстом права, нормой ограничения и официальным тестом. Пределы: Слово «интерес» или «цель» само по себе не определяет функцию довода.; Коллективная цель может быть конституционно допустимым основанием ограничения, но только при соблюдении статьи 55 и специального стандарта.; Таксономия не расширяет компетенцию суда и не создает субъективное право.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-dworkin-principle-policy-02`; legal review `legal-anchor-a-r1-031`; source SHA-256 `b7fa25cd543ce87b72af45fa5211536fb51e38e3979c1ca410a66a1f33e6c8f9`.

<a id="cmc-dworkin-history-morality-03"></a>
### `cmc-dworkin-history-morality-03` — Ronald Dworkin

- **Работа и locator:** Hard Cases, chapter 4 of Taking Rights Seriously; печат. 87; PDF 9; раздел II.B; OCR page-09.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Соединять линию официальной практики с объясняющим ее принципом и проверять напряжение между ними явно.
- **Когда полезна:** Текст допускает несколько решений, а практика содержит разные направления.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Выборка практики неполна или односторонна.
- **Оговорки источника:** История не является автоматически справедливой.; Моральная оценка не дает судье свободы игнорировать институциональные решения.
- **Источник не доказывает:** Тезис не разрешает выбирать между историей и справедливостью по личному предпочтению.
- **Фальсификаторы и пределы переноса:** Доктрина не дает права игнорировать обязательную силу акта.
- **Контрпример:** Ссылка только на справедливость без объяснения устойчивой практики не выполняет метод.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Российский anchor поддерживает сбор линии толкований и практики и ее системную реконструкцию. Он уже доктрины Дворкина: принципиальное или моральное оправдание допустимо лишь при наличии конституционной и официальной правовой опоры. Пределы: Неполная или односторонняя выборка практики искажает результат.; Моральный принцип не позволяет игнорировать обязательный акт или ясную норму.; Изменение официальной позиции, редакции закона и предмета дела должно отражаться во временном анализе.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-dworkin-history-morality-03`; legal review `legal-anchor-a-r1-032-r2`; source SHA-256 `b7fa25cd543ce87b72af45fa5211536fb51e38e3979c1ca410a66a1f33e6c8f9`.

<a id="cmc-dworkin-precedent-gravity-04"></a>
### `cmc-dworkin-precedent-gravity-04` — Ronald Dworkin

- **Работа и locator:** Hard Cases, chapter 4 of Taking Rights Seriously; печат. 113; PDF 35; раздел V.B.1; OCR page-35.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Извлекать из позиции принцип, необходимый для результата, и проверять его применимость к заявителю через релевантное сходство.
- **Когда полезна:** Сторона ссылается на прежнее решение с иными фактами.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Не доступна мотивировка решения либо она цитируется фрагментарно.
- **Оговорки источника:** Специфическая обязательная сила решения и его принципиальная «гравитация» различаются.; Сходство случаев требует самостоятельного обоснования.
- **Источник не доказывает:** Тезис не позволяет переносить результат прецедента по поверхностной фактической аналогии.
- **Фальсификаторы и пределы переноса:** Политическое обоснование не обязательно имеет такое же расширительное действие.
- **Контрпример:** Одинаковое слово в двух делах не делает их одинаковыми по оправдывающему принципу.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Для решений КС РФ российская опора поддерживает точное извлечение обязательного нормативного смысла и проверку предметной применимости. Дворкиновское расширительное действие «прецедента» шире: оно не становится общим правилом для любого судебного акта и любого оправдывающего принципа. Пределы: Нужно различать обязательный конституционно-правовой смысл, иные мотивы и фактический контекст.; Решения обычных судов не получают автоматически такую же общеобязательную силу, как решения КС РФ.; Фактическое сходство без совпадения нормы, редакции и конституционного вопроса недостаточно.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-r1-01-dworkin`; legal review `legal-anchor-a-r1-033-r2`; source SHA-256 `b7fa25cd543ce87b72af45fa5211536fb51e38e3979c1ca410a66a1f33e6c8f9`.

<a id="cmc-dworkin-coherent-justification-05"></a>
### `cmc-dworkin-coherent-justification-05` — Ronald Dworkin

- **Работа и locator:** Hard Cases, chapter 4 of Taking Rights Seriously; печат. 116–118; PDF 38–40; раздел V.B.2; OCR pages 38–40.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Проводить системный stress-test предложенного принципа на вышестоящих и однопорядковых позициях.
- **Когда полезна:** Довод опирается на единичное благоприятное решение.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Не задан релевантный корпус актов и критерий отбора.
- **Оговорки источника:** Полная бесшовность — регулятивный идеал, а не описание фактически непротиворечивого права.; Разные судьи могут расходиться в оценке соответствия и политической морали.
- **Источник не доказывает:** Тезис не требует искусственно примирять все решения любой ценой.
- **Фальсификаторы и пределы переноса:** Системная согласованность не отменяет специальную норму и временные различия.
- **Контрпример:** Принцип, оправдывающий одно дело, но противоречащий устойчивой линии сходных дел, слаб.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальные источники прямо поддерживают вертикальный и системный stress-test и учет сложившейся практики. Дворкиновское требование лучшего целостного морального оправдания шире и должно быть заменено проверкой по российской иерархии, специальным нормам и точным правовым позициям. Пределы: Критерий отбора корпуса должен быть заранее объяснен, включая неблагоприятные акты.; Системная согласованность не отменяет специальную норму, временные различия или изменение позиции.; Горизонтальная согласованность не создает общеобязательность обычного судебного решения.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-dworkin-coherent-justification-05`; legal review `legal-anchor-a-r1-034-r2`; source SHA-256 `b7fa25cd543ce87b72af45fa5211536fb51e38e3979c1ca410a66a1f33e6c8f9`.

<a id="cmc-dworkin-institutional-mistakes-06"></a>
### `cmc-dworkin-institutional-mistakes-06` — Ronald Dworkin

- **Работа и locator:** Hard Cases, chapter 4 of Taking Rights Seriously; печат. 121–122; PDF 43–44; раздел V.B.3; OCR pages 43–44.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Для каждого конфликтующего акта отдельно решать, сохраняет ли он обязательную силу и почему не должен расширяться на новый случай.
- **Когда полезна:** Ключевой принцип жалобы конфликтует с действующим актом или решением.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Статус, обязательность или последующая судьба акта не проверены.
- **Оговорки источника:** Даже ошибочный закон может сохранять специфическую обязательную силу.; Отступление от истории prima facie ослабляет оправдание и требует усиленной аргументации.
- **Источник не доказывает:** Тезис не позволяет исключать любой конфликтующий прецедент как ошибку ad hoc.
- **Фальсификаторы и пределы переноса:** Доктринальная критика не отменяет обязательный официальный акт.
- **Контрпример:** Называть решение ошибочным только потому, что оно мешает жалобе, методологически недопустимо.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Статус conflict завышен: card требует отдельно установить, сохраняет ли акт обязательную силу, и запрещает превращать доктринальную критику в отмену официального акта. В российском контуре ч. 6 ст. 125 Конституции РФ и ст. 6, 79 1-ФКЗ делают этот safeguard обязательным. Перенос допустим только как различение обязательной силы позиции и границ ее распространения на новый случай; он не позволяет аналитику не применять решение КС РФ. Пределы: Решения КС РФ и данный ими обязательный нормативный смысл сохраняют юридическую силу; аналитик не вправе объявлять их необязательными.; Различение допустимо только по точному предмету, редакции нормы, фактам и границам официального вывода, а не из-за неудобства результата.; Доктринальная критика может объяснять предложение о более узком переносе, но не служит основанием не применять решение КС РФ.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-dworkin-institutional-mistakes-06`; legal review `legal-anchor-a-r1-035`; source SHA-256 `b7fa25cd543ce87b72af45fa5211536fb51e38e3979c1ca410a66a1f33e6c8f9`.

<a id="cmc-dworkin-judicial-humility-07"></a>
### `cmc-dworkin-judicial-humility-07` — Ronald Dworkin

- **Работа и locator:** Hard Cases, chapter 4 of Taking Rights Seriously; печат. 130; PDF 52; раздел VI; OCR page-52.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Добавлять к сильному принципиальному выводу раздел о неопределенности, альтернативной реконструкции и последствиях возможной ошибки.
- **Когда полезна:** Проект утверждает единственно возможный ответ при неоднородной практике.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Автор проекта не рассмотрел сильнейший контрдовод.
- **Оговорки источника:** Критерий сравнительный: нужно оценивать и ошибки альтернативного метода.; Скромность не означает автоматическую передачу правового вопроса большинству.
- **Источник не доказывает:** Тезис не доказывает институциональное превосходство любого суда в моральном рассуждении.
- **Фальсификаторы и пределы переноса:** Скромность не оправдывает уклонение от решения поставленного правового вопроса.
- **Контрпример:** Фраза «суд может ошибиться» без анализа альтернатив не является методической скромностью.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальная норма подтверждает доказательность, предметные пределы и мотивированность решения, но не тот же операциональный стандарт: она не требует сравнивать ошибки альтернатив, объявлять уровень уверенности или использовать доктринальную «скромность». Перенос допустим только как прозрачная внутренняя QA-эвристика, не как критерий допустимости, компетенции или исхода. Пределы: Метод Дворкина относится к зарубежной общей теории права и не является российским правовым стандартом.; ФКЗ не обязывает суд или автора жалобы количественно сравнивать риск ошибок альтернативных методов.; Оговорка о неуверенности не заменяет правовое обоснование и не влияет сама по себе на допустимость жалобы.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-dworkin-judicial-humility-07`; legal review `legal-anchor-b-r1-001-cmc-dworkin-judicial-humility-07`; source SHA-256 `b7fa25cd543ce87b72af45fa5211536fb51e38e3979c1ca410a66a1f33e6c8f9`.

<a id="cmc-bondar-multidimensional-constitutionalism-01"></a>
### `cmc-bondar-multidimensional-constitutionalism-01` — Николай Семёнович Бондарь

- **Работа и locator:** Российский судебный конституционализм: введение в методологию исследования; печат. 13–16; PDF 13–16; раздел 1.1.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При анализе проблемы отдельно фиксировать нормативный текст, практику реализации, доктринальные смыслы и социокультурный контекст.
- **Когда полезна:** Формально действующая гарантия расходится с практикой и общественными условиями.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Факты практики заменены общими социологическими предположениями.
- **Оговорки источника:** Перечень измерений служит аналитической моделью автора.; Политическое измерение не должно подчинять конституционализм конъюнктуре.
- **Источник не доказывает:** Тезис не устанавливает юридическую силу доктрины или общественного сознания.
- **Фальсификаторы и пределы переноса:** Ненормативный контекст объясняет, но сам не устанавливает право.
- **Контрпример:** Общественное одобрение практики не делает ее конституционной.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальное право прямо требует совместно учитывать текст, официальное толкование, практику и системное место нормы. Оно не придает доктрине, общественному сознанию или социокультурным оценкам самостоятельной юридической силы и не требует универсальной четырехслойной карты. Поэтому подтвержден только нормативно-практический и системный минимум метода. Пределы: Доктринальный и социокультурный материал может объяснять проблему, но не верифицирует действующее право.; Правоприменительная практика учитывается для выявления нормативного смысла, но сама по себе не является предметом конституционного нормоконтроля.; Метод не расширяет предмет обращения и не дает КС РФ полномочий оценивать политическую или социально-экономическую целесообразность.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder; ksrf-decision-execution.
- **Provenance:** source review `source-review-b-cmc-bondar-multidimensional-constitutionalism-01`; legal review `legal-anchor-b-r1-002-cmc-bondar-multidimensional-constitutionalism-01`; source SHA-256 `f3b8b44f3ca308a5bdb63c529fd8f37a04376fc1abeb85c7275a3a121eba04c7`.

<a id="cmc-bondar-constitutional-realism-02"></a>
### `cmc-bondar-constitutional-realism-02` — Николай Семёнович Бондарь

- **Работа и locator:** Российский судебный конституционализм: введение в методологию исследования; печат. 33–36; PDF 33–36; раздел 1.3–1.4.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Сопоставлять обещание нормы с механизмом, фактической реализацией и доступной защитой.
- **Когда полезна:** Орган ссылается на формальное наличие гарантии при системном отсутствии результата.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Нет проверяемых данных о применении нормы к заявителю.
- **Оговорки источника:** Автор связывает реализм с институциональным потенциалом Конституции и национальным контекстом.; Фактическая практика не подменяет нормативную оценку.
- **Источник не доказывает:** Тезис не делает любое сложившееся отношение конституционно оправданным.
- **Фальсификаторы и пределы переноса:** Общий системный тезис не заменяет доказательство личной затронутости.
- **Контрпример:** Единичная ошибка применения не всегда доказывает дефект всей модели.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальные нормы не позволяют считать формального провозглашения права достаточным и требуют связи оспариваемой нормы с конкретным нарушением и судебной защитой. Однако они не устанавливают общий эмпирический тест «норма — механизм — практика — разрыв» и не позволяют КС РФ оценивать фактическую эффективность вне нормативного предмета жалобы. Пределы: Общие данные о системной неэффективности не заменяют доказательство применения нормы и личной затронутости.; КС РФ решает вопросы права и не исследует факты, входящие в компетенцию иных судов или органов.; Из принципа непосредственного действия не следует конкретный способ восстановления без проверки статей 79, 87 и 100 ФКЗ и резолютивной части решения.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder; ksrf-decision-execution.
- **Provenance:** source review `source-review-b-cmc-bondar-constitutional-realism-02`; legal review `legal-anchor-b-r1-003-cmc-bondar-constitutional-realism-02`; source SHA-256 `f3b8b44f3ca308a5bdb63c529fd8f37a04376fc1abeb85c7275a3a121eba04c7`.

<a id="cmc-bondar-methodological-pluralism-03"></a>
### `cmc-bondar-methodological-pluralism-03` — Николай Семёнович Бондарь

- **Работа и locator:** Российский судебный конституционализм: введение в методологию исследования; печат. 35–43, 75–77; PDF 35–43, 75–77; раздел 1.4 and 3.1.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** В исследовательском мемо разнести вопросы валидности нормы, ее истории, эффектов и ценностного оправдания.
- **Когда полезна:** Один метод оставляет необъясненным ключевой аспект проблемы.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Источник одного слоя выдается за доказательство другого.
- **Оговорки источника:** Догматический метод остается необходимым для установления содержания позитивного права.; Плюрализм не означает эклектическое смешение несовместимых выводов.
- **Источник не доказывает:** Тезис не позволяет фактическими или моральными соображениями отменить действующую норму.
- **Фальсификаторы и пределы переноса:** Плюрализм требует источников для каждого вида утверждений.
- **Контрпример:** Социологический опрос сам по себе не определяет конституционный смысл нормы.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Статья 74 дает нормативно-системную рамку исследования, но не превращает исторический, социологический, аксиологический или культурологический анализ в обязательные правовые стадии. Эти подходы могут использоваться объяснительно, если не подменяют официальный источник и не выводят Суд за пределы вопросов права. Пределы: Для каждого ненормативного утверждения нужен самостоятельный проверяемый источник.; Социологический или ценностный вывод не отменяет действующую норму и не доказывает ее неконституционность.; Методологический плюрализм не расширяет компетенцию КС РФ и не создает remedy.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder; ksrf-decision-execution.
- **Provenance:** source review `source-review-b-cmc-bondar-methodological-pluralism-03`; legal review `legal-anchor-b-r1-004-cmc-bondar-methodological-pluralism-03`; source SHA-256 `f3b8b44f3ca308a5bdb63c529fd8f37a04376fc1abeb85c7275a3a121eba04c7`.

<a id="cmc-bondar-living-constitutionalism-04"></a>
### `cmc-bondar-living-constitutionalism-04` — Николай Семёнович Бондарь

- **Работа и locator:** Российский судебный конституционализм: введение в методологию исследования; печат. 45; PDF 45; раздел 2. Introduction.
- **Статус:** source `passed/keep`; legal `illustrative/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Обосновывая эволюционное толкование, показывать его опору в тексте и функции Конституции и предел, исключающий подмену.
- **Когда полезна:** Старое толкование не учитывает изменившийся устойчивый социальный контекст.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Предлагаемый результат противоречит прямому тексту или меняет компетенцию суда.
- **Оговорки источника:** Автор прямо различает «живой конституционализм» и «живую конституцию».; Актуализация должна происходить в пределах конституционного правосудия.
- **Источник не доказывает:** Тезис не наделяет суд полномочием переписывать Конституцию по соображениям актуальности.
- **Фальсификаторы и пределы переноса:** Изменение контекста не является самостоятельным источником новой нормы.
- **Контрпример:** Политическая целесообразность без конституционной опоры не является актуализацией.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальные нормы подтверждают существование конституционного толкования и учет правоприменительного смысла, но не устанавливают доктрину «живого конституционализма» и не делают изменение общественных отношений самостоятельным основанием нового смысла. Официальное толкование Конституции возможно лишь в специальной компетенции и процедуре, а контроль конкретной нормы ограничен предметом обращения. Пределы: Изменившийся контекст не является самостоятельным источником нормы.; Автор жалобы не вправе объявлять собственную эволюционную интерпретацию общеобязательным конституционным смыслом.; Метод недопустим, если фактически меняет текст Конституции, компетенцию Суда или баланс, оставленный законодателю.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder; ksrf-decision-execution.
- **Provenance:** source review `source-review-b-cmc-bondar-living-constitutionalism-04`; legal review `legal-anchor-b-r1-005-cmc-bondar-living-constitutionalism-04`; source SHA-256 `f3b8b44f3ca308a5bdb63c529fd8f37a04376fc1abeb85c7275a3a121eba04c7`.

<a id="cmc-bondar-judicial-constitutionalism-conditions-06"></a>
### `cmc-bondar-judicial-constitutionalism-conditions-06` — Николай Семёнович Бондарь

- **Работа и locator:** Российский судебный конституционализм: введение в методологию исследования; печат. 70–74; PDF 70–74; раздел 2.4.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Оценивать средство защиты не по названию института, а по доступу, объему проверки, корректирующему эффекту и восстановлению права.
- **Когда полезна:** Формальная доступность суда принимается за достаточную эффективность защиты.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Не установлены актуальные процессуальные правила и последствия решения.
- **Оговорки источника:** Это комплекс идеальных условий авторской модели.; Автор включает в защиту социально-экономические права.
- **Источник не доказывает:** Тезис не доказывает наличие каждого условия в современной практике КС РФ.
- **Фальсификаторы и пределы переноса:** Доктринальная модель не заменяет анализ допустимости конкретной жалобы.
- **Контрпример:** Орган, который может высказаться, но не повлиять на норму или дело, не выполняет всю модель.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальное право действительно требует раздельно проверить доступ, предмет, юридический эффект и возможный пересмотр, поэтому четырехблочная карта полезна. Но оно не устанавливает доктринальный идеал «судебного конституционализма» как самостоятельный критерий и не гарантирует восстановление в каждом деле: последствия зависят от вида решения, указаний КС РФ и процессуального статуса дела. Пределы: Формальная доступность жалобы не отменяет специальных условий статьи 97 ФКЗ.; КС РФ проверяет нормативный вопрос и не является инстанцией переоценки фактов или законности судебных актов.; Пересмотр конкретного дела не автоматичен во всех категориях и проверяется по тексту постановления и действующей редакции статей 79 и 100 ФКЗ.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder; ksrf-decision-execution.
- **Provenance:** source review `source-review-b-cmc-bondar-judicial-constitutionalism-conditions-06`; legal review `legal-anchor-b-r2-007-cmc-bondar-judicial-constitutionalism-conditions-06`; source SHA-256 `f3b8b44f3ca308a5bdb63c529fd8f37a04376fc1abeb85c7275a3a121eba04c7`.

<a id="cmc-bondar-sociocultural-context-08"></a>
### `cmc-bondar-sociocultural-context-08` — Николай Семёнович Бондарь

- **Работа и locator:** Российский судебный конституционализм: введение в методологию исследования; печат. 86–87; PDF 86–87; раздел 3.2.
- **Статус:** source `passed/keep`; legal `illustrative/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Для иностранного аргумента отдельно описывать функциональное сходство, институциональные различия и предел переноса.
- **Когда полезна:** Иностранная доктрина переносится как готовое российское правило.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Нет первичного иностранного источника или российского официального аналога.
- **Оговорки источника:** Контекст не отменяет универсальных правовых ценностей.; Тезис выражает авторскую позицию о национально-культурной обусловленности.
- **Источник не доказывает:** Тезис не оправдывает нарушение прав ссылкой на неопределенную национальную особенность.
- **Фальсификаторы и пределы переноса:** Культурный контекст должен быть доказан, а не заявлен стереотипом.
- **Контрпример:** Различие правовых семей не делает любой сравнительный материал нерелевантным.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Конституция признает конкретные исторические и государственные ценности и собственное верховенство, но не устанавливает авторскую общую формулу национально-культурной обусловленности всех прав. Функциональное сравнение институтов допустимо как аналитика, однако культурное утверждение должно быть доказано и не может уменьшать прямо гарантированное право. Пределы: Традиция не является самостоятельным основанием ограничения права вне статьи 55 части 3 Конституции и специального федерального закона.; Нельзя выводить правовой результат из стереотипа или неопределенной ссылки на культуру.; Иностранный материал может иметь сравнительную роль, но российское правило и компетенция должны подтверждаться отдельно.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder; ksrf-decision-execution.
- **Provenance:** source review `source-review-b-r1-04-bondar-sociocultural-context`; legal review `legal-anchor-b-r1-009-cmc-bondar-sociocultural-context-08`; source SHA-256 `f3b8b44f3ca308a5bdb63c529fd8f37a04376fc1abeb85c7275a3a121eba04c7`.

<a id="cmc-joint-social-right-definiteness-01"></a>
### `cmc-joint-social-right-definiteness-01` — Константин Викторович Арановский, Сергей Дмитриевич Князев, Евгений Борисович Хохлов

- **Работа и locator:** О правах человека и социальных правах; печат. 73, 77; PDF 75, 79; раздел Основания и субъективные права.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Из авторского критерия компилятор выводит проверочную эвристику: до содержательного довода можно построить корреспонденцию «носитель — основание — обязанное лицо — исполнение».
- **Когда полезна:** В жалобе названо благо, но не определена юридическая обязанность.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Нельзя определить обязанного субъекта или юридическое основание.
- **Оговорки источника:** Не все социальные права имеют одинаковую конструкцию.; Определенность может следовать из закона, договора или иного признанного основания.
- **Источник не доказывает:** Тезис не отрицает социальные права как класс и не устанавливает их закрытый перечень.
- **Фальсификаторы и пределы переноса:** Неопределенность доктринального названия не исключает конкретного законного права.
- **Контрпример:** Общая государственная программа без индивидуализируемой обязанности может не создавать субъективного требования.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальные нормы подтверждают необходимость установить конкретное законное основание, случай обеспечения и личное нарушение, что поддерживает ядро матрицы. Но они не устанавливают универсальную частноправовую корреспонденцию «носитель — контрагент — объем» для каждого социального права: часть обязанностей государства имеет институциональную или программно-законодательную форму. Пределы: Нельзя отказать в защите конституционного социального права только потому, что обязанность не построена как двустороннее частное правоотношение.; Содержание конкретной выплаты или услуги определяется специальным законом и официальной практикой, а не одной общей типологией.; Матрица не заменяет проверку примененной нормы, личной затронутости, допустимости и доступного remedy.
- **Маршруты:** ksrf-case-triage; ksrf-formal-filing-check; ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `461b620a-8cb2-44f1-a2d6-22b25ef588fc`; legal review `legal-anchor-b-r1-010-cmc-joint-social-right-definiteness-01`; source SHA-256 `174883b9917c6bb916e9e9feeada890f05efbfb4f147dee71cf4197c7a7ae5a4`.

<a id="cmc-joint-social-program-not-right-02"></a>
### `cmc-joint-social-program-not-right-02` — Константин Викторович Арановский, Сергей Дмитриевич Князев, Евгений Борисович Хохлов

- **Работа и locator:** О правах человека и социальных правах; печат. 77; PDF 79; раздел Основания и субъективные права.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Не обещать судебное взыскание до установления индивидуализируемой обязанности; отдельно описать программный и субъективный компоненты.
- **Когда полезна:** Заявитель выводит конкретную выплату из общей цели государства.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Не изучены специальные нормы, конкретизирующие общую гарантию.
- **Оговорки источника:** Квалификация меняется, если обязанность конкретизирована законом, договором или обещанием.; Программная норма сохраняет юридическую и политическую значимость в своей роли.
- **Источник не доказывает:** Тезис не доказывает, что программное положение не имеет никаких правовых последствий.
- **Фальсификаторы и пределы переноса:** Название положения не предрешает его юридическую конструкцию.
- **Контрпример:** Закон с точной формулой выплаты нельзя понизить до программы из-за бюджетной сложности.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Различение общей гарантии и установленного законом объема согласуется со статьей 39 и фильтром личной затронутости статьи 97. Но отсутствие точного размера не лишает конституционную гарантию юридической силы и не исключает контроля закона или бездействия в допустимом производстве; бинарное понижение до «программы» было бы чрезмерным. Пределы: Перед квалификацией нужно проверить все специальные нормы, переходные положения и официальное толкование.; Неопределенность объема не равна отсутствию права и может сама образовывать проблему качества регулирования.; Метод не обещает взыскание и не заменяет анализ компетенции КС РФ и доступного способа защиты.
- **Маршруты:** ksrf-case-triage; ksrf-formal-filing-check; ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-b-cmc-joint-social-program-not-right-02`; legal review `legal-anchor-b-r1-011-cmc-joint-social-program-not-right-02`; source SHA-256 `174883b9917c6bb916e9e9feeada890f05efbfb4f147dee71cf4197c7a7ae5a4`.

<a id="cmc-joint-social-resource-revision-03"></a>
### `cmc-joint-social-resource-revision-03` — Константин Викторович Арановский, Сергей Дмитриевич Князев, Евгений Борисович Хохлов

- **Работа и locator:** О правах человека и социальных правах; печат. 82; PDF 84; раздел Пределы социальных обязательств.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Разделять гарантированное ядро, изменяемую надстройку и законные условия пересмотра социальной меры.
- **Когда полезна:** Размер помощи изменен со ссылкой на ресурсы или конъюнктуру.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Не установлена временная версия закона и момент возникновения права.
- **Оговорки источника:** Ресурсный довод не отменяет защищенное ядро и требования равенства.; Изменение должно следовать правовой процедуре, а не произвольной экономии.
- **Источник не доказывает:** Тезис не доказывает допустимость ретроактивного лишения уже возникшего требования.
- **Фальсификаторы и пределы переноса:** Дефицит бюджета сам по себе не оправдывает любую меру.
- **Контрпример:** Отмена начисленной выплаты задним числом не становится допустимой из-за общей ссылки на кризис.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальные источники поддерживают проверку защищенного содержания, предсказуемости и перехода при изменении социальных мер. Они не закрепляют универсальные категории «ядро» и «надстройка» и не признают ресурсный довод самостоятельным основанием ограничения; допустимость и последствия зависят от конкретной нормы, момента возникновения права и пропорциональности. Пределы: Бюджетный дефицит сам по себе не доказывает конституционность ухудшения.; Нужно различать уже возникшее индивидуальное требование, будущие периоды и общую законодательную политику.; Ретроактивность, равенство групп и достаточность переходного периода проверяются отдельно по официальным источникам.
- **Маршруты:** ksrf-case-triage; ksrf-formal-filing-check; ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-b-cmc-joint-social-resource-revision-03`; legal review `legal-anchor-b-r1-012-cmc-joint-social-resource-revision-03`; source SHA-256 `174883b9917c6bb916e9e9feeada890f05efbfb4f147dee71cf4197c7a7ae5a4`.

<a id="cmc-joint-social-rights-heterogeneity-04"></a>
### `cmc-joint-social-rights-heterogeneity-04` — Константин Викторович Арановский, Сергей Дмитриевич Князев, Евгений Борисович Хохлов

- **Работа и locator:** О правах человека и социальных правах; печат. 82–83; PDF 84–85; раздел Социальные права как родовая общность и российская их перспектива.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Из установленной авторами разнородности компилятор выводит эвристику декомпозиции общего заявления о социальном праве на самостоятельные юридические требования.
- **Когда полезна:** Несколько разных требований объединены общим ярлыком социального права.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Декомпозиция меняет или сужает волеизъявление заявителя без согласования.
- **Оговорки источника:** Часть социальных прав авторы признают фундаментальными и защищаемыми.; Классификация проводится по юридической конструкции, а не престижу блага.
- **Источник не доказывает:** Тезис не допускает общего отказа в защите только из-за социальной природы права.
- **Фальсификаторы и пределы переноса:** Одна жизненная ситуация может порождать несколько разных прав.
- **Контрпример:** Право на конкретную пенсию нельзя смешивать с общей целью повышения благосостояния.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Раздельное описание каждого притязания помогает выполнить требования предметности и личной затронутости и не противоречит многообразию социальных гарантий Конституции. Однако доктринальная типология не является официальной исчерпывающей классификацией, а отсутствие частноправового «контрагента» не позволяет отказать в защите публичного социального права. Пределы: Декомпозиция не должна сужать волеизъявление заявителя или терять взаимосвязь требований.; Каждый элемент нужно сверять со специальным законом и официальной практикой.; Тип конструкции не предрешает допустимость жалобы, нарушение или меру защиты.
- **Маршруты:** ksrf-case-triage; ksrf-formal-filing-check; ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-84f392d0-62a7-45d7-a55d-0b46c5641d22d`; legal review `legal-anchor-b-r1-013-cmc-joint-social-rights-heterogeneity-04`; source SHA-256 `174883b9917c6bb916e9e9feeada890f05efbfb4f147dee71cf4197c7a7ae5a4`.

<a id="cmc-troitskaya-four-stage-test-01"></a>
### `cmc-troitskaya-four-stage-test-01` — Александра Алексеевна Троицкая

- **Работа и locator:** Пределы прав и абсолютные права: за рамками принципа пропорциональности?; печат. 46; PDF 48; раздел 2. Предпосылки применения.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Строить довод по четырем отдельным критериям и запрещать перенос аргумента с одной стадии на другую.
- **Когда полезна:** Норма вмешивается в конституционное право.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Не установлены вмешательство или фактическая цель.
- **Оговорки источника:** В юрисдикциях возможны вариации структуры.; Критерии применяются к установленному вмешательству в право.
- **Источник не доказывает:** Тезис не доказывает, что КС РФ всегда последовательно применяет все четыре стадии.
- **Фальсификаторы и пределы переноса:** Тест неприменим к абсолютному запрету балансирования без отдельного обоснования.
- **Контрпример:** Значимая цель не доказывает необходимость выбранного средства.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальное право прямо поддерживает отдельную проверку цели, необходимости, адекватности и пропорциональности и запрет затрагивать существо права. Но ни статья 55, ни приведенная обязательная мотивировка не превращают это во всех категориях дел в неизменный четырехпунктный алгоритм; применимость зависит от установленного ограничения и природы права. Пределы: Сначала нужно доказать сферу защиты и само вмешательство.; Четыре заголовка не заменяют фактические данные о цели и последствиях меры.; Особые мнения в Постановлении № 8-П/2010 не являются позицией Суда и не могут дополнять binding standard.
- **Маршруты:** ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-troitskaya-four-stage-test-01`; legal review `legal-anchor-b-r1-014-cmc-troitskaya-four-stage-test-01`; source SHA-256 `77df826964fb6c101d6dce2a9d3760cd5bc7d34d1e2f0e9088fa14dd4f0ac4a8`.

<a id="cmc-troitskaya-zero-stage-scope-02"></a>
### `cmc-troitskaya-zero-stage-scope-02` — Александра Алексеевна Троицкая

- **Работа и locator:** Пределы прав и абсолютные права: за рамками принципа пропорциональности?; печат. 47–48; PDF 49–50; раздел 3. Пределы прав.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Сначала доказать охват притязания текстом, целью и системой права, затем переходить к оправданию ограничения.
- **Когда полезна:** Спор идет о том, является ли действие реализацией заявленного права.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Не определено конкретное действие или притязание заявителя.
- **Оговорки источника:** Предел права определяется толкованием его содержания, а не удобством отказа.; Положительная формула права редко исчерпывает все защищаемые возможности.
- **Источник не доказывает:** Тезис не разрешает выводить притязание за сферу защиты только потому, что оно прямо не названо.
- **Фальсификаторы и пределы переноса:** Нулевая стадия не должна скрывать балансирование конкурирующих ценностей.
- **Контрпример:** Отсутствие слова «интернет» в старой норме не исключает цифровое выражение из свободы слова.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Последовательность «содержание права — наличие ограничения — оправдание» реально прослеживается в официальном решении и согласуется со статьей 74. Квалификация как отдельной универсальной стадии остается доктринальной: не всякое дело КС РФ требует теста ограничений, а объем права устанавливается конкретным официальным толкованием. Пределы: Отсутствие буквального упоминания новой технологии или способа реализации не исключает охват правом.; На стадии охвата нельзя скрыто переносить аргументы о пользе или удобстве ограничения.; Вывод о сфере права должен опираться на применимое официальное толкование, факты и предмет жалобы.
- **Маршруты:** ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-troitskaya-zero-stage-scope-02`; legal review `legal-anchor-b-r1-015-cmc-troitskaya-zero-stage-scope-02`; source SHA-256 `77df826964fb6c101d6dce2a9d3760cd5bc7d34d1e2f0e9088fa14dd4f0ac4a8`.

<a id="cmc-troitskaya-cautious-right-limits-03"></a>
### `cmc-troitskaya-cautious-right-limits-03` — Александра Алексеевна Троицкая

- **Работа и locator:** Пределы прав и абсолютные права: за рамками принципа пропорциональности?; печат. 49–50; PDF 51–52; раздел 3. Пределы прав.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Проводить hard-negative проверку: не маскирует ли узкое определение права неявное взвешивание.
- **Когда полезна:** Притязание исключено из права с опорой на общественный интерес.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Нельзя восстановить реальные основания исключения притязания.
- **Оговорки источника:** Предел может следовать из текста, истории, цели, системы и социальных фактов.; Сумеречные случаи требуют более щедрого определения сферы защиты.
- **Источник не доказывает:** Тезис не требует включать в право любое заявленное действие.
- **Фальсификаторы и пределы переноса:** Осторожность не отменяет явные негативные пределы текста.
- **Контрпример:** Категория речи не должна исключаться из защиты только потому, что государство считает ее вредной.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Официальное решение подтверждает необходимость не смешивать определение содержания права с оправданием ограничения и проверять реальное затрагивание гарантий. Авторская hard-negative эвристика полезна против скрытого баланса, однако официальное право не требует переносить в пропорциональность всякое спорное определение пределов права. Пределы: Явный текстовый запрет или предел права нельзя отменить одной гипотезой о защитной ценности действия.; Конкурирующая ценность должна быть показана по фактам и официальным основаниям, а не предполагаться.; Тест не предрешает, что спорное действие охватывается правом или что ограничение неконституционно.
- **Маршруты:** ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-troitskaya-cautious-right-limits-03`; legal review `legal-anchor-b-r1-016-cmc-troitskaya-cautious-right-limits-03`; source SHA-256 `77df826964fb6c101d6dce2a9d3760cd5bc7d34d1e2f0e9088fa14dd4f0ac4a8`.

<a id="cmc-troitskaya-absolute-right-04"></a>
### `cmc-troitskaya-absolute-right-04` — Александра Алексеевна Троицкая

- **Работа и locator:** Пределы прав и абсолютные права: за рамками принципа пропорциональности?; печат. 51–52; PDF 53–54; раздел 3. Абсолютные права.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** До балансирования проверять наличие независимо обоснованного абсолютного запрета и точно очерчивать его предмет.
- **Когда полезна:** Ограничение затрагивает возможный неотступаемый аспект права.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Абсолютность выведена только из доктрины без официальной проверки.
- **Оговорки источника:** Абсолютность может принадлежать узкому аспекту права, а не всему праву.; Круг абсолютных гарантий требует самостоятельного этического и системного обоснования.
- **Источник не доказывает:** Тезис не доказывает абсолютность конкретного права одним его высоким статусом.
- **Фальсификаторы и пределы переноса:** Расширение абсолютного ядра увеличивает риск конфликтов абсолютов и требует строгой аргументации.
- **Контрпример:** Не всякое затрагивание права на достоинство автоматически попадает в абсолютный запрет без определения аспекта.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Категорический текст статьи 21 поддерживает остановку балансирования после установления вмешательства в точный запрет. Но статья 56 часть 3 регулирует специальный режим чрезвычайного положения, а доктринальное понятие «абсолютного аспекта» шире официальных формул; для каждого случая нужен самостоятельный действующий источник и точное определение охвата. Пределы: Нельзя объявлять абсолютным все право только из-за наличия в нем одного категорического запрета.; Статья 56 часть 3 не переносится автоматически из режима чрезвычайного положения на любую обычную ситуацию.; Факт вмешательства и принадлежность к точному абсолютному аспекту требуют отдельного доказательства.
- **Маршруты:** ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-troitskaya-absolute-right-04`; legal review `legal-anchor-b-r1-017-cmc-troitskaya-absolute-right-04`; source SHA-256 `77df826964fb6c101d6dce2a9d3760cd5bc7d34d1e2f0e9088fa14dd4f0ac4a8`.

<a id="cmc-troitskaya-three-zones-qa-05"></a>
### `cmc-troitskaya-three-zones-qa-05` — Александра Алексеевна Троицкая

- **Работа и locator:** Пределы прав и абсолютные права: за рамками принципа пропорциональности?; печат. 63–64; PDF 65–66; раздел 5. Заключение.
- **Статус:** source `passed/keep`; legal `illustrative/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Ввести трехзонную маркировку каждого притязания и QA-запрет на переход между зонами без отдельной аргументации.
- **Когда полезна:** Проект смешивает отсутствие права, допустимое ограничение и абсолютный запрет.
- **Предусловия:** Определены конкретное право, спорное притязание и процессуальная цель анализа.
- **Остановиться или воздержаться:** Классификация основана только на желаемом результате дела.
- **Оговорки источника:** Первая и третья зоны не должны выводиться из скрытого предположения о неизбежном проигрыше или выигрыше.; Автор критикует непоследовательное применение этих категорий в практике КС РФ.
- **Источник не доказывает:** Тезис не предоставляет готовый перечень абсолютных прав или пределов каждого права.
- **Фальсификаторы и пределы переноса:** Зоны зависят от конкретного права и не переносятся автоматически.
- **Контрпример:** Называть притязание абсолютным после выгодного балансирования — круговая аргументация.
- **Не использовать для:** Выдать доктринальный тезис за действующее право или обещание исхода дела.
- **Российская правовая граница:** Три аналитические зоны удобно напоминают о разных вопросах охвата, ограничения и категорического запрета. Это не официальный тест: границы зависят от конкретного права, статья 56 имеет специальный контекст, а обязательный формат мотивировки определяется применимыми нормами и решениями, а не доктринальной таблицей. Пределы: Маркировка должна оставаться прозрачной аналитической эвристикой, а не ссылкой на якобы установленный КС РФ тест.; Крайние зоны требуют конкретного официального источника и не выводятся из удобства классификации.; Средняя зона не всегда требует одинакового набора стадий, если спор не касается ограничения права.
- **Маршруты:** ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-b-cmc-troitskaya-three-zones-qa-05`; legal review `legal-anchor-b-r1-018-cmc-troitskaya-three-zones-qa-05`; source SHA-256 `77df826964fb6c101d6dce2a9d3760cd5bc7d34d1e2f0e9088fa14dd4f0ac4a8`.

<a id="cmc-vitruk-echr-nonautomatic-use-01"></a>
### `cmc-vitruk-echr-nonautomatic-use-01` — Николай Васильевич Витрук

- **Работа и locator:** О некоторых особенностях использования решений Европейского Суда по правам человека в практике Конституционного Суда Российской Федерации и иных судов; печат. 86; PDF 87; раздел Абзацы о творческом этапе учета и допустимости использования правовых позиций ЕСПЧ.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Перед использованием позиции ЕСПЧ составить отдельную карту переносимости, а не ограничиваться тематическим совпадением с жалобой.
- **Когда полезна:** В проекте жалобы приводится постановление ЕСПЧ как поддержка конституционного довода.
- **Предусловия:** Доступен полный или надежно извлеченный текст постановления ЕСПЧ.; Выделена правовая позиция, а не только итог по делу.; Определены факты и примененная норма российского дела.
- **Остановиться или воздержаться:** Нет надежного текста постановления или невозможно отделить позицию суда от доводов стороны.; Существенные факты либо институциональный контекст различаются, а их влияние не объяснено.; Не проверено последующее развитие позиции.
- **Оговорки источника:** Тезис сформулирован применительно к практике учета позиций ЕСПЧ российскими правоприменителями в 2006 году.; Автор отдельно требует проверить допустимость переноса с учетом индивидуальных фактов и национально-правового контекста.
- **Источник не доказывает:** Тезис не доказывает современную обязательность конкретного постановления ЕСПЧ для Российской Федерации.; Тезис не позволяет переносить вывод одного дела без сопоставления фактов, нормы и развития практики.
- **Фальсификаторы и пределы переноса:** Более позднее постановление изменяет или ограничивает выбранную позицию.; Иная правовая квалификация ключевых фактов разрушает заявленную аналогию.; Российская процессуальная конструкция не допускает предлагаемого способа использования довода.
- **Контрпример:** Одинаковое упоминание права на справедливое судебное разбирательство не делает переносимым постановление, если в нем решался иной процессуальный дефект и иная стадия производства.
- **Не использовать для:** Не устанавливать таким путем действующее российское право.; Не обещать принятие жалобы или требуемый исход.; Не подменять проверку российской нормы пересказом практики ЕСПЧ.
- **Российская правовая граница:** Карта ratio и фактов остается добросовестной техникой сравнительного анализа, но прежняя нормативная предпосылка статьи 2010 года существенно изменилась после 2022–2023 годов. На 14.08.2026 позиция ЕСПЧ не может подаваться как автоматически применимый текущий российский стандарт или источник обязательного remedy; возможная сравнительная роль должна быть обозначена прямо. Пределы: Сначала нужно установить временной статус постановления ЕСПЧ и применимый переходный режим.; Сравнительный довод не заменяет действующую российскую норму и не расширяет компетенцию КС РФ.; Нельзя обещать исполнение, пересмотр или компенсацию только из ссылки на ЕСПЧ.
- **Маршруты:** ksrf-echr-argumentation; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-path-r2-cmc-vitruk-echr-nonautomatic-use-01`; legal review `legal-anchor-b-r1-019-cmc-vitruk-echr-nonautomatic-use-01`; source SHA-256 `3fed4c1ba604a47c35edaa86f07ff0aacb5487a8653e75eb7f5616b268f34360`.

<a id="cmc-vitruk-effect-execution-distinction-02"></a>
### `cmc-vitruk-effect-execution-distinction-02` — Николай Васильевич Витрук

- **Работа и locator:** О некоторых особенностях использования решений Европейского Суда по правам человека в практике Конституционного Суда Российской Федерации и иных судов; печат. 85; PDF 86; раздел Абзацы о непосредственном действии и исполнении решения ЕСПЧ.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При анализе исполнения судебного решения разносить по разным полям его юридическое действие, индивидуальные меры, общие меры и фактическое завершение каждой меры.
- **Когда полезна:** В материалах дела утверждается, что решение действует или исполнено, но не раскрыты фактически принятые меры.
- **Предусловия:** Установлен точный текст резолютивной части решения.; Определены адресаты и требуемые действия.; Доступны документы о принятых мерах.
- **Остановиться или воздержаться:** Не установлен обязательный текст решения или его адресат.; Нет доказательств фактических мер, а вывод строится только на принятии нового акта.; Современный правовой режим исполнения не проверен.
- **Оговорки источника:** Разграничение изложено в доктринальной статье 2006 года.; Автор отмечает различие между обязательностью компенсации и усмотрением государства в выборе общих мер.
- **Источник не доказывает:** Тезис не подтверждает, что конкретное решение исполнено фактически.; Тезис не определяет современную процедуру исполнения решений международных судов в России.
- **Фальсификаторы и пределы переноса:** Решение не требует заявленных составителем общих мер.; Представленные документы подтверждают лишь формальное издание акта, но не устранение нарушения.; Иной компетентный орган официально определил иной объем исполнения.
- **Контрпример:** Публикация нормативной поправки не доказывает исполнение решения, если заявителю не предоставлена требуемая индивидуальная мера и прежняя практика продолжается.
- **Не использовать для:** Не считать юридическое действие автоматическим доказательством исполнения.; Не выводить конкретный remedy без текста решения.; Не обещать восстановление права или исход жалобы.
- **Российская правовая граница:** Разделение юридического действия и последующего исполнения прямо закреплено для решений КС РФ и потому поддерживает структуру карты. Конкретные категории компенсации, индивидуальных и общих мер из прежней конвенционной модели нельзя автоматически переносить на КС РФ или на текущий статус ЕСПЧ; каждую меру определяют резолютивная часть и действующий закон. Пределы: Нужно сначала определить орган, вид решения, дату и применимый правовой режим.; Наличие обязанности принять общий акт не доказывает предоставление индивидуального remedy, и наоборот.; Составитель не вправе приписывать решению меры, которых нет в его резолютивной части или действующем законе.
- **Маршруты:** ksrf-echr-argumentation; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-path-r2-cmc-vitruk-effect-execution-distinction-02`; legal review `legal-anchor-b-r2-020-cmc-vitruk-effect-execution-distinction-02`; source SHA-256 `3fed4c1ba604a47c35edaa86f07ff0aacb5487a8653e75eb7f5616b268f34360`.

<a id="cmc-brezhnev-combined-dispute-test-01"></a>
### `cmc-brezhnev-combined-dispute-test-01` — Олег Брежнев

- **Работа и locator:** Конституционно-правовые споры как явления современной действительности (генезис, содержание, порядок разрешения); печат. 4; PDF 4; раздел Абзацы о формальном и материально-правовом подходах к определению конституционно-правового спора.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При первичном triage строить двухосевую проверку: сначала материальная конституционная природа разногласия, затем компетенция и специальная процедура его разрешения.
- **Когда полезна:** Заявитель связывает отраслевой спор с Конституцией или предполагает обращение в КС РФ.
- **Предусловия:** Определены стороны, предмет и спорная норма.; Известна процессуальная история дела.; Установлены доступные способы судебной защиты.
- **Остановиться или воздержаться:** Не установлена примененная норма или предмет разногласия.; Конституционная ссылка носит только риторический характер.; Не проверены компетенция и специальный порядок разрешения.
- **Оговорки источника:** Материальный блок включает субъектный состав и предмет отношений.; Формальный блок относится к специальному порядку разрешения спора.
- **Источник не доказывает:** Применение Конституции судом общей юрисдикции само по себе не превращает любой спор в конституционно-правовой.; Квалификация спора не доказывает допустимость конкретной жалобы в КС РФ.
- **Фальсификаторы и пределы переноса:** Предмет спора исчерпывается установлением фактов или применением отраслевой нормы без самостоятельного конституционного вопроса.; Закон относит спор к иному органу и отсутствует предмет конституционного нормоконтроля.; Материальная и формальная квалификации расходятся и это расхождение не разрешено.
- **Контрпример:** Трудовой спор не становится конституционно-правовым только потому, что сторона сослалась на конституционное право на труд и суд применил Конституцию наряду с трудовым законом.
- **Не использовать для:** Не подменять анализ допустимости общим утверждением о важности права.; Не переоценивать факты как сверхинстанционный суд.; Не обещать принятие обращения КС РФ.
- **Российская правовая граница:** Раздельная проверка содержания вопроса и законного процессуального маршрута точно согласуется с ФКЗ и полезна для triage. Однако «материальный конституционный спор» не является самостоятельным входом в КС РФ: решающими остаются конкретный вид производства, надлежащий субъект, оспариваемый нормативный акт и условия допустимости. Пределы: Конституционная лексика в отраслевом или фактическом споре не создает компетенцию КС РФ.; Расхождение двух осей нельзя разрешать в пользу желаемого форума без прямой нормы.; Метод не определяет автоматически remedy и не заменяет исчерпание внутригосударственных средств по статье 97.
- **Маршруты:** ksrf-case-triage; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-path-r2-cmc-brezhnev-combined-dispute-test-01`; legal review `legal-anchor-b-r2-021-cmc-brezhnev-combined-dispute-test-01`; source SHA-256 `89743a5651316d2a58766d7db952916904b6ee9c1c2ac536867fae9ac1600d9a`.

<a id="cmc-varlamova-conceptual-baseline-01"></a>
### `cmc-varlamova-conceptual-baseline-01` — Наталия Владимировна Варламова

- **Работа и locator:** Права человека: попытки интегративной интерпретации; печат. 99; PDF 101; раздел Вводные абзацы о корреляции типов правопонимания и теорий прав человека.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При сопоставлении конкурирующих правовых аргументов сначала раскрывать концептуальные предпосылки каждого, а затем сравнивать выводы.
- **Когда полезна:** В одном доводе объединены источники разных школ или юрисдикций под общей формулой права.
- **Предусловия:** Определены цитируемые источники и их говорящие.; Выделено предлагаемое каждым источником содержание права.; Зафиксирован предмет ограничения или защиты.
- **Остановиться или воздержаться:** Нельзя установить собственную позицию автора и она смешана с цитируемым мнением.; Совместимость основана только на одинаковых словах.; Не объяснено, как различия влияют на вывод по делу.
- **Оговорки источника:** Тезис относится к теоретической интерпретации прав человека.; Автор критически относится к интеграции подходов без учета их концептуальных оснований.
- **Источник не доказывает:** Тезис не устанавливает единственно правильную концепцию прав человека.; Совпадение терминов в двух источниках не доказывает совпадение нормативного содержания.
- **Фальсификаторы и пределы переноса:** Источники прямо одинаково определяют происхождение, пределы и защиту права.; Различие школ не влияет на рассматриваемый узкий вопрос.; Составитель приписывает автору взгляды цитируемого им оппонента.
- **Контрпример:** Два источника признают право на свободу, но один понимает его как предоставленное государством полномочие, а другой — как предел государственной власти; их нельзя считать взаимозаменяемыми без оговорки.
- **Не использовать для:** Не объявлять одну школу действующим правом.; Не смешивать позицию автора с цитируемыми теориями.; Не обещать исход жалобы.
- **Российская правовая граница:** Выявление несовместимых предпосылок может предотвратить логический эклектизм, но это исследовательская эвристика. Текущий официальный стандарт требует привязки к Конституции, примененной норме и ее действительному смыслу; происхождение аргумента из определенной школы само по себе не определяет юридическую силу или исход. Пределы: Нельзя приписывать источнику концепцию без прямого текста и контекста.; Различие теорий можно опустить, если оно не влияет на конкретный нормативный вопрос.; Концептуальный мост не заменяет официальный российский источник, компетенцию и remedy-анализ.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-path-r2-cmc-varlamova-conceptual-baseline-01`; legal review `legal-anchor-b-r1-023-cmc-varlamova-conceptual-baseline-01`; source SHA-256 `1658a35eb9467c3dad1a5eb74142be364985f0dd91b0b2c66d137f990f0486a4`.

<a id="cmc-varlamova-rights-guarantee-fit-02"></a>
### `cmc-varlamova-rights-guarantee-fit-02` — Наталия Владимировна Варламова

- **Работа и locator:** Права человека: попытки интегративной интерпретации; печат. 106; PDF 108; раздел Заключительный вывод о смешении объективно различных прав.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Для каждого заявленного права отдельно проверять юридическую природу, адресата обязанности, необходимую меру и судебную защитимость, прежде чем объединять требования.
- **Когда полезна:** Один аргумент применяет одинаковую модель обязанности или remedy к разным правам.
- **Предусловия:** Перечислены все заявленные права.; Определены фактические вмешательства и требуемые меры.; Доступны официальные нормы о защите каждого права.
- **Остановиться или воздержаться:** Не установлен юридический характер заявленного притязания.; Предлагаемый remedy не связан с конкретной обязанностью.; Разные права объединены только риторически.
- **Оговорки источника:** Вывод сделан на материале европейских актов и отражает авторскую классификацию прав.; Для разных прав автор предполагает разные характер обязательств и механизмы защиты.
- **Источник не доказывает:** Тезис не доказывает невозможность совместного закрепления разных категорий прав вообще.; Тезис не определяет действующие гарантии конкретного российского права.
- **Фальсификаторы и пределы переноса:** Действующее право устанавливает единый механизм защиты для рассматриваемых прав.; Различия не влияют на предмет и требование конкретной жалобы.; Классификация основана лишь на доктринальном ярлыке без официального подтверждения.
- **Контрпример:** Требование немедленно предоставить ресурсную социальную услугу нельзя обосновывать ровно тем же способом, что требование прекратить прямой запрет выражения мнения, без анализа разных обязанностей и средств защиты.
- **Не использовать для:** Не ранжировать ценность прав.; Не отрицать защитимость права только по его категории.; Не обещать конкретный remedy.
- **Российская правовая граница:** Пообъектная проверка прав, примененных норм и последствий соответствует индивидуализации жалобы и предотвращает смешение remedies. Но негативные, позитивные и институциональные обязанности являются аналитическими категориями, а официальный способ защиты определяется текстом конкретного права, законом, компетенцией суда и видом решения. Пределы: Доктринальный ярлык обязанности не может заменять официальный источник ее содержания.; Различия нужно фиксировать лишь в той мере, в какой они влияют на предмет и требование.; Совместное изложение допустимо при общей примененной норме и связи, но не обещает общий remedy.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-path-r2-cmc-varlamova-rights-guarantee-fit-02`; legal review `legal-anchor-b-r1-024-cmc-varlamova-rights-guarantee-fit-02`; source SHA-256 `1658a35eb9467c3dad1a5eb74142be364985f0dd91b0b2c66d137f990f0486a4`.

<a id="cmc-lapaeva-conventional-standards-audit-02"></a>
### `cmc-lapaeva-conventional-standards-audit-02` — Валентина Лапаева

- **Работа и locator:** Правовая демократия как цивилизационный выбор России (с позиций либертарного правопонимания); печат. 157; PDF 158; раздел Абзац о формальном равенстве как критерии оценки конвенциональных правовых регуляторов.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Используя международный или сравнительный стандарт, отдельно проверять его формальное основание, содержательный критерий равенства и применимость к российскому контексту.
- **Когда полезна:** Стандарт предлагается как самоочевидный и не анализируются его основания и последствия.
- **Предусловия:** Установлен точный текст стандарта.; Определен его официальный статус.; Выявлены затрагиваемые группы и правовые последствия.
- **Остановиться или воздержаться:** Не установлен официальный статус стандарта.; Критика подменяет юридический анализ неприятием источника.; Нет данных для оценки затронутых групп и последствий.
- **Оговорки источника:** Это вывод либертарного правопонимания, а не официальная норма.; Автор использует критерий для критической оценки международно вырабатываемых стандартов.
- **Источник не доказывает:** Доктринальный критерий не отменяет юридическую силу применимого официального источника.; Тезис не разрешает игнорировать обязательный стандарт из-за несогласия с ним.
- **Фальсификаторы и пределы переноса:** Применимый официальный источник прямо обязателен и не допускает предлагаемого отступления.; Формальное равенство использовано без определения общего масштаба.; Доктринальная критика не влияет на узкий правовой вопрос дела.
- **Контрпример:** Нельзя отклонить обязательное правило только потому, что составитель считает иной баланс более равным; сначала нужно установить юридический статус и допустимые способы толкования правила.
- **Не использовать для:** Не отрицать обязательность официального права доктринальной критикой.; Не выдавать теорию за позицию КС РФ.; Не обещать исход жалобы.
- **Российская правовая граница:** Официальное право прямо требует установить источник, статус и конституционные пределы международного материала, что поддерживает первую и третью части аудита. Формальное равенство как универсальный содержательный метакритерий является авторской доктриной; оно не позволяет отклонить обязательную норму или подменить конкретный конституционный стандарт. Пределы: Для каждого материала нужно фиксировать договор, дату, обязательность и переходный режим.; Доктринальная критика не отменяет действующий обязательный источник.; Сравнительный стандарт не создает компетенцию или remedy, отсутствующие в российском законе.
- **Маршруты:** ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-c-r1-lapaeva-conventional-standards-audit-02`; legal review `legal-anchor-b-r1-026-cmc-lapaeva-conventional-standards-audit-02`; source SHA-256 `7bc7ba68f5662924fde1cca533047c98bc0c05b538150e7b746a2e5c71746772`.

<a id="cmc-dzhagaryan-act-specific-quality-01"></a>
### `cmc-dzhagaryan-act-specific-quality-01` — Армен Джагарян

- **Работа и locator:** Вмененная безупречность: решения Конституционного Суда Российской Федерации и правовое качество. Ответ на статью А. Петрова; печат. 113; PDF 115; раздел Раздел 1, абзац о пределах универсализации категории правового качества.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Перед оценкой акта определять его тип, функцию, юридическую силу и институциональный режим, а критерии переносить только после проверки совместимости.
- **Когда полезна:** Одна универсальная шкала качества применяется к разным видам юридических актов.
- **Предусловия:** Определен вид оцениваемого акта.; Установлены его юридическая сила и функция.; Известен источник предлагаемых критериев.
- **Остановиться или воздержаться:** Тип и статус акта не установлены.; Критерий заимствован из иной категории без обоснования.; Оценка качества смешана с выводом о юридической недействительности.
- **Оговорки источника:** Тезис развит в полемике об оценке решений КС РФ.; Автор связывает ошибку универсализации с размыванием различий и правовой субординации.
- **Источник не доказывает:** Тезис не запрещает сравнительный анализ разных видов актов.; Тезис не устанавливает конкретный перечень критериев для каждого вида акта.
- **Фальсификаторы и пределы переноса:** Закон прямо устанавливает единый критерий для обеих категорий актов.; Сравниваемый критерий относится к общему атрибуту и совместимость доказана.; Классификация акта составителем ошибочна.
- **Контрпример:** Критерии качества закона нельзя автоматически превращать в шкалу юридической действительности итогового решения КС РФ, не учитывая его особый статус и режим окончательности.
- **Не использовать для:** Не объявлять акт недействительным по экспертной шкале.; Не исключать профессиональную критику.; Не обещать процессуальный результат.
- **Российская правовая граница:** Специальный официальный режим решения КС РФ подтверждает необходимость сначала классифицировать акт и отделить обязательный эффект от внешней оценки качества. Универсальный метатест совместимости критериев остается доктринальным; отдельные общие критерии могут применяться, если это прямо обосновано и не переопределяет юридическую силу. Пределы: Неверная классификация акта делает дальнейший перенос критериев ненадежным.; Экспертная шкала не изменяет действительность, обязательность и remedy сама по себе.; Общий критерий допустим только при доказанной совместимости с функцией и режимом конкретного акта.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-decision-execution.
- **Provenance:** source review `source-review-c-path-r2-cmc-dzhagaryan-act-specific-quality-01`; legal review `legal-anchor-b-r1-027-cmc-dzhagaryan-act-specific-quality-01`; source SHA-256 `8ca7bbb13c5379b96b2bd2731fc5a4fce552709656413a816a9798528c63313e`.

<a id="cmc-kryazhkov-ideal-empirical-institution-01"></a>
### `cmc-kryazhkov-ideal-empirical-institution-01` — Владимир Алексеевич Кряжков

- **Работа и locator:** Региональная конституционная юстиция в Российской Федерации: состояние и пути развития; печат. 157; PDF 158; раздел Раздел «Ценность конституционных (уставных) судов», заключительная оговорка.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** В институциональном анализе вести раздельные колонки для нормативного назначения, наблюдаемой практики и контекстных ограничений.
- **Когда полезна:** Заявленное назначение института используется как доказательство его фактической эффективности.
- **Предусловия:** Определено нормативное назначение института.; Доступны данные о его практике.; Выявлены релевантные политико-правовые ограничения.
- **Остановиться или воздержаться:** Нет эмпирических данных, но заявлен вывод об эффективности.; Идеальная модель приписана институту без нормативного основания.; Контекстные факторы подменяют доказательство причинности.
- **Оговорки источника:** Оговорка относится к региональным конституционным (уставным) судам.; Эмпирическую проверку автор далее проводит статистикой обращений и решений.
- **Источник не доказывает:** Идеальная функция института не доказывает ее фактическое достижение.; Отдельный недостаток практики не опровергает всю институциональную модель.
- **Фальсификаторы и пределы переноса:** Показатели не измеряют заявленную функцию.; Выборка решений нерепрезентативна.; Более полные данные опровергают заявленное расхождение.
- **Контрпример:** Наличие у суда полномочия защищать права не доказывает доступность защиты, если не исследованы обращения граждан, принятые решения и их исполнение.
- **Не использовать для:** Не выдавать ценностную модель за факт.; Не отрицать институт по одному примеру.; Не обещать результат обращения.
- **Российская правовая граница:** Официальные нормы дают воспроизводимую нормативную колонку, а официальная статистика может снабжать часть наблюдаемых данных. Само трехколоночное исследование, выбор показателей и причинный анализ не являются правилом действующего права и не могут использоваться для расширения компетенции или вывода по отдельной жалобе. Пределы: Показатель должен реально измерять заявленную функцию и иметь указанную выборку и период.; Нормативное полномочие не доказывает доступность или фактическое исполнение.; Эмпирическая корреляция не устанавливает причину без отдельного дизайна и данных.
- **Маршруты:** ksrf-argument-patterns; ksrf-decision-execution.
- **Provenance:** source review `source-review-c-path-r2-cmc-kryazhkov-ideal-empirical-institution-01`; legal review `legal-anchor-b-r2-029-cmc-kryazhkov-ideal-empirical-institution-01`; source SHA-256 `46da7431082a4ff8087a2099a82f8c77800570817804543713341431e951b7af`.

<a id="cmc-kryazhkov-nonhierarchical-competence-02"></a>
### `cmc-kryazhkov-nonhierarchical-competence-02` — Владимир Алексеевич Кряжков

- **Работа и locator:** Региональная конституционная юстиция в Российской Федерации: состояние и пути развития; печат. 161; PDF 162; раздел Критика идеи иерархической системы конституционной юстиции.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Перед ссылкой на другой суд проверять не ранг органа, а его предметную компетенцию, масштаб проверки и юридический канал влияния решения.
- **Когда полезна:** Решение одного конституционного суда представляется как акт вышестоящей или нижестоящей инстанции без правового основания.
- **Предусловия:** Установлен статус каждого суда.; Определены предмет и масштаб проверки.; Известен юридический эффект решения.
- **Остановиться или воздержаться:** Не проверен современный статус органа.; Инстанционная связь предполагается по названию суда.; Не установлен предмет исходного решения.
- **Оговорки источника:** Тезис относится к институциональной модели, существовавшей на момент публикации.; КС РФ не наделялся автором апелляционными, кассационными или надзорными полномочиями над региональными судами.
- **Источник не доказывает:** Раздельная компетенция не исключает нормативного взаимодействия правовых позиций.; Исторический тезис не подтверждает современное существование региональных конституционных судов.
- **Фальсификаторы и пределы переноса:** Действующее право прямо установило инстанционную связь.; Решение имеет специальный общеобязательный эффект для другого органа.; Сравниваемые органы проверяли разные нормы и аналогия не объяснена.
- **Контрпример:** Нельзя называть КС РФ кассационной инстанцией по отношению к иному конституционному органу только потому, что оба рассматривают вопросы конституционности.
- **Не использовать для:** Не отрицать все формы влияния судебной практики.; Не выдумывать инстанционное обжалование.; Не обещать принятие жалобы.
- **Российская правовая граница:** Компетенционно-ориентированный метод остается верным и защищает от выдуманной инстанционной связи. Конкретная исходная пара федерального и региональных конституционных судов исторически устарела после обязательного упразднения последних; карточку можно использовать только после замены примера на действующие органы и проверки точного эффекта их актов. Поэтому временная ось квалифицирована, а не провалена: действующий компетенционный прием сохраняется после обязательной замены упраздненного институционального примера. Пределы: Нельзя описывать региональные конституционные и уставные суды как действующий на 14.08.2026 уровень судебной системы.; Конституционные советы при законодательных органах, если созданы, не тождественны судам и требуют собственного статуса.; Аналогическая ссылка не создает обязательность, пересмотр или подведомственность без прямой нормы.
- **Маршруты:** ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-path-r2-cmc-kryazhkov-nonhierarchical-competence-02`; legal review `legal-anchor-b-r2-030-cmc-kryazhkov-nonhierarchical-competence-02`; source SHA-256 `46da7431082a4ff8087a2099a82f8c77800570817804543713341431e951b7af`.

<a id="cmc-mityukov-multifactor-execution-02"></a>
### `cmc-mityukov-multifactor-execution-02` — Михаил Митюков

- **Работа и locator:** Конституционные суды постсоветских государств: проблемы исполнения решений; печат. 73; PDF 75; раздел Заключительный абзац перед выводами.
- **Статус:** source `passed/keep`; legal `illustrative/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** План исполнения должен включать правовые обязанности и процедуры, организационных владельцев, ресурсы, публичную отчетность и контроль фактического результата.
- **Когда полезна:** Неисполнение объясняется одной причиной либо предлагается только санкция или только просветительская мера.
- **Предусловия:** Установлены обязательные действия.; Определены ответственные органы.; Собраны данные о фактических барьерах.
- **Остановиться или воздержаться:** Объем обязательства не установлен.; Причина задержки предполагается без доказательств.; Предлагаемая мера выходит за компетенцию адресата.
- **Оговорки источника:** Тезис выражает авторский вывод из сравнительного обзора постсоветских государств.; Источник не утверждает наличие одного гарантированного механизма исполнения.
- **Источник не доказывает:** Правовой механизм сам по себе не гарантирует фактическое исполнение.; Политические факторы не освобождают адресатов от юридических обязанностей.
- **Фальсификаторы и пределы переноса:** Документы показывают чисто техническую задержку, не требующую многоканального вмешательства.; Предлагаемая неправовая мера противоречит обязательному юридическому режиму.; Индикаторы не измеряют устранение выявленного дефекта.
- **Контрпример:** Угроза санкции не устраняет неисполнение, вызванное отсутствием ответственного процесса и необходимых данных, но организационная мера также не заменяет обязательную нормативную поправку.
- **Не использовать для:** Не оправдывать неисполнение политикой.; Не сводить план к наказанию.; Не обещать фактическое завершение исполнения.
- **Российская правовая граница:** Закон дает юридический минимум — обязательность, отдельных ответственных субъектов и сроки, — но не тот же операциональный стандарт. Организационные владельцы, ресурсы, политические барьеры, публичная отчетность и индикаторы остаются управленческой эвристикой. Их можно сохранить после редакции как необязательные поддерживающие меры, отдельно от юридических обязанностей. Пределы: Неправовые меры не заменяют обязательную нормативную или процессуальную меру.; Публичная отчетность, ресурсное обеспечение и индикаторы требуют самостоятельного правового или организационного основания для каждого адресата.; Многофакторное объяснение не оправдывает неисполнение и не расширяет компетенцию КС РФ.
- **Маршруты:** ksrf-decision-execution; ksrf-complaint-cycle.
- **Provenance:** source review `source-review-c-path-r2-cmc-mityukov-multifactor-execution-02`; legal review `legal-anchor-b-r1-032-cmc-mityukov-multifactor-execution-02`; source SHA-256 `0fc093ecb43ea98a1bfe354f1dec5deed06fe9999363d399fb7ec321951bad2a`.

<a id="cmc-gritsenko-comparative-reception-gate-01"></a>
### `cmc-gritsenko-comparative-reception-gate-01` — Елена Владимировна Гриценко

- **Работа и locator:** В поисках утраченных идеалов: российская муниципальная реформа и опыт Германии; печат. 18; PDF 20; раздел Введение, абзац о глубоком понимании и допустимости рецепции.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Перед использованием зарубежной модели проходить reception gate: функция, институты, компетенция, контекст, правовое основание и адаптация.
- **Когда полезна:** Зарубежное решение предлагается как готовый образец российской реформы или толкования.
- **Предусловия:** Доступен первичный зарубежный источник.; Определена функция сравниваемого института.; Описана российская целевая конструкция.
- **Остановиться или воздержаться:** Нет первичного текста зарубежной модели.; Совпадение основано только на названии института.; Ключевые различия компетенции или гарантий не исследованы.
- **Оговорки источника:** Тезис сформулирован на сравнении местного самоуправления России и Германии.; Общие исторические связи и принципы не устраняют существенных различий моделей.
- **Источник не доказывает:** Сходство целей реформ не доказывает переносимость средств.; Различия систем не делают всякое сравнительное заимствование недопустимым.
- **Фальсификаторы и пределы переноса:** Контекстное условие, определяющее результат, отсутствует в российской системе.; Заимствование противоречит обязательной российской норме.; Более близкий функциональный аналог опровергает выбранное сравнение.
- **Контрпример:** Нельзя переносить немецкую конструкцию муниципального органа только по сходству задач, если в системах различаются правосубъектность, уровень государственной интеграции и судебная защита.
- **Не использовать для:** Не использовать зарубежный опыт как действующее российское право.; Не отвергать сравнение из-за любого различия.; Не обещать успешность реформы.
- **Российская правовая граница:** Официальная норма подтверждает лишь предел: сравнительный материал не меняет предмет и компетенцию КС РФ. Сама многоэлементная матрица рецепции остается сравнительно-правовой методикой; юридическая допустимость результата должна подтверждаться отдельными российскими источниками. Пределы: Зарубежная норма или институциональная практика не является действующим российским правом сама по себе.; Сопоставимость функции не доказывает совпадение компетенции, гарантий или доступного remedy.; Матрица не расширяет предмет жалобы и полномочия КС РФ.
- **Маршруты:** ksrf-argument-patterns; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-c-path-r2-cmc-gritsenko-comparative-reception-gate-01`; legal review `legal-anchor-b-r1-033-cmc-gritsenko-comparative-reception-gate-01`; source SHA-256 `0f24c493dd129c2db469029a12c4199d7c011a380f93497306b98c406a42791c`.

<a id="cmc-gritsenko-contextual-option-generation-02"></a>
### `cmc-gritsenko-contextual-option-generation-02` — Елена Владимировна Гриценко

- **Работа и locator:** В поисках утраченных идеалов: российская муниципальная реформа и опыт Германии; печат. 36; PDF 38; раздел Заключительный абзац статьи.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Использовать сравнительный корпус сначала для генерации нескольких вариантов, затем фильтровать их по контексту и российским правовым ограничениям.
- **Когда полезна:** Рассматривается только один зарубежный образец либо он предлагается без альтернатив.
- **Предусловия:** Сформулирована функция, которую нужно обеспечить.; Собраны несколько сопоставимых моделей.; Определены российские ограничения и ресурсы.
- **Остановиться или воздержаться:** Нет нескольких моделей или функционального описания.; Контекстные данные отсутствуют.; Выбранный вариант противоречит обязательному российскому праву.
- **Оговорки источника:** Вывод сделан применительно к муниципальным реформам.; Зарубежные варианты используются как материал, а не как готовое решение.
- **Источник не доказывает:** Популярность зарубежной модели не доказывает ее применимость.; Контекстный анализ не гарантирует успех адаптированного варианта.
- **Фальсификаторы и пределы переноса:** Предлагаемый механизм работал только при отсутствующем контекстном условии.; Адаптация уничтожает ключевую функцию модели.; Риски выбранного варианта выше доступной альтернативы.
- **Контрпример:** Один иностранный способ укрупнения муниципалитетов нельзя объявлять оптимальным, не сравнив альтернативы и влияние различий в финансировании, демократии и распределении полномочий.
- **Не использовать для:** Не копировать готовую модель.; Не считать сравнение доказательством результата.; Не обещать конкретный исход.
- **Российская правовая граница:** Генерация альтернатив и контекстный фильтр полезны как сравнительная эвристика, но не установлены официальным российским стандартом. Статья 74 подтверждает только предметный предел; каждый вариант и remedy должны иметь самостоятельное действующее правовое основание. Пределы: Количество зарубежных вариантов не доказывает полноту или качество анализа.; Контекстный фильтр не заменяет проверку российского права и компетенции адресата.; КС РФ не обязан выбирать или проектировать институциональный вариант за пределами предмета обращения.
- **Маршруты:** ksrf-argument-patterns; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-c-path-r2-cmc-gritsenko-contextual-option-generation-02`; legal review `legal-anchor-b-r1-034-cmc-gritsenko-contextual-option-generation-02`; source SHA-256 `0f24c493dd129c2db469029a12c4199d7c011a380f93497306b98c406a42791c`.

<a id="cmc-vaipan-cyclic-proportionality-01"></a>
### `cmc-vaipan-cyclic-proportionality-01` — Григорий Викторович Вайпан

- **Работа и locator:** Принцип пропорциональности и аргументация в сфере ограничений прав человека: от Р. Алекси к Р. Дворкину и обратно; печат. 45; PDF 47; раздел Раздел IV.1 «От балансирования к категоризации и обратно».
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** В тесте пропорциональности явно чередовать определение охвата права и оценку веса доводов, сохраняя трассу переходов между ними.
- **Когда полезна:** Тест пропорциональности объявляет вес или предел права без обоснования перехода между ними.
- **Предусловия:** Определено затронутое право.; Установлена цель ограничения.; Собраны доводы и факты о последствиях.
- **Остановиться или воздержаться:** Не определено вмешательство в право.; Вес интереса объявлен без фактов или критериев.; Категория права выбрана только для получения желаемого результата.
- **Оговорки источника:** Тезис относится к методологии пропорциональности.; Взаимозависимость не дает автоматического материального ответа, но структурирует аргументацию.
- **Источник не доказывает:** Тезис не устанавливает единственно правильный результат балансирования.; Цикличность не означает бесполезность принципа пропорциональности.
- **Фальсификаторы и пределы переноса:** Официальная норма однозначно исключает спорный интерес из охвата права.; Фактические данные опровергают заявленную тяжесть вмешательства.; Альтернативное толкование лучше объясняет текст и последствия без скрытого выбора.
- **Контрпример:** Нельзя сначала узко определить охват права, а затем объявить ограничение легким, не показав, почему исключенные интересы не входят в право.
- **Не использовать для:** Не превращать баланс в арифметику.; Не скрывать категориальные выборы.; Не обещать признание ограничения непропорциональным.
- **Российская правовая граница:** Конституция и решения КС РФ требуют необходимости, соразмерности и баланса, но не устанавливают авторский циклический метод «категория — довод — баланс — пересмотр категории». Функциональное сходство недостаточно для превращения этой теории в российский правовой стандарт. Пределы: Допустимо только прозрачное использование как сравнительной техники организации аргумента.; Каждый материальный критерий охвата права и ограничения должен иметь отдельную официальную российскую опору.; Метод не доказывает компетенцию КС РФ, допустимость жалобы или средство защиты.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-c-r1-vaipan-cyclic-proportionality-01`; legal review `legal-anchor-c-r1-072`; source SHA-256 `65eeae5f16b53a90d8aa05c68200a800b62c9cff17b72cfb1f69fada1b750fb2`.

<a id="cmc-vaipan-proportionality-open-challenge-02"></a>
### `cmc-vaipan-proportionality-open-challenge-02` — Григорий Викторович Вайпан

- **Работа и locator:** Принцип пропорциональности и аргументация в сфере ограничений прав человека: от Р. Алекси к Р. Дворкину и обратно; печат. 50–51; PDF 52–53; раздел Раздел V «Заключение: пропорциональность как аргументация».
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** QA пропорциональности должен искать не финальную формулу, а уязвимые переходы: факты, категории, альтернативы, распределение бремени и необоснованные остатки.
- **Когда полезна:** Аргумент объявляет результат пропорциональности самоочевидным или окончательным.
- **Предусловия:** Есть полная цепочка обоснования ограничения.; Определены факты, цели и альтернативы.; Доступны позиции обеих сторон.
- **Остановиться или воздержаться:** Нет позиции противоположной стороны.; Фактическая база ограничения не установлена.; Составитель выдает отсутствие окончательного критерия за автоматическую победу.
- **Оговорки источника:** Автор одновременно критикует отсутствие единого материального критерия пропорциональности.; Открытость спора не отменяет обязанности дать мотивированное решение.
- **Источник не доказывает:** Тезис не означает, что любое ограничение юридически допустимо.; Продолжение аргументации не гарантирует пересмотр решения.
- **Фальсификаторы и пределы переноса:** Возражение основано на неподтвержденной альтернативе.; Официальное право исключает предлагаемый критерий.; Новый факт устраняет ранее выявленный разрыв обоснования.
- **Контрпример:** Фраза «мера соразмерна общественной цели» не завершает анализ, если не объяснены тяжесть вмешательства, выбор альтернатив и причины отклонения возражений.
- **Не использовать для:** Не объявлять всякое ограничение незаконным.; Не бесконечно размножать нерелевантные возражения.; Не обещать пересмотр решения.
- **Российская правовая граница:** ФКЗ требует мотивов решения и тем самым поддерживает тщательный stress-test как рабочую технику, но российское право не объявляет каждое ограничение юридически «недообоснованным» и не создает право на бесконечный диалог: решение КС РФ окончательно и не подлежит обжалованию. Поэтому официальной опоры той же пропозиции нет. Пределы: Использовать только как внутренний QA-прием, не как норму права.; Открытость аргументации не означает процессуальную возможность бесконечного пересмотра или обжалования постановления КС РФ.; Возражения должны быть юридически релевантны и опираться на проверенные факты и официальные критерии.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-echr-argumentation.
- **Provenance:** source review `source-review-c-path-r2-cmc-vaipan-proportionality-open-challenge-02`; legal review `legal-anchor-c-r1-073`; source SHA-256 `65eeae5f16b53a90d8aa05c68200a800b62c9cff17b72cfb1f69fada1b750fb2`.

<a id="cmc-luebbe-wolff-universal-core-01"></a>
### `cmc-luebbe-wolff-universal-core-01` — Гертруда Люббе-Вольф

- **Работа и locator:** Международная защита прав человека и принцип субсидиарности: аргументы в пользу решения-«коридора» в случае конфликта прав; печат. 68; PDF 70; раздел Основной текст, обсуждение универсальности и субсидиарности.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При сравнительном аргументе следует отдельно установить обязательный минимум защиты и область допустимых институционально обусловленных вариантов.
- **Когда полезна:** Иностранное решение представляется как единственно возможное содержание универсального права.
- **Предусловия:** Определено затронутое право.; Доступны тексты сравниваемых стандартов и их контекст.
- **Остановиться или воздержаться:** Универсальное ядро лишь заявлено и не обосновано.; Иностранный результат переносится без проверки российского контекста.
- **Оговорки источника:** Автор исходит из существования универсального ядра прав.; Вариативность связывается с уважительными различиями коллективных предпочтений, а не с любым отклонением.
- **Источник не доказывает:** Тезис не позволяет считать любое национальное ограничение допустимым.; Статья не определяет содержание ядра применительно к российскому делу.
- **Фальсификаторы и пределы переноса:** Прямой обязательный стандарт может исключить вариативность.; Нарушение ядра права нельзя оправдать ссылкой на коллективные предпочтения.
- **Контрпример:** Прямой запрет пыток не превращается в вопрос национального предпочтения.
- **Не использовать для:** Не снижать обязательный минимум защиты.; Не объявлять иностранное решение нормой российского права.
- **Российская правовая граница:** Российская Конституция признает неотчуждаемые права и запрещает умалять их, однако не закрепляет авторскую модель международной субсидиарности и «коллективных предпочтений» вне универсального ядра. Такая модель не совпадает по институциональному уровню с российским конституционным контролем. Пределы: Сравнительный материал нельзя использовать для снижения прямо действующих гарантий Конституции РФ.; Граница существа конкретного права и допустимого усмотрения должна подтверждаться российским официальным источником по соответствующему праву.; Доктрина не определяет компетенцию, допустимость жалобы или способ защиты в КС РФ.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-r1-luebbe-wolff-universal-core-01`; legal review `legal-anchor-c-r1-074`; source SHA-256 `48bf5cc3c6ec5d173ec26c60648360e73bb43a834d976c7d763b67dc8cdd689a`.

<a id="cmc-luebbe-wolff-rights-corridor-02"></a>
### `cmc-luebbe-wolff-rights-corridor-02` — Гертруда Люббе-Вольф

- **Работа и locator:** Международная защита прав человека и принцип субсидиарности: аргументы в пользу решения-«коридора» в случае конфликта прав; печат. 70; PDF 72; раздел Основной текст, модель решения-«коридора», рис. 3.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Сравнительный стандарт следует формулировать как нижние границы защиты обеих сторон и отдельно отмечать зону, где источник допускает несколько национальных решений.
- **Когда полезна:** Аргумент требует перенести одно иностранное балансирующее решение как единственно допустимое.
- **Предусловия:** Установлены два реально конфликтующих права.; Определены минимальные требования к каждому праву.
- **Остановиться или воздержаться:** Минимальная граница хотя бы одного права не установлена.; Предлагаемая линия нарушает установленный минимум защиты.
- **Оговорки источника:** Конструкция предложена для наднационального суда и конфликтующих прав частных лиц.; Коридор ограничен минимальным пространством каждого права.
- **Источник не доказывает:** Модель не является готовой нормой российского конституционного права.; Наличие коридора не позволяет национальному органу игнорировать минимальные гарантии.
- **Фальсификаторы и пределы переноса:** Прямое правило источника права может не оставлять коридора.; На национальном уровне институциональный смысл коридора может отсутствовать.
- **Контрпример:** Если официальный стандарт прямо запрещает конкретное вмешательство, пространство выбора нельзя конструировать доктринально.
- **Не использовать для:** Не расширять усмотрение сверх источника права.; Не обещать конкретный исход балансирования.
- **Российская правовая граница:** Конституция требует согласовывать осуществление прав с правами других лиц и допускает только необходимые ограничения, но не создает описанную автором институциональную модель наднационального «коридора». Метод может сдерживать чрезмерно категоричный сравнительный довод, однако границы обоих прав и наличие усмотрения должны следовать из российских официальных источников. Пределы: Использовать только как сравнительную карту, а не источник российского стандарта.; Нельзя конструировать зону выбора, если Конституция, закон или обязательная позиция КС РФ задают единственный результат.; Минимум каждого права необходимо независимо подтвердить действующей официальной опорой.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-r1-luebbe-wolff-rights-corridor-02`; legal review `legal-anchor-c-r1-075`; source SHA-256 `48bf5cc3c6ec5d173ec26c60648360e73bb43a834d976c7d763b67dc8cdd689a`.

<a id="cmc-alexy-balancing-stages-01"></a>
### `cmc-alexy-balancing-stages-01` — Роберт Алекси

- **Работа и locator:** Сбалансированность, конституционный контроль и представительство; печат. 114; PDF 115; раздел § 1.2 «Структура сбалансированности».
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При аргументации ограничения права нужно разнести по отдельным блокам интенсивность вмешательства, значимость конкурирующей цели и обоснование их соотношения.
- **Когда полезна:** В позиции стороны или суда используется балансирование конкурирующих принципов.
- **Предусловия:** Определены затронутое право и конкурирующий принцип.; Установлены фактические последствия вмешательства.
- **Остановиться или воздержаться:** Не определен хотя бы один из конкурирующих принципов.; Соотношение объявлено без фактических и нормативных оснований.
- **Оговорки источника:** Модель относится к пропорциональности в узком смысле.; Степени и их сопоставление требуют аргументации, а не механического подсчета.
- **Источник не доказывает:** Трехчастная структура не делает исход балансирования арифметически предопределенным.; Статья не устанавливает действующий для КС РФ процессуальный тест.
- **Фальсификаторы и пределы переноса:** Наличие менее обременительной равнозначной меры требует анализа необходимости до узкого балансирования.; Несовместимый институциональный контекст может исключить перенос модели.
- **Контрпример:** Ссылка на общественный интерес без оценки тяжести вмешательства не образует трехстадийного балансирования.
- **Не использовать для:** Не присваивать правам числовые веса автоматически.; Не обещать исход конституционного производства.
- **Российская правовая граница:** Российское право применяет категории необходимости, соразмерности и согласования конституционных ценностей, но не превращает авторскую трехчастную весовую структуру в обязательный процессуальный тест. Ее можно использовать как неавторитетный чек-лист полноты, сохраняя отдельные официальные основания для каждого материального вывода. Пределы: Не присваивать принципам формальные веса и не выдавать три стадии за тест КС РФ.; До балансирования следует проверить текстовые запреты, компетенцию и необходимость меры по действующему праву.; Чек-лист не определяет допустимость жалобы или средство защиты.
- **Маршруты:** ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-c-path-r2-cmc-alexy-balancing-stages-01`; legal review `legal-anchor-c-r1-076`; source SHA-256 `7712a39b927be3dd83ee19383d2a0ade3ec791e17082c20d76454fe2c57944d9`.

<a id="cmc-alexy-reasoned-representation-02"></a>
### `cmc-alexy-reasoned-representation-02` — Роберт Алекси

- **Работа и locator:** Сбалансированность, конституционный контроль и представительство; печат. 117; PDF 118; раздел § 3.2 «Предпосылки надлежаще обоснованного представительства».
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Конституционно-правовой довод следует проверять не только на формальную связность, но и на публично объяснимые основания, которые адресат может принять без ссылки на авторитет суда как таковой.
- **Когда полезна:** Аргумент оправдывает приоритет судебной конституционной оценки над решением законодателя.
- **Предусловия:** Выделен ключевой вывод и цепочка его оснований.; Определен адресат объяснения.
- **Остановиться или воздержаться:** Вывод держится только на авторитете суда или автора.; Невозможно восстановить основания, доступные для внешней критики.
- **Оговорки источника:** Тезис является частью авторской теории дискурсивного конституционализма.; Приемлемость аргумента не тождественна фактическому одобрению большинством.
- **Источник не доказывает:** Тезис не доказывает демократическую легитимность любого решения конституционного суда.; Убедительность для автора не заменяет проверку корректности доводов.
- **Фальсификаторы и пределы переноса:** Фактическая непопулярность аргумента сама по себе не опровергает его корректность.; Публичная приемлемость не заменяет официальную правовую проверку.
- **Контрпример:** Мотивировка «так решил суд» не удовлетворяет условию обоснованного представительства.
- **Не использовать для:** Не измерять легитимность опросом популярности.; Не объявлять доктрину источником действующего права.
- **Российская правовая граница:** ФКЗ требует излагать мотивы решения, но не закрепляет дискурсивную теорию «обоснованного представительства» и не ставит юридическую силу решения в зависимость от принятия аргументов разумным адресатом. Метод полезен лишь как QA качества объяснения. Пределы: Не использовать общественную приемлемость или предполагаемую разумность адресата как юридический критерий действительности решения.; Публично объяснимая аргументация не заменяет норму о компетенции, допустимости и последствиях решения.; Метод не дает основания требовать пересмотра окончательного акта КС РФ.
- **Маршруты:** ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-c-path-r2-cmc-alexy-reasoned-representation-02`; legal review `legal-anchor-c-r1-077`; source SHA-256 `7712a39b927be3dd83ee19383d2a0ade3ec791e17082c20d76454fe2c57944d9`.

<a id="cmc-moller-four-stage-test-01"></a>
### `cmc-moller-four-stage-test-01` — Кай Мёллер

- **Работа и locator:** Принцип соразмерности: в ответ на критику; печат. 88; PDF 90; раздел § 2 «Принцип соразмерности».
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При оценке ограничения права необходимо последовательно ответить на четыре вопроса и не переносить неразрешенную проблему с ранней стадии в итоговое балансирование.
- **Когда полезна:** Мера ограничивает конституционное право ради заявленной публичной или частной цели.
- **Предусловия:** Определены мера, право и заявленная цель.; Доступны факты о действии меры и возможных альтернативах.
- **Остановиться или воздержаться:** Не установлена фактическая цель или действие меры.; Нет данных для сравнения эффективности альтернатив.
- **Оговорки источника:** Балансирование завершает тест после проверки подлинного конфликта.; Автор отмечает упрощенность традиционной формулы необходимости в сложных случаях.
- **Источник не доказывает:** Четыре стадии не являются автоматически действующим тестом КС РФ.; Прохождение первых трех стадий не предрешает итоговое балансирование.
- **Фальсификаторы и пределы переноса:** Некоторые системы распределяют оценку альтернатив между стадиями иначе.; Прямая запретительная норма может завершить анализ до балансирования.
- **Контрпример:** Недопустимая цель не становится допустимой из-за эффективности выбранной меры.
- **Не использовать для:** Не подменять доказательства названиями стадий.; Не вычислять соразмерность арифметически.
- **Российская правовая граница:** Конституция прямо поддерживает вопросы о допустимой цели и необходимости и позволяет использовать вопросы о связи, альтернативе и бремени для проверки доказательности. Но официальный российский стандарт не совпадает с обязательной четырехстадийной архитектурой карточки; интенсивность и последовательность проверки зависят от права, меры и практики КС РФ. Пределы: Формулировать четыре вопроса как аналитический чек-лист, а не цитату или обязательный тест КС РФ.; Для каждого материального критерия и конкретного права нужна самостоятельная официальная опора.; Отсутствие данных об альтернативе не доказывает автоматически соразмерность или несоразмерность меры.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-path-r2-cmc-moller-four-stage-test-01`; legal review `legal-anchor-c-r2-079`; source SHA-256 `e0a157696278d5a2ec962ff7b56f1c422e4e85259a26c86236d3a12979ccbf78`.

<a id="cmc-moller-all-relevant-factors-02"></a>
### `cmc-moller-all-relevant-factors-02` — Кай Мёллер

- **Работа и locator:** Принцип соразмерности: в ответ на критику; печат. 91–92; PDF 93–94; раздел § 2.4 «Четвертая стадия: балансирование».
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Перед итоговым выводом нужно проверить, не потеряны ли достоинство, агентность, распределение бремени и иные деонтические факторы из-за сведения анализа к суммарной пользе.
- **Когда полезна:** Приоритет меры обосновывается тем, что совокупная польза превышает вред одному лицу.
- **Предусловия:** Определены носители прав и распределение бремени.; Собраны все заявленные выгоды и вред.
- **Остановиться или воздержаться:** Не определено, на кого фактически возложено бремя.; Итог основан только на агрегированной пользе.
- **Оговорки источника:** Автор допускает анализ интересов как один из способов, но не как единственный.; Пример с трансплантацией показывает предел чистого количественного сравнения.
- **Источник не доказывает:** Тезис не дает готовой шкалы приоритета всех прав и интересов.; Ссылка на этику не освобождает от рациональной мотивировки.
- **Фальсификаторы и пределы переноса:** Не каждый спор содержит абсолютное деонтическое ограничение.; Перечень факторов сам по себе не устанавливает их вес.
- **Контрпример:** Спасение большего числа людей не само по себе оправдывает принудительное убийство одного ради изъятия органов.
- **Не использовать для:** Не максимизировать суммарную пользу автоматически.; Не превращать этическую интуицию в непроверяемое утверждение.
- **Российская правовая граница:** Конституция защищает достоинство и требует необходимости ограничения, но не закрепляет теоретический запрет утилитарного агрегирования или универсальный набор деонтических факторов. Карточка пригодна как напоминание не терять качественные последствия, если каждый фактор релевантен по официальному праву и доказан. Пределы: Не выдавать перечень достоинство—агентность—распределение бремени за исчерпывающий тест КС РФ.; Каждый фактор должен быть связан с конкретной конституционной нормой, обязательной позицией и фактами дела.; Доктринальная этическая оценка не заменяет юридический стандарт, компетенцию и средство защиты.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-path-r2-cmc-moller-all-relevant-factors-02`; legal review `legal-anchor-c-r1-080`; source SHA-256 `e0a157696278d5a2ec962ff7b56f1c422e4e85259a26c86236d3a12979ccbf78`.

<a id="cmc-moller-structured-ethical-reasoning-03"></a>
### `cmc-moller-structured-ethical-reasoning-03` — Кай Мёллер

- **Работа и locator:** Принцип соразмерности: в ответ на критику; печат. 100; PDF 102; раздел § 3.4, ответ на критику структуры соразмерности.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Сложное ограничение следует декомпозировать по каждой цели и альтернативе, сохраняя прослеживаемость от факта до итогового приоритета.
- **Когда полезна:** У меры несколько заявленных целей, причинных связей или альтернатив.
- **Предусловия:** Все заявленные цели перечислены отдельно.; Имеются данные о действии меры и альтернативах.
- **Остановиться или воздержаться:** Разные цели слиты в одну абстрактную формулу.; Нет доказательств связи меры хотя бы с одной существенной целью.
- **Оговорки источника:** Структура особенно полезна в сложных многоцелевых делах.; Автор не утверждает, что алгоритм устраняет этическое суждение или неопределенность.
- **Источник не доказывает:** Формальное заполнение стадий не гарантирует правильность результата.; Алгоритм не заменяет фактические доказательства и нормативные основания.
- **Фальсификаторы и пределы переноса:** В простом деле часть стадий может не иметь самостоятельного значения.; Декомпозиция не отвечает сама по себе на спорный этический вопрос.
- **Контрпример:** Мера с одной недопустимой и одной допустимой целью нельзя оправдать общей ссылкой на смешанный публичный интерес.
- **Не использовать для:** Не маскировать ценностный выбор процедурой.; Не считать наличие матрицы доказательством соразмерности.
- **Российская правовая граница:** Официальное право требует необходимых ограничений для допустимых целей и мотивированного решения, но не предписывает метод карточки как универсальный алгоритм. Декомпозиция повышает прослеживаемость анализа и допустима как техника, а не источник материального вывода. Пределы: Не называть авторскую последовательность обязательным тестом российского конституционного контроля.; Связь меры с каждой целью и сравнение альтернатив требуют фактических доказательств, а не заполнения шаблона.; Прямая конституционная норма может завершить анализ до итогового балансирования.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-path-r2-cmc-moller-structured-ethical-reasoning-03`; legal review `legal-anchor-c-r1-081`; source SHA-256 `e0a157696278d5a2ec962ff7b56f1c422e4e85259a26c86236d3a12979ccbf78`.

<a id="cmc-kumm-comella-institutional-doctrines-01"></a>
### `cmc-kumm-comella-institutional-doctrines-01` — Маттиас Кумм, Виктор Ферререс Комелла

- **Работа и locator:** Особая роль конституционных прав в разрешении частноправовых споров; печат. 52; PDF 53; раздел Введение, главная задача статьи.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Сравнивая горизонтальное действие прав, нужно картировать компетенцию судов, объект проверки и процессуальный маршрут, а не выводить результат из названия иностранной доктрины.
- **Когда полезна:** Сторона ссылается на иностранную модель действия конституционных прав в частном споре.
- **Предусловия:** Определены источник и юрисдикция иностранной доктрины.; Установлен процессуальный маршрут российского дела.
- **Остановиться или воздержаться:** Институциональные параметры исходной системы не установлены.; Вывод основан только на совпадении терминов.
- **Оговорки источника:** Тезис основан на сравнении Германии, Канады и США.; Авторы не отрицают материально-правового значения конкретных прав и интересов.
- **Источник не доказывает:** Название доктрины само по себе не предсказывает результат частноправового спора.; Сравнение не доказывает тождество институциональных условий России с рассмотренными странами.
- **Фальсификаторы и пределы переноса:** Прямое совпадение материальной нормы не устраняет различий компетенции.; Российская процедура может не позволять воспроизвести иностранный механизм.
- **Контрпример:** Доктрина косвенного эффекта в одной системе не переносится автоматически в другую при ином распределении полномочий между судами.
- **Не использовать для:** Не выбирать доктрину по названию.; Не расширять компетенцию КС РФ сравнительной ссылкой.
- **Российская правовая граница:** ФКЗ действительно требует в российской части отдельно установить компетенцию, нормативный объект и процессуальный маршрут, но не подтверждает сравнительное объяснение различий между иностранными доктринами. Карточка допустима только как метод сравнительного картирования; российский результат должен выводиться из Конституции и ФКЗ. Пределы: Не переносить название иностранной доктрины как основание для прямой жалобы против частного лица.; В КС РФ проверяется нормативный акт и его конституционный смысл, а не разрешается частный спор по существу.; Компетенция, допустимость и последствия должны проверяться отдельно по действующим российским нормам.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-path-r2-cmc-kumm-comella-institutional-doctrines-01`; legal review `legal-anchor-c-r1-082`; source SHA-256 `7712a39b927be3dd83ee19383d2a0ade3ec791e17082c20d76454fe2c57944d9`.

<a id="cmc-kumm-comella-normative-issues-hidden-02"></a>
### `cmc-kumm-comella-normative-issues-hidden-02` — Маттиас Кумм, Виктор Ферререс Комелла

- **Работа и locator:** Особая роль конституционных прав в разрешении частноправовых споров; печат. 70; PDF 71; раздел § 4 «Заключение», три итоговых тезиса.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** После классификации механизма горизонтального действия нужно заново явно поставить материальный вопрос: какие права конфликтуют, где проходит граница и чем она оправдана.
- **Когда полезна:** Вывод обоснован преимущественно ссылкой на прямой, косвенный эффект или государственные действия.
- **Предусловия:** Выделены частные участники и применяемая норма.; Определены затронутые конституционные интересы.
- **Остановиться или воздержаться:** Права и интересы сторон не реконструированы.; Доктринальный ярлык выдается за достаточное обоснование исхода.
- **Оговорки источника:** Речь идет о трех доктринах, рассмотренных авторами в конкретных системах.; Институциональная функция доктрин при этом может оставаться значимой.
- **Источник не доказывает:** Тезис не требует отказаться от процессуальных доктрин.; Он не задает готовое материальное решение любого конфликта частных интересов.
- **Фальсификаторы и пределы переноса:** Формальная доктрина может быть обязательной для допустимости, даже если не решает материальный вопрос.; Не всякий частный спор имеет конституционно значимый конфликт.
- **Контрпример:** Фраза о косвенном эффекте прав не объясняет, почему свобода одной стороны должна уступить интересу другой.
- **Не использовать для:** Не отменять процессуальные требования.; Не конституционализировать любой частный спор.
- **Российская правовая граница:** Обязанность выявлять конкретный нормативный конфликт совместима с предметом конституционного контроля, но авторская критика сравнительных классификаций не является самостоятельной нормой. Ее можно применять только как вопрос к аргументу, не меняя российского объекта проверки и не подменяя анализ конкретных прав. Пределы: КС РФ не разрешает частный спор вместо компетентного суда и не устанавливает заново его факты.; Материальная граница каждого права требует официальной нормы и позиции по конкретному предмету.; Иностранная классификация не определяет допустимость российской жалобы.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-path-r2-cmc-kumm-comella-normative-issues-hidden-02`; legal review `legal-anchor-c-r1-083`; source SHA-256 `7712a39b927be3dd83ee19383d2a0ade3ec791e17082c20d76454fe2c57944d9`.

<a id="cmc-kumm-comella-function-before-transfer-03"></a>
### `cmc-kumm-comella-function-before-transfer-03` — Маттиас Кумм, Виктор Ферререс Комелла

- **Работа и locator:** Особая роль конституционных прав в разрешении частноправовых споров; печат. 72; PDF 73; раздел § 4 «Заключение», заключительный абзац.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Перед сравнительной ссылкой нужно описать проблему, функцию доктрины, ее механизм и институциональные предпосылки, а затем проверить наличие российского функционального аналога.
- **Когда полезна:** Найден иностранный термин или тест с потенциально релевантным результатом.
- **Предусловия:** Доступен первичный источник доктрины.; Определена российская проблема, для которой ищется аналог.
- **Остановиться или воздержаться:** Функция доктрины неизвестна или выведена только из названия.; В российской системе отсутствует сопоставимая проблема или институт.
- **Оговорки источника:** Одна и та же этикетка может обозначать разные функции в разных системах.; Функция определяется также структурой прав и институциональными соображениями.
- **Источник не доказывает:** Функциональное сходство не доказывает полную переносимость доктрины.; Из текста не следует, что любая иностранная доктрина полезна российскому делу.
- **Фальсификаторы и пределы переноса:** Сходный результат может достигаться совершенно иным механизмом.; Историческое описание функции может быть устаревшим.
- **Контрпример:** Совпадение слова «горизонтальный» не доказывает одинаковую юрисдикцию и последствия контроля.
- **Не использовать для:** Не копировать иностранную формулу целиком.; Не скрывать институциональные различия.
- **Российская правовая граница:** Метод разумно предотвращает ложный сравнительный перенос, но не имеет статуса российского правового стандарта. Его результат должен быть лишь картой совместимости, после которой компетенция, объект проверки, материальная норма и последствия доказываются официальными российскими источниками. Пределы: Функциональное сходство не создает юридическую обязательность иностранной доктрины.; Нельзя заполнять пробел российской компетенции сравнительным аргументом.; При отсутствии проверяемого российского аналога вывод должен остаться иллюстративным.
- **Маршруты:** ksrf-rights-argument-builder; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-path-r2-cmc-kumm-comella-function-before-transfer-03`; legal review `legal-anchor-c-r1-084`; source SHA-256 `7712a39b927be3dd83ee19383d2a0ade3ec791e17082c20d76454fe2c57944d9`.

<a id="cmc-schauer-precedent-not-analogy-01"></a>
### `cmc-schauer-precedent-not-analogy-01` — Frederick F. Schauer

- **Работа и locator:** Why Precedent in Law (and Elsewhere) Is Not Totally About Analogy; печат. 3; PDF 4; раздел Introduction, distinction between precedent and analogy.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** В ссылках на судебную практику нужно маркировать, используется ли акт как обязательное ограничение, как убедительная позиция или лишь как аналогия.
- **Когда полезна:** Прошлое решение используется для вывода по текущему делу.
- **Предусловия:** Доступен полный текст прошлого решения.; Определена его формальная роль в целевой юрисдикции.
- **Остановиться или воздержаться:** Формальная роль решения не установлена.; Совпадение вопроса заменено поверхностным сходством фактов.
- **Оговорки источника:** Тезис описывает genuine precedential constraint, а не любое цитирование прошлого дела.; Первоначально все равно требуется установить релевантное сходство вопроса.
- **Источник не доказывает:** Тезис не устанавливает обязательную силу решений в российском праве.; Любое сходное дело не становится связывающим прецедентом.
- **Фальсификаторы и пределы переноса:** В российской системе роль судебных актов отличается от common law stare decisis.; Даже обязательный акт может допускать разграничение при существенном различии вопроса.
- **Контрпример:** Выбор удобного иностранного дела из нескольких кандидатов является аналогией, а не следованием связывающему прецеденту.
- **Не использовать для:** Не объявлять иностранные решения обязательными.; Не использовать авторитет вместо анализа вопроса.
- **Российская правовая граница:** Практическое требование различать обязательную силу, убеждающее использование и аналогию подтверждается специальным статусом решений КС РФ. Однако объяснение Шауэра относится к common law и не описывает российскую систему источников; обязательность конкретной позиции и ее применимость должны устанавливаться по резолютивной части, выявленному смыслу и совпадению нормативного вопроса. Пределы: Не называть всякую ссылку на решение КС РФ прецедентом в смысле stare decisis.; Обязательность решения не устраняет необходимость доказать релевантность проверенной нормы и выявленного конституционного смысла.; Решения иных судов имеют другой процессуальный и нормативный статус и требуют отдельной проверки.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-cmc-schauer-precedent-not-analogy-01`; legal review `legal-anchor-c-r2-085`; source SHA-256 `43e99fd67defa39a83e4d05571df309c5bc7b82ad1cc6008b00f71be346c6dee`.

<a id="cmc-schauer-source-choice-test-02"></a>
### `cmc-schauer-source-choice-test-02` — Frederick F. Schauer

- **Работа и locator:** Why Precedent in Law (and Elsewhere) Is Not Totally About Analogy; печат. 10–12; PDF 11–13; раздел § III «On the Differences Between Analogy and Precedent».
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Чтобы выявить манипулятивную ссылку, следует спросить, был ли источник выбран ради удобного результата или навязан совпадением правового вопроса и формальной силой.
- **Когда полезна:** Автор позиции называет выбранное сходное решение прецедентом.
- **Предусловия:** Есть перечень потенциально релевантных актов.; Определен точный правовой вопрос.
- **Остановиться или воздержаться:** Поиск альтернативных актов не проведен.; Правовой вопрос сформулирован слишком широко для проверки совпадения.
- **Оговорки источника:** Неизбежность означает профессионально и институционально признанное совпадение вопроса.; Творческое разграничение возможно, но автор считает его нетипичным для подлинного ограничения.
- **Источник не доказывает:** Отсутствие выбора не делает интерпретацию прецедента бесспорной.; Сходство фактов без совпадения вопроса не создает прецедентного ограничения.
- **Фальсификаторы и пределы переноса:** Наличие нескольких актов не всегда устраняет формальную иерархию.; Иногда аналогия используется внутри применения обязательного акта.
- **Контрпример:** Составитель выбирает одно из десяти похожих дел, потому что оно поддерживает желаемый результат, и называет его связывающим прецедентом.
- **Не использовать для:** Не запрещать аналогии.; Не приписывать акту обязательность без официального основания.
- **Российская правовая граница:** Российский ФКЗ определяет обязательность решений КС РФ, но не закрепляет психологический тест «выбран или навязан» из теории common law. Как внутренний QA вопрос может выявлять cherry-picking, однако юридическая сила и применимость устанавливаются объективно по виду акта, норме, резолютивной части и вопросу, а не по мотиву исследователя. Пределы: Не выводить обязательность из ощущения неизбежности источника.; Проверять полноту официальной практики и отличия фактов и нормативного вопроса.; Диагностика выбора не определяет допустимость жалобы и средство защиты.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-cmc-schauer-source-choice-test-02`; legal review `legal-anchor-c-r1-086`; source SHA-256 `43e99fd67defa39a83e4d05571df309c5bc7b82ad1cc6008b00f71be346c6dee`.

<a id="cmc-schauer-second-order-values-03"></a>
### `cmc-schauer-second-order-values-03` — Frederick F. Schauer

- **Работа и locator:** Why Precedent in Law (and Elsewhere) Is Not Totally About Analogy; печат. 13; PDF 14; раздел § IV «Does Precedential Constraint Make Sense?».
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При предложении отступить от сложившейся позиции нужно отдельно сопоставить ошибочность первичного результата с потерями определенности, равенства и доверия от изменения курса.
- **Когда полезна:** Предлагается отступить от прежнего решения как ошибочного.
- **Предусловия:** Идентифицирована прежняя устойчивая позиция.; Сформулирована предполагаемая ошибка и последствия отступления.
- **Остановиться или воздержаться:** Прежняя позиция или практика не установлена.; Системные последствия только декларированы.
- **Оговорки источника:** Автор называет такие случаи исключением, а не общим правилом принятия решений.; Особая значимость ценностей связывается с функцией правовой системы.
- **Источник не доказывает:** Стабильность не требует сохранять любой ошибочный акт без исключений.; Статья не задает российские основания пересмотра правовой позиции.
- **Фальсификаторы и пределы переноса:** Тяжелое нарушение права может перевесить стабильность.; Авторская теория не определяет формальные основания отступления в России.
- **Контрпример:** Новое толкование исправляет ошибку, но без переходных мер разрушает обоснованные ожидания адресатов.
- **Не использовать для:** Не закреплять ошибку только из-за ее возраста.; Не объявлять доктрину обязательным российским тестом.
- **Российская правовая граница:** Официальная позиция подтверждает значимость определенности, стабильности, предсказуемости и доверия, поэтому эти потери допустимо учитывать при предложении изменить правовой подход. Но она относится к регулированию статуса и оборота, а не закрепляет теорию второпорядковых ценностей прецедента или запрет отступать от ошибочной позиции. Пределы: Не приписывать Постановлению № 35-П доктрину stare decisis.; Стабильность не легализует продолжение применения нормы вопреки Конституции и обязательному решению КС РФ.; Вес доверия и переходные последствия зависят от предмета, адресатов и действующей компетенции.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-cmc-schauer-second-order-values-03`; legal review `legal-anchor-c-r2-087`; source SHA-256 `43e99fd67defa39a83e4d05571df309c5bc7b82ad1cc6008b00f71be346c6dee`.

<a id="cmc-sajo-self-defense-paradox-01"></a>
### `cmc-sajo-self-defense-paradox-01` — Андраш Шайо

- **Работа и locator:** Самозащита конституционного государства; печат. 3; PDF 4; раздел Введение, риск самозащиты для конституционного государства.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Каждую меру защиты конституционного строя нужно проверять симметрично: на способность снизить угрозу и на риск разрушить свободы, процедуры и ограничения власти.
- **Когда полезна:** Ограничение права оправдывается самозащитой демократии, безопасностью или борьбой с экстремизмом.
- **Предусловия:** Конкретная угроза описана и подтверждена.; Определены затронутые права и институциональные гарантии.
- **Остановиться или воздержаться:** Угроза описана абстрактно без проверяемого механизма.; Не оценены последствия меры для прав и контроля власти.
- **Оговорки источника:** Автор обсуждает воинствующую демократию и угрозы захвата власти изнутри.; Риск не означает безусловного отказа от всяких защитных мер.
- **Источник не доказывает:** Наличие угрозы не оправдывает любое ограничение прав.; Тезис не устанавливает конкретные полномочия КС РФ или органов безопасности.
- **Фальсификаторы и пределы переноса:** Непосредственная чрезвычайная угроза может менять интенсивность допустимого вмешательства.; Доктрина не заменяет официальный тест законности и необходимости.
- **Контрпример:** Расширение репрессивных полномочий без гарантий контроля может укрепить аппарат принуждения, но ослабить конституционный порядок.
- **Не использовать для:** Не отрицать возможность самозащиты государства.; Не оправдывать ограничения одним ярлыком угрозы.
- **Российская правовая граница:** Конституция одновременно содержит инструменты защиты строя и пределы ограничительной власти, что поддерживает двустороннюю проверку эффекта защитительной меры. Однако «парадокс самозащиты демократии» остается сравнительной теорией и не является самостоятельным российским основанием или тестом. Пределы: Нельзя оправдывать ограничение общей ссылкой на самозащиту без цели, закона, необходимости и фактов угрозы.; Нельзя и исключать предусмотренную Конституцией защиту только из-за абстрактного риска злоупотребления.; Для конкретной политической меры нужны профильный закон и обязательная практика.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-path-r2-cmc-sajo-self-defense-paradox-01`; legal review `legal-anchor-c-r2-088`; source SHA-256 `6fba33e7f7e6d13de7427fd1555252c64768321f73a2874192f9dd9bdc65cedb`.

<a id="cmc-sajo-anti-abuse-conditions-02"></a>
### `cmc-sajo-anti-abuse-conditions-02` — Андраш Шайо

- **Работа и locator:** Самозащита конституционного государства; печат. 4; PDF 5; раздел «Что такое воинствующая демократия? От чего защищать государство?».
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Довод о защитительном ограничении должен включать отдельный блок антизлоупотребительных гарантий, ответственных органов, критериев применения и контроля.
- **Когда полезна:** Норма предоставляет широкое усмотрение по ограничению политических или иных основных прав.
- **Предусловия:** Определены полномочие, адресаты и основания вмешательства.; Доступны процедуры контроля и обжалования.
- **Остановиться или воздержаться:** Механизмы контроля неизвестны.; Гарантии существуют только номинально и их действие не проверено.
- **Оговорки источника:** Автор реалистически допускает не полное исключение, а разумное сдерживание злоупотреблений.; Тезис относится к мерам воинствующей демократии.
- **Источник не доказывает:** Формальное наличие контроля не доказывает его эффективность.; Статья не задает исчерпывающий набор российских гарантий.
- **Фальсификаторы и пределы переноса:** Нулевая вероятность злоупотребления недостижима; требуется оценка разумного сдерживания.; Чрезвычайность не отменяет необходимость правовых гарантий автоматически.
- **Контрпример:** Широкий запрет политической деятельности без ясных критериев и независимого пересмотра не удовлетворяет антизлоупотребительному условию.
- **Не использовать для:** Не требовать невозможной абсолютной безопасности.; Не считать цель защиты достаточной без гарантий.
- **Российская правовая граница:** Законность, необходимость и судебная защита дают официальное основание проверять риск произвола, ответственный орган, критерии и контроль. Но тезис «приемлемы только при полном наборе механизмов» шире текста Конституции: конкретные гарантии и их достаточность зависят от вида вмешательства и профильного закона. Пределы: Не использовать авторский перечень как закрытый или самодостаточный юридический тест.; Для каждой меры нужно установить действующие процедуры, критерии, орган контроля и судебный маршрут по профильному закону.; Наличие формальной процедуры не доказывает ее эффективности без анализа содержания и практики применения.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-path-r2-cmc-sajo-anti-abuse-conditions-02`; legal review `legal-anchor-c-r2-089`; source SHA-256 `6fba33e7f7e6d13de7427fd1555252c64768321f73a2874192f9dd9bdc65cedb`.

<a id="cmc-sajo-context-minimum-impairment-03"></a>
### `cmc-sajo-context-minimum-impairment-03` — Андраш Шайо

- **Работа и locator:** Самозащита конституционного государства; печат. 10; PDF 11; раздел «Заключение».
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Для ограничения под видом защиты демократии нужно доказать контекстуальную серьезность угрозы, отделить правомерное поведение и сравнить менее ограничительные меры.
- **Когда полезна:** Ограничение охватывает поведение, часть которого является правомерным.
- **Предусловия:** Определена конкретная угроза и ее исторический контекст.; Доступны альтернативные меры.
- **Остановиться или воздержаться:** Нет доказательств необратимого или серьезного риска.; Невозможно отделить правомерное поведение из-за неопределенности нормы.
- **Оговорки источника:** Автор связывает оправданность с необратимым разрушением демократии и состоянием общества.; Исторический контекст служит оценке угрозы, а не самостоятельным разрешением запрета.
- **Источник не доказывает:** Прошлый авторитарный опыт не оправдывает бессрочное широкое ограничение.; Минимальное ущемление требует сравнения конкретных альтернатив.
- **Фальсификаторы и пределы переноса:** Историческая аналогия может быть ложной или устаревшей.; Минимальность не равна абсолютному отсутствию бремени.
- **Контрпример:** Полный запрет объединения охватывает мирную деятельность, хотя адресные санкции могли бы пресечь доказанные опасные действия.
- **Не использовать для:** Не криминализировать идеи без проверки угрозы.; Не переносить венгерские выводы как российское право.
- **Российская правовая граница:** Конституционный запрет умаления и требование необходимости поддерживают отделение правомерного поведения и проверку более щадящего решения. Но исторический контекст угрозы и строгая формула минимального ущемления не являются автономным универсальным тестом российского права; их релевантность зависит от конкретного права и закона. Пределы: Историческая опасность не заменяет доказательства актуальной связи конкретной меры с допустимой целью.; Менее ограничительная альтернатива должна быть сопоставима по эффективности и юридически доступна.; Профильный закон и актуальная практика обязательны для оценки конкретной меры.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-path-r2-cmc-sajo-context-minimum-impairment-03`; legal review `legal-anchor-c-r2-090`; source SHA-256 `6fba33e7f7e6d13de7427fd1555252c64768321f73a2874192f9dd9bdc65cedb`.

<a id="cmc-garlicki-integrated-interpretation-01"></a>
### `cmc-garlicki-integrated-interpretation-01` — Лех Гарлицкий

- **Работа и locator:** Конституционные суды против верховных судов; печат. 148; PDF 149; раздел § 1.3 «Конституция, созданная судьями».
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При реконструкции примененного смысла нормы нужно собирать не только текст закона, но и конституционные, надгосударственные и судебные интерпретационные слои, сохраняя компетенционные границы.
- **Когда полезна:** Отраслевая норма применяется без учета заявленного конституционного измерения.
- **Предусловия:** Есть судебные акты по делу.; Определены релевантные нормативные слои.
- **Остановиться или воздержаться:** Неясно, какой смысл нормы применен к заявителю.; Надгосударственный источник используется без проверки его применимости.
- **Оговорки источника:** Вывод сделан на сравнительном европейском материале.; Форма взаимодействия зависит от компетенции и процедур конкретной системы.
- **Источник не доказывает:** Обычный суд не получает автоматически полномочие отменять закон.; Статья не определяет современное распределение компетенции в России.
- **Фальсификаторы и пределы переноса:** Пересечение интерпретаций не снимает формальных границ компетенции.; Единичная ошибка суда не обязательно образует нормативную проблему.
- **Контрпример:** Общий суд учитывает конституционный принцип при толковании, но не получает от этого полномочие аннулировать закон erga omnes.
- **Не использовать для:** Не превращать КС РФ в апелляционную инстанцию.; Не смешивать источники разной юридической роли.
- **Российская правовая граница:** Российский суд обязан учитывать несколько нормативных уровней, поэтому требование собрать закон, Конституцию, международный договор и обязательные интерпретации функционально подтверждено. Но тезис 2007 года об «надгосударственных актах» требует существенной корректировки после статьи 79: международный материал не превосходит Конституцию, а компетенции КС РФ и иных судов сохраняются раздельными. Пределы: Использовать точное различие между международным договором и решением межгосударственного органа.; Не приписывать обычному суду полномочие признавать федеральный закон неконституционным вместо направления запроса в КС РФ.; Для конкретной нормы учитывать обязательный конституционный смысл и действующее процессуальное право.
- **Маршруты:** ksrf-echr-argumentation; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-tail-garlicki-integrated-interpretation-01`; legal review `legal-anchor-c-r2-091`; source SHA-256 `8d1198ecf8ca06094eb5b6fa4f5e08e46d47ca9baa8126ea7f857fccb7018dd8`.

<a id="cmc-garlicki-systemic-tension-02"></a>
### `cmc-garlicki-systemic-tension-02` — Лех Гарлицкий

- **Работа и locator:** Конституционные суды против верховных судов; печат. 153–154; PDF 154–155; раздел § 3.1 «Системная напряженность».
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Разногласие высших судов следует сначала классифицировать как функциональное пересечение, конфликт интерпретаций или институциональный отказ, не объявляя само расхождение кризисом.
- **Когда полезна:** Высшие суды расходятся в толковании конституционно значимой нормы.
- **Предусловия:** Идентифицированы точные позиции каждого суда.; Установлены полномочия и последствия решений.
- **Остановиться или воздержаться:** Позиции судов пересказаны без первичных актов.; Конфликт выведен только из разных исходов несопоставимых дел.
- **Оговорки источника:** Вывод относится к централизованной модели конституционного контроля.; Автор различает нормальную латентную напряженность и деструктивный конфликт.
- **Источник не доказывает:** Любой межсудебный конфликт не становится приемлемым.; Тезис не разрешает вопрос о том, какой суд прав по существу.
- **Фальсификаторы и пределы переноса:** Открытое неисполнение решения может быть не нормальной напряженностью, а кризисом.; Системность не оправдывает нарушение компетенции.
- **Контрпример:** Различная интенсивность контроля в разных производствах не доказывает войну судов.
- **Не использовать для:** Не драматизировать обычное разделение функций.; Не скрывать реальное неисполнение под словом «диалог».
- **Российская правовая граница:** Конституция разграничивает компетенции высших судов и ФКЗ делает решения КС РФ обязательными, но не легализует авторскую норму о «нормальной напряженности» или «войне судов». Классификация может служить нейтральным исследовательским словарем, пока не ослабляет обязательную силу решения и не приписывает органам отсутствующие полномочия. Пределы: Нельзя нормализовать неисполнение обязательного решения КС РФ как обычное функциональное пересечение.; Каждое расхождение проверяется по предмету компетенции, виду акта и его юридической силе.; Оценочная метка кризиса не заменяет официальный правовой анализ.
- **Маршруты:** ksrf-echr-argumentation; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-tail-garlicki-systemic-tension-02`; legal review `legal-anchor-c-r1-092`; source SHA-256 `8d1198ecf8ca06094eb5b6fa4f5e08e46d47ca9baa8126ea7f857fccb7018dd8`.

<a id="cmc-garlicki-dialogue-persuasion-04"></a>
### `cmc-garlicki-dialogue-persuasion-04` — Лех Гарлицкий

- **Работа и locator:** Конституционные суды против верховных судов; печат. 156; PDF 157; раздел § 3.4 «Позиция конституционных судов слабее».
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При разработке правовой позиции для межсудебного применения нужно формулировать операционное толкование, отвечать на отраслевые возражения и указывать исполнимый путь его внедрения.
- **Когда полезна:** Желаемый результат зависит от того, как иной суд применит конституционную интерпретацию.
- **Предусловия:** Определен суд-получатель и его компетенция.; Известны отраслевые возражения к предлагаемому смыслу.
- **Остановиться или воздержаться:** Предлагаемый смысл неоперационален для суда-получателя.; Аргумент опирается только на институциональный статус автора позиции.
- **Оговорки источника:** Вывод зависит от объема компетенции и процедур конкретного суда.; Речь идет прежде всего о положительном толковании, применяемом другими судами.
- **Источник не доказывает:** Диалог не заменяет обязательную юридическую силу там, где она установлена.; Убедительность не гарантирует фактическое исполнение.
- **Фальсификаторы и пределы переноса:** При прямом обязательном предписании роль убеждения может быть вторичной.; Слабость институционального контроля не разрешает выход за компетенцию.
- **Контрпример:** Абстрактный призыв учитывать Конституцию без объяснения отраслевого применения вряд ли изменит практику обычных судов.
- **Не использовать для:** Не заменять исполнение риторикой.; Не объявлять открытый конфликт всегда недопустимым.
- **Российская правовая граница:** Точный review target требует трех приемов подготовки межсудебной позиции: операционного толкования, ответа на отраслевые возражения и исполнимого пути внедрения. Проверенные нормы устанавливают силу и пределы применения решений КС РФ, но не предписывают этот трехэлементный метод как универсальный российский стандарт. Поэтому карточка остается illustrative/comparative_only: техника может служить QA ясности и исполнимости, если не подменяет обязательную силу конкретного решения, компетенцию адресата или предусмотренный законом способ исполнения. Пределы: Использовать адресную межсудебную мотивировку только как сравнительный QA-прием, а не как обязательный тест КС РФ.; Операционное толкование и путь исполнения должны оставаться в пределах компетенции адресата и обязательной силы конкретного решения КС РФ.; Ответ на отраслевые возражения и описание внедрения не создают самостоятельного remedial-полномочия и не гарантируют фактическое исполнение.
- **Маршруты:** ksrf-echr-argumentation; ksrf-argument-patterns.
- **Provenance:** source review `source-review-c-tail-garlicki-dialogue-persuasion-04`; legal review `legal-anchor-c-r2-094`; source SHA-256 `8d1198ecf8ca06094eb5b6fa4f5e08e46d47ca9baa8126ea7f857fccb7018dd8`.

<a id="cmc-scalia-rules-equality-predictability-01"></a>
### `cmc-scalia-rules-equality-predictability-01` — Antonin Scalia

- **Работа и locator:** The Rule of Law as a Law of Rules; печат. 1178–1179; PDF 4–5; раздел Основной текст, преимущества общих правил.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При выборе между категориальным тестом и открытым балансированием нужно явно учитывать равенство сопоставимых дел, предсказуемость и цену неизбежного переохвата правила.
- **Когда полезна:** Аргумент предлагает открытый тест по совокупности обстоятельств либо жесткое категориальное правило.
- **Предусловия:** Определен класс сопоставимых случаев.; Доступны примеры пограничных ситуаций.
- **Остановиться или воздержаться:** Класс случаев не определен.; Издержки категориального правила не исследованы.
- **Оговорки источника:** Автор сравнивает общие судебные правила с подходом по совокупности обстоятельств.; Преимущество правила не объявлено безусловным для любой ситуации.
- **Источник не доказывает:** Любое простое правило не становится справедливым или конституционным.; Предсказуемость не оправдывает сохранение тяжелого нарушения права.
- **Фальсификаторы и пределы переноса:** Высокая вариативность фактов может делать общее правило чрезмерно грубым.; Применимый текст может прямо требовать учета совокупности обстоятельств.
- **Контрпример:** Ясное правило обеспечивает одинаковый результат, но несправедливо охватывает редкий чрезвычайный случай.
- **Не использовать для:** Не считать определенность абсолютной ценностью.; Не импортировать американский метод толкования.
- **Российская правовая граница:** Равенство, определенность и предсказуемость являются действующими конституционными ориентирами, поэтому их необходимо учитывать при выборе формы критерия. Но Скалиа делает дополнительный нормативный выбор в пользу правил, которого российские источники не предписывают; цена переохвата и допустимость открытого стандарта зависят от предмета. Пределы: Не выводить из равенства автоматическое преимущество категориального правила.; Ясное правило также проверяется на необоснованное различие, переохват и умаление права.; Постановление № 35-П касается конкретного имущественного регулирования и не является общим трактатом о правилах и стандартах.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-tail-scalia-rules-equality-predictability-01`; legal review `legal-anchor-c-r2-095`; source SHA-256 `f3f7949c1d81b1e1a9447becce786305c4f29e5b806dc6f4bdd1d54a636d781d`.

<a id="cmc-scalia-rules-constrain-judges-02"></a>
### `cmc-scalia-rules-constrain-judges-02` — Antonin Scalia

- **Работа и locator:** The Rule of Law as a Law of Rules; печат. 1179–1180; PDF 5–6; раздел Основной текст, правила как самоограничение суда.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Правовую позицию следует формулировать как воспроизводимый критерий и проверять его на деле с противоположно желаемым результатом для выявления скрытой дискреции.
- **Когда полезна:** Предлагаемый тест поддерживает желаемый результат только в текущем деле.
- **Предусловия:** Сформулирован операциональный критерий.; Есть сопоставимый контрпример с иным предпочтительным исходом.
- **Остановиться или воздержаться:** Критерий нельзя применить вне текущих фактов.; Исключения вводятся после получения нежелательного результата.
- **Оговорки источника:** Аргумент относится к судебно создаваемым правилам в системе прецедента.; Открытый тест не исключает мотивировки, но затрудняет демонстрацию несогласованности.
- **Источник не доказывает:** Самосвязывание правилом не гарантирует его нормативную правильность.; Последующее отступление может быть допустимо при надлежащем обосновании.
- **Фальсификаторы и пределы переноса:** Некоторые стандарты неизбежно требуют оценочного суждения.; Новое существенное обстоятельство может оправдать разграничение.
- **Контрпример:** Тест «совокупности обстоятельств» меняет вес факторов всякий раз, когда прежнее правило ведет к нежелательному исходу.
- **Не использовать для:** Не запрещать мотивированное отступление.; Не считать всякий стандарт произволом.
- **Российская правовая граница:** Обязательность решений КС РФ для адресатов не тождественна предложенной Скалиа модели самосвязывания автора правилом. Проверка критерия на противоположном примере полезна как тест скрытой дискреции, но не является российской нормой и не может доказывать обязательность будущего результата. Пределы: Не смешивать общеобязательность решения с абсолютным запретом КС РФ развивать или уточнять позицию.; Контрпример должен проверять равные юридически значимые обстоятельства, а не только желаемый исход.; QA-тест не устанавливает компетенцию, допустимость или средство защиты.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-tail-scalia-rules-constrain-judges-02`; legal review `legal-anchor-c-r1-096`; source SHA-256 `f3f7949c1d81b1e1a9447becce786305c4f29e5b806dc6f4bdd1d54a636d781d`.

<a id="cmc-scalia-rules-limit-03"></a>
### `cmc-scalia-rules-limit-03` — Antonin Scalia

- **Работа и locator:** The Rule of Law as a Law of Rules; печат. 1187; PDF 13; раздел Заключительные оговорки автора.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Перед применением открытого баланса нужно исчерпать доступные общие критерии, а затем явно обозначить остаточный фактический или оценочный вопрос, который нельзя корректно категоризировать.
- **Когда полезна:** Анализ сразу переходит к общей совокупности обстоятельств без промежуточных правил.
- **Предусловия:** Определен нормативный текст и класс случаев.; Исследованы возможные устойчивые критерии.
- **Остановиться или воздержаться:** Предлагаемое правило не имеет текстовой или иной нормативной опоры.; Пограничные случаи показывают неприемлемый переохват.
- **Оговорки источника:** Автор прямо признает пределы категориальных правил.; Он оставляет открытым трудный вопрос о том, когда открытый анализ неизбежен.
- **Источник не доказывает:** Тезис не разрешает без обоснования заменить любой оценочный стандарт жестким правилом.; Балансирование не объявляется всегда нелегитимным.
- **Фальсификаторы и пределы переноса:** Прямое предписание учитывать все обстоятельства ограничивает категоризацию.; Недостаток опыта может не позволять безопасно сформулировать правило.
- **Контрпример:** Редкий чрезвычайный случай требует индивидуальной оценки после применения всех устойчивых общих критериев.
- **Не использовать для:** Не устранять судебное суждение фиктивной точностью.; Не превращать предпочтение правил в абсолют.
- **Российская правовая граница:** Российские источники требуют мотивированного учета нормы, ее места в системе и обстоятельств, но не устанавливают приоритет правил над стандартами по Скалиа. Двухшаговая техника допустима как организация анализа, если не скрывает релевантные исключения и не меняет официальный критерий. Пределы: Не представлять остаточный баланс как разрешенную суду свободную дискрецию.; Прямой текст и обязательное истолкование имеют приоритет над методическим предпочтением формы критерия.; Выбор между правилом и стандартом должен быть обоснован предметом конкретного права.
- **Маршруты:** ksrf-argument-patterns; ksrf-complaint-qa.
- **Provenance:** source review `source-review-c-tail-scalia-rules-limit-03`; legal review `legal-anchor-c-r1-097`; source SHA-256 `f3f7949c1d81b1e1a9447becce786305c4f29e5b806dc6f4bdd1d54a636d781d`.

<a id="cmc-habermas-cooriginal-autonomy-01"></a>
### `cmc-habermas-cooriginal-autonomy-01` — Jürgen Habermas

- **Работа и locator:** Constitutional Democracy: A Paradoxical Union of Contradictory Principles?; печат. 767; PDF derived 2 / original sample 8; раздел § 1, co-originality of private and public autonomy.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** В конфликте личной свободы и демократического решения нужно проверять двустороннюю зависимость: как ограничение частной автономии влияет на равное гражданство и как участие обеспечивает равную реальность частных свобод.
- **Когда полезна:** Ограничение права оправдывается только демократическим происхождением закона либо право представляется внешним пределом без связи с самоопределением.
- **Предусловия:** Определены частная свобода и форма политического участия.; Показано воздействие меры на обе стороны автономии.
- **Остановиться или воздержаться:** Одна сторона автономии лишь декларирована без фактов.; Демократическое происхождение нормы используется как достаточное оправдание любого ограничения.
- **Оговорки источника:** Автор отвергает простое ранжирование прав человека и народного суверенитета.; Тезис относится к нормативному обоснованию конституционной демократии.
- **Источник не доказывает:** Публичная цель не получает автоматический приоритет над частным правом.; Теория не устанавливает конкретный результат российского спора.
- **Фальсификаторы и пределы переноса:** Конкретное право может иметь специальную нормативную структуру.; Философская взаимозависимость не заменяет официальный тест ограничения.
- **Контрпример:** Формально принятый большинством закон лишает группу условий для равного политического участия и тем самым подрывает собственную демократическую легитимацию.
- **Не использовать для:** Не растворять индивидуальные права в воле большинства.; Не превращать теорию в готовую формулу исхода.
- **Российская правовая граница:** Конституция отдельно защищает личные права, равенство и участие в управлении, но не закрепляет философскую взаимозависимость Хабермаса как самостоятельный критерий проверки. Двусторонний вопрос может расширять аргумент, однако каждый вывод должен опираться на конкретное право и установленный стандарт ограничения. Пределы: Не выводить юридическое нарушение непосредственно из философской категории автономии.; Нужно назвать конкретные конституционные права, адресата обязанности и форму вмешательства.; Связь политического участия и частной свободы требует фактического обоснования в конкретном деле.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-c-tail-habermas-cooriginal-autonomy-01`; legal review `legal-anchor-c-r1-098`; source SHA-256 `11ee5f5efd5c0d30dbeaf75a615dd81a9f7deaa0aed1a7d21f94731a07e9b19d`.

<a id="cmc-habermas-constitution-project-02"></a>
### `cmc-habermas-constitution-project-02` — Jürgen Habermas

- **Работа и locator:** Constitutional Democracy: A Paradoxical Union of Contradictory Principles?; печат. 774–776; PDF derived 9–11 / original sample 15–17; раздел § 4, constitution as a self-correcting historical project.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Историю правовой позиции нужно оценивать как последовательность проблем, включения ранее исключенных интересов, коррекций и регрессий, а не как линейное подтверждение текущего результата.
- **Когда полезна:** Текущая позиция обосновывается историей толкования или необходимостью ее пересмотра.
- **Предусловия:** Собрана хронология первичных решений и нормативных изменений.; Определен постоянный нормативный вопрос.
- **Остановиться или воздержаться:** История восстановлена по вторичным пересказам без первичных актов.; Современный смысл объявлен прогрессом без нормативного критерия.
- **Оговорки источника:** Самокоррекция является долгосрочной нормативной интерпретацией, а не гарантированным фактом.; Автор прямо признает возможность прерываний и исторических регрессий.
- **Источник не доказывает:** Любое изменение толкования не является прогрессом.; История сама по себе не легитимирует современную интерпретацию.
- **Фальсификаторы и пределы переноса:** Разрыв конституционного режима может ограничить модель единого проекта.; Позднейшее решение может быть регрессом, а не обучением.
- **Контрпример:** Поздняя практика сужает равное участие маргинализированной группы и потому не становится улучшением только из-за хронологической новизны.
- **Не использовать для:** Не читать историю телеологически.; Не объявлять доктринальный проект действующим правом.
- **Российская правовая граница:** История поправок и развитие толкования показывают изменение правового материала, но не подтверждают нормативную теорию обучения, включения и регрессии. Историческая карта полезна для исследования, однако действующий смысл определяется официальным текстом и обязательными решениями, а не предполагаемым направлением проекта. Пределы: Не оценивать действительность нормы по соответствию философской траектории прогресса.; Каждый исторический этап нужно подтверждать актом, редакцией, датой действия и официальным толкованием.; Нельзя смешивать желаемую коррекцию с установленным действующим правом.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-c-tail-habermas-constitution-project-02`; legal review `legal-anchor-c-r1-099`; source SHA-256 `11ee5f5efd5c0d30dbeaf75a615dd81a9f7deaa0aed1a7d21f94731a07e9b19d`.

<a id="cmc-habermas-rights-two-stages-03"></a>
### `cmc-habermas-rights-two-stages-03` — Jürgen Habermas

- **Работа и locator:** Constitutional Democracy: A Paradoxical Union of Contradictory Principles?; печат. 777–778; PDF derived 12–13 / original sample 18–19; раздел § 5, two stages in the genesis of basic rights.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При аргументации нужно отдельно сформулировать структурную функцию права и доказать, какое конкретное содержание требуется в обстоятельствах дела.
- **Когда полезна:** Довод перескакивает от общего права к конкретному требованию без промежуточного обоснования.
- **Предусловия:** Определена абстрактная категория права.; Установлены конкретные риски и потребности дела.
- **Остановиться или воздержаться:** Конкретное притязание выведено только из названия права.; Контекстуальная потребность не подтверждена.
- **Оговорки источника:** Первый этап дает категории прав без полного конкретного содержания.; Второй этап требует эмпирической информации о рисках и потребностях регулирования.
- **Источник не доказывает:** Абстрактная категория права не предрешает каждую конкретную гарантию.; Историческая конкретизация не может игнорировать равную свободу и участие.
- **Фальсификаторы и пределы переноса:** Официальный текст может уже задавать более точное содержание.; Разные конкретизации могут одинаково реализовывать структурную функцию.
- **Контрпример:** Общая ссылка на частную жизнь не объясняет конкретное требование защиты данных без анализа новых информационных рисков.
- **Не использовать для:** Не подменять норму философской реконструкцией.; Не считать одну конкретизацию единственно возможной без сравнения.
- **Российская правовая граница:** Российский анализ действительно должен связать конституционную гарантию с обстоятельствами применения, но официальные источники не закрепляют философскую двухстадийную конструкцию карточки. Разделение функции и конкретного требования допустимо как схема аргумента, если оба вывода независимо подтверждены текстом, обязательным толкованием и фактами. Пределы: Не превращать структурную функцию права в новую ненаписанную гарантию.; Конкретное содержание должно вытекать из действующей нормы и релевантной официальной позиции, а не только из философской необходимости.; Схема не заменяет допустимость жалобы, компетенцию и способ защиты.
- **Маршруты:** ksrf-argument-patterns; ksrf-rights-argument-builder.
- **Provenance:** source review `source-review-c-tail-habermas-rights-two-stages-03`; legal review `legal-anchor-c-r1-100`; source SHA-256 `11ee5f5efd5c0d30dbeaf75a615dd81a9f7deaa0aed1a7d21f94731a07e9b19d`.

<a id="cmc-kelsen-general-annulment-01"></a>
### `cmc-kelsen-general-annulment-01` — Ханс Кельзен

- **Работа и locator:** El control de la constitucionalidad de las leyes: estudio comparado de las constituciones austriaca y norteamericana; печат. 84; PDF 4; раздел Раздел II, общий эффект аннулирования неконституционной нормы.
- **Статус:** source `passed/keep`; legal `qualified/revise`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** При анализе модели конституционного контроля нужно раздельно фиксировать орган контроля, объём решения, круг адресатов и момент прекращения действия нормы.
- **Когда полезна:** В проекте жалобы смешиваются неприменение нормы в деле, её общее аннулирование и момент утраты силы.
- **Предусловия:** Определён вид оспариваемого нормативного акта.; Доступны официальные правила о полномочиях КС РФ и последствиях его решения.
- **Остановиться или воздержаться:** Официальные российские правила о последствиях решения не проверены.; Историческая австрийская конструкция подаётся как действующее российское право.
- **Оговорки источника:** Тезис относится к исторической австрийской модели, рассматриваемой автором.; Автор отдельно указывает на преимущественно перспективное действие и специальные исключения.
- **Источник не доказывает:** Описание не устанавливает последствия решений КС РФ.; Из тезиса не следует, что всякое признание нормы неконституционной автоматически имеет одинаковый временной эффект.
- **Фальсификаторы и пределы переноса:** Иная модель контроля может предусматривать только неприменение либо специальные последствия.; Временной эффект зависит от применимого официального регулирования и самого решения.
- **Контрпример:** Отказ суда применить норму лишь в одном споре не равнозначен её общему прекращению для будущих случаев.
- **Не использовать для:** Не переносить историческую австрийскую модель в российское право без проверки.; Не предсказывать резолютивную часть будущего решения КС РФ.
- **Российская правовая граница:** Российское право подтверждает полезность карты «орган — объем — адресаты — момент — последствия», но материальная формула Кельзена относится к иной системе. В России необходимо дополнительно различать вид решения, выявленное истолкование, непосредственное действие, общий запрет применения и пересмотр конкретного дела. Пределы: Не переносить австрийский момент аннулирования и перспективность как готовое описание российского права.; Учитывать специальные временные и компенсационные правила статьи 79 и последствия для дела заявителя.; Точный результат определяется Конституцией, ФКЗ и резолютивной частью конкретного постановления.
- **Маршруты:** ksrf-argument-patterns; ksrf-case-triage.
- **Provenance:** source review `source-review-c-tail-kelsen-general-annulment-01`; legal review `legal-anchor-c-r2-101`; source SHA-256 `94a13b723913faf0c33a814b6c037c3e2d6a21b4df6c9a3d9091bbbfc409d94d`.

<a id="cmc-kelsen-indirect-review-public-interest-03"></a>
### `cmc-kelsen-indirect-review-public-interest-03` — Ханс Кельзен

- **Работа и locator:** El control de la constitucionalidad de las leyes: estudio comparado de las constituciones austriaca y norteamericana; печат. 88; PDF 8; раздел Раздел III, косвенный путь контроля и инициатива суда ex officio.
- **Статус:** source `passed/keep`; legal `illustrative/comparative_only`; `law_as_of=2026-08-14`.
- **Методическая гипотеза:** Перед использованием сравнительной процедуры нужно разложить её на инициатора, процессуальный триггер, усмотрение суда и защищаемый интерес.
- **Когда полезна:** Иностранное описание контроля используется без различения права стороны и полномочия суда.
- **Предусловия:** Установлен процессуальный маршрут, описанный источником.; Известны российские правила обращения и передачи конституционного вопроса.
- **Остановиться или воздержаться:** Иностранная историческая процедура выдаётся за российскую.; Не проверены специальные условия обращения заявителя в КС РФ.
- **Оговорки источника:** Тезис относится к конкретному историческому устройству косвенного контроля.; Автор противопоставляет этот путь иным способам инициирования контроля.
- **Источник не доказывает:** Описание не устанавливает российские правила обращения в КС РФ.; Оно не означает, что частный интерес не имеет значения в любом конституционном процессе.
- **Фальсификаторы и пределы переноса:** Прямой индивидуальный доступ к конституционному суду изменяет распределение процессуальной инициативы.; Право стороны требовать рассмотрения может быть прямо закреплено и не сводиться к предложению суду.
- **Контрпример:** Прямо предусмотренная законом индивидуальная жалоба не совпадает с обращением стороны к обычному суду с просьбой инициировать контроль ex officio.
- **Не использовать для:** Не выводить допустимость российской жалобы из австрийской модели.; Не отрицать частный интерес заявителя без анализа применимого права.
- **Российская правовая граница:** Историческая процедура не совпадает с действующей российской моделью: Конституция и ФКЗ предусматривают как индивидуальную жалобу, так и запрос суда при разных предпосылках. Карточка сама предлагает лишь разложить сравнительный маршрут, поэтому ее можно оставить иллюстрацией, но не использовать для утверждения об отсутствии у стороны собственного права на обращение. Пределы: Не описывать действующий российский контроль как исключительно косвенный или запускаемый только судом.; Отдельно проверять требования индивидуальной жалобы по статьям 96–100 и запроса суда по статьям 101–102 ФКЗ.; Историческое распределение публичного и частного интереса не определяет современную российскую допустимость.
- **Маршруты:** ksrf-argument-patterns; ksrf-case-triage.
- **Provenance:** source review `source-review-c-tail-kelsen-indirect-review-public-interest-03`; legal review `legal-anchor-c-r1-103`; source SHA-256 `94a13b723913faf0c33a814b6c037c3e2d6a21b4df6c9a3d9091bbbfc409d94d`.
