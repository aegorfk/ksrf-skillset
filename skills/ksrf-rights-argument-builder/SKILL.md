---
name: ksrf-rights-argument-builder
description: Превратить утверждённый портфель гипотез в проверяемые разделы правовой позиции для жалобы в КС РФ. Используй, когда нужно собрать основной и резервный аргументы, выбрать подходящую структуру проверки, связать источники с тезисами и remedy, не подгоняя дело под заранее заданный тест или корпусный паттерн.
---

# Сборка правовой позиции для жалобы в КС РФ

## Вход

Работай от `ArgumentPortfolio`, созданного через `ksrf-explore-arguments`. Если портфель отсутствует, сначала верни дело в автономное исследование, которое само выводит кандидатов права и последствия из материалов; не проси пользователя выбрать конституционную статью или готовую квалификацию. Если principal выбран без human approval, верни портфель на утверждение. Не выбирай ближайший паттерн вместо этого шага.

Обязательные входы:

- hard gates по норме, применению, делу, исчерпанию и сроку;
- principal и, если есть, reserve hypothesis;
- supporting/adverse findings с locators;
- authority ledger из `ksrf-practice-authority-builder`, если использовалась практика высших судов или CasusLegal;
- refusal model, falsifier и ограничения переноса;
- предполагаемая просительная формула.

## Порядок работы

1. Сверь факты и источники с `CaseFile`; найденное автоматически не становится доказанным без проверки.
2. Для каждой утверждённой гипотезы выбери структуру, которая лучше объясняет именно её механизм. Допустимы:
   - вопрос -> правило -> применение -> вывод;
   - механизм нормы -> непосредственный вред -> стандарт контроля -> remedy;
   - competing interpretations -> constitutional limit -> сохраняющий смысл;
   - обязанность/гарантия -> нормативный барьер -> неэффективность -> минимальное исправление.
3. Явно отдели:
   - Конституцию, закон и проверенные позиции КС РФ;
   - материалы дела;
   - официальные данные;
   - научную/эмпирическую методику;
   - международный, сравнительный или состязательный материал.
4. Из `ksrf-argument-patterns` и его references бери только проверенные аналогии, формулы и counterarguments. Для каждой аналогии покажи совпадение и различие нормы, механизма вреда, институционального контекста и remedy.
5. Для научной методики начни со встроенных карточек `../ksrf-argument-patterns/references/constitutional-methodology-verified-cards.md` и `../ksrf-argument-patterns/references/constitutional-methodology-reference-only-corpus.md`; `../ksrf-argument-patterns/references/constitutionalist-authority-corpus.md` используй как маршрут расширения. Конкретную работу нужно открывать только для прямой цитаты, атрибуции нового тезиса или выхода за пределы карточки. Если первоисточник недоступен, поставь `source_unavailable`, не цитируй и не приписывай автору формулу; продолжай с безымянной методической функцией карточки в пределах guardrail. `discovery_only` не используется как доктринальный авторитет. Для правоограничения и законодательных фактов открой `references/proportionality-and-lawmaking-workbook.md`: сравнительные модели работают как параллельные stress-tests, а материальный конфликт последовательностей требует `model_conflict -> abstain`, не выбора «главного» автора. Для главного тезиса, трёх уровней и отдельной проверки компетенции/последствий используй `../ksrf-argument-patterns/references/constitutional-argument-architecture.md`; эта научная архитектура не доказывает содержание Конституции.
   Если спор зависит от rules/principles, уровня абстракции, аналогии или цели, используй `../ksrf-argument-patterns/references/legal-reasoning-model-branches.md`. Если довод вводит баланс, идентичность или социальную эволюцию как мета-паттерн, до drafting проверь trigger и доказательства по `../ksrf-complaint-qa/references/meta-argumentation-qa.md`.
   Если спор касается дискриминации или intersectionality, позитивной обязанности, горизонтального эффекта, достоинства, границы `scope -> interference -> justification` либо предполагаемого конфликта двух прав, используй `references/equality-positive-obligations-and-right-boundaries.md`. MF-14–18 и genuine-conflict gate из него остаются `idea_only`: применяй workflows как исследовательские и QA-карточки, сохраняй российские официальные anchors обоих прав и возвращай `model_conflict -> abstain`, когда выбор ветви меняет результат.
   Если сравнительный довод зависит от устройства органа, предмета контроля, доступа, процедуры или эффекта решения, заполни `references/constitutional-institutions-access-and-remedy.md`. Сопоставляй функции, а не одинаковые названия; иностранный institution passport не подтверждает российскую компетенцию, reopening или индивидуальное восстановление.
   Если линия касается официального электронного обращения, конфиденциальности, критики должностного лица или квалификации сообщения как публичного распространения по части второй статьи 128.1 УК РФ, используй `references/citizen-appeal-confidentiality-and-criticism.md`. Отдельно проверяй канал и круг доступа, ложность/порочащий характер, злоупотребление и применённую норму; использование Интернета само по себе не отвечает на все эти вопросы.
6. Если подходящего паттерна нет, построй аргумент непосредственно от нормы, официальных конституционных принципов, причинности и предлагаемой гарантии. Отсутствие аналогии укажи как transferability risk.
7. Для споров о доказывании заполни `references/evidence-impact-method.md`: классифицируй индивидуальные, содержательные законодательные, процедурные и процессуальные факты; укажи предмет, бремя, стандарт, доступ к информации, временную актуальность, возможность опровержения, последствие недоказанности и нормативный носитель. Не спорь только с весом отдельного доказательства и не смешивай доказываемое специальное основание с усмотрением по итоговому решению.
   Если довод касается социального права, доступности гарантии, институциональной сдержанности или фактической эффективности защиты, дополнительно заполни `references/social-rights-institutional-evidence.md`: разнеси reason, российскую официальную authority и social facts, проверь индикаторы, access funnel и individual bridge. Сравнительная методика не заменяет российский критерий и при неполных данных должна завершаться abstain.
8. Для каждого существенного тезиса дай evidence id, source anchor, locator и предел вывода. Непроверенное пометь `проверить`; adverse findings не убирай из черновика внутреннего memo.
9. Если передан authority ledger, используй только записи с подходящей ролью и `drafting_ready=true`; не превращай `application_evidence` ВС РФ в конституционный критерий и сохрани `transfer.limit` и adverse response в трассировке.
10. В частном споре построй `state-attribution bridge`: назови государственное нормативное правило, презумпцию, стандарт, закрытый перечень или обязательный смысл, который создал вред. Действия частного оппонента сами по себе не являются предметом нормоконтроля.
11. Для профессиональной гарантии раздели собственное право профессионала, гарантию права доверителя, публичную функцию института и процессуальную легитимацию заявителя. Не подменяй личное нарушение общей значимостью профессии.
12. Примени лучший контраргумент к principal hypothesis и покажи, почему reserve hypothesis остаётся самостоятельной, а не повторяет основную.
13. Сверь remedy с механизмом: требование должно устранять нормативный дефект, не просить отменить судебный акт и не предрешать факты.

## Вывод

- `Утверждённый портфель и причина выбора`;
- `Основной раздел` с evidence traceability;
- `Резервный раздел` либо причина его отсутствия;
- `Карта аналогий и пределов переноса`;
- `Adverse findings и ответы`;
- `Refusal model`;
- `Primary/narrower remedy`;
- `Недостающие материалы и verification tasks`.

## Ограничения

- Не выдавай constitutional test за обязательный только потому, что он есть в справочнике.
- Не считай corpus frequency, semantic similarity или число ссылок качеством аргумента.
- Не используй научный, международный или состязательный материал как замену российской правовой опоре.
- Не скрывай факт, что независимый critic не использовался или source locator не проверен.

## Справочники

- `../ksrf-complaint-cycle/references/offline-practice-core.md` — автономная архитектура аргумента, safety-valve, determinacy и evidence-role тесты.
- `../ksrf-complaint-cycle/references/strategic-complaint-design.md` — государственная связка частного спора, профессиональные гарантии и внешний эффект решения.
- `../ksrf-complaint-cycle/references/source-authority-and-route.md` — маршрут и реестр источников.
- `references/workflow-reference.md` — возможные тесты и формы раздела.
- `references/evidence-impact-method.md` — нормативный дефект доказывания и empirical layer.
- `references/social-rights-institutional-evidence.md` — reason/authority/social-fact trace, индикаторы социальных прав, четыре оси restraint, access funnel и evidence-acquisition/abstain.
- `references/proportionality-and-lawmaking-workbook.md` — authority/purpose, пригодность, альтернативы, маржинальный баланс, R1/R2 и critic-pass с запретом импортировать иностранную последовательность теста.
- `references/equality-positive-obligations-and-right-boundaries.md` — MF-14–18 и genuine-conflict gate для равенства/intersectionality, позитивных обязанностей, горизонтального эффекта, достоинства, границ и реального конфликта двух прав; evidence fields, stop/human gates и точные locators сравнительных источников.
- `references/constitutional-institutions-access-and-remedy.md` — InstitutionPassport по design/jurisdiction/access/proceeding/decision/effects/compliance с contextual transfer, current-law и российским competence gates.
- `references/citizen-appeal-confidentiality-and-criticism.md` — узкая current-law карточка № 43-П/2025 для официального интернет-обращения, конфиденциальности, критики должностных лиц и границы публичного распространения по части второй статьи 128.1 УК РФ.
- `../ksrf-argument-patterns/references/constitutional-argument-architecture.md` — главный тезис, трёхуровневая трасса, institutional competence и consequence critic с официальным российским gate.
- `../ksrf-argument-patterns/references/legal-reasoning-model-branches.md` — competing readings, under-/over-inclusion, purpose и hard-case branches с ручным разрешением конфликта.
- `../ksrf-complaint-qa/references/meta-argumentation-qa.md` — prerequisites баланса, идентичности и эволютивного подхода; научный trigger не заменяет российский тест.
- `references/complaint-patterns.md` — идеи дополнительных линий.
- `../ksrf-argument-patterns/references/*` — optional analogies, evidence maps, counterarguments, language formulas и retrieval.
- `../ksrf-argument-patterns/references/constitutionalist-authority-corpus.md` — выбор и проверка доктринального метода без name-dropping.
- `../ksrf-argument-patterns/references/constitutional-methodology-reference-only-corpus.md` — route-indexed сравнительные и adverse методы по правам; только гипотезы, counterexamples и transfer limits, не обязательный тест.
- `../ksrf-practice-authority-builder/SKILL.md` — роли практики высших судов, authority ledger и drafting blocks.
- `../ksrf-complaint-cycle/references/science-support-pack.md` — место и предел научных/экспертных материалов.
