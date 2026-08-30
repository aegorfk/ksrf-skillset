---
name: ksrf-argument-patterns
description: Скилл находит, проверяет и ограничивает перенос аргументативных аналогий из постановлений и заседаний КС РФ. Он применяется как необязательная библиотека гипотез, поисковых терминов, контрпримеров и формул, когда нужно проверить новую конституционно-правовую линию; он не служит закрытой типологией или обязательным обоснованием жалобы.
---

# Паттерны аргументации КС РФ как исследовательская библиотека

## Роль в filing-readiness

Pattern/refusal cards остаются critic и candidate layer. Они не доказывают official source, редакцию или применение нормы и не закрывают issue option автоматически. Для отказных аналогов используй evidence roles и coverage language из `../ksrf-complaint-cycle/references/failed-complaint-corpus.md`.

## Роль

Этот скилл не выбирает правовую позицию за исследователя и не устанавливает исчерпывающий перечень допустимых аргументов. Он превращает корпус Постановлений, стенограмм и вспомогательных материалов в candidate findings:

- возможные аналогии и различия;
- термины и направления поиска;
- контрпримеры и refusal risks;
- доказательственные вопросы;
- варианты узкого remedy и языка КС РФ.

Pattern match становится опорой только после ручной проверки официального акта, точного locator и переносимости.

## Корпус и происхождение

Для обычной работы используй встроенные references этого skillset и `../ksrf-complaint-cycle/references/offline-practice-core.md`. Они содержат автономную методологию и не требуют доступа к локальному проекту, Telegram, Zakon.ru или исходным research-корпусам. Внешние корпуса нужны только для обновления, расширенного discovery или аудита происхождения. Не цитируй generated card без проверки source anchor и quote locator в официальном тексте.

Для доктринального и сравнительного поиска используй `references/constitutionalist-authority-corpus.md` как маршрут, а `references/constitutionalist-authority-corpus.json` как полный реестр авторов, работ, алиасов, тематических направлений и статусов готовности. Начинай с `method_integrated`, затем `full_text_available` и `triangulated_academic`. `academic_indexed` и `bibliographic_lead` требуют открытия самой работы; `discovery_only` — только поисковый lead, а не авторитет для жалобы. Для 19 прошедших pre-promotion карточек открой `references/constitutional-methodology-verified-cards.md`; для остальных 84 source/legal-reviewed методов — `references/constitutional-methodology-reference-only-corpus.md`. Второй файл используется только для option generation, red-team и границ переноса: `revise|comparative_only` не становятся обязательными инструкциями без eval и human approval. Для проверенного российского Lawinfo-среза 2023–2026 используй `references/lawinfo-constitutional-methods-2023-2026.md` и его JSON: это операционные карточки с DOI, страницами, fingerprints и явным российским official-anchor gate. Для исторических вопросов о предмете жалобы, Секретариате, сроке/исчерпании, доказательствах, видах решений, правовых позициях и исполнении открывай `../ksrf-complaint-cycle/references/lawinfo-historical-complaint-procedure-2009-2024.md`; его JH-M карточки — только reference-only critic layer с обязательным current-law check.

## Порядок работы

1. Получи нейтральный профиль из `ksrf-explore-arguments`: норма, судебный смысл, механизм, вред, стадия, предполагаемый remedy и неизвестные звенья.
2. Сформулируй несколько поисковых представлений:
   - точная норма и системная связка;
   - механизм вреда;
   - право/институциональная гарантия;
   - доказательственный носитель;
   - remedy;
   - лучший контраргумент.
3. Используй `references/pattern-matrix.md`, `references/constitutional-graph.md`, hearing materials, `references/external-ks-complaint-webinar-methods.md` и retrieval architecture как карты кандидатов. Не обязан выбирать ни одного семейства. Вебинарный материал используй только как профессиональный checklist и red-team слой, а не как официальный источник позиции КС РФ.
4. Для каждого кандидата открой `references/decision-index.md` и официальный акт. Проверь:
   - что позиция принадлежит КС РФ, а не стороне;
   - норму, редакцию и временной контекст;
   - mechanism/harm/remedy;
   - отрицательную или сохраняющую формулу;
   - последующее изменение регулирования.
5. Запиши candidate finding по контракту `../ksrf-explore-arguments/references/artifact-contracts.md` с relation `supports`, `weakens`, `distinguishes` или `blocks`.
6. Ищи минимум один контрпример или более узкую позицию для сильной аналогии. Лексическое, векторное или графовое сходство не доказывает переносимость.
7. Если гипотезе нужна доктринальная методика, сначала используй встроенные `references/constitutional-methodology-verified-cards.md` и `references/constitutional-methodology-reference-only-corpus.md` в пределах их статуса и guardrails. Открывай исходную работу только для прямой цитаты, атрибуции нового тезиса или выхода за пределы встроенной карточки. Если работа недоступна, поставь `source_unavailable`: методическую карточку можно использовать как внутренний вопрос или red-team ход, но нельзя приписывать автору неподтверждённую формулу. Для критики позиции высшего суда проверь доктринальную память, системные связи, право/привилегию и усмотрение/доказываемый факт. Когда нужно воспроизводимо разобрать мотивировку или иностранный пример, используй `references/comparative-argument-coding.md`: код типа не определяет юридический вес, а иностранный материал остаётся `ResearchFinding` до отдельного российского якоря. Не вставляй фамилию ради усиления риторики.
   Если срабатывает Lawinfo-триггер, примени соответствующие LI-M карточки. Для каждого существенного довода проведи текстовую, интенциональную, consistency- и pragmatic-атаку; у семейств нет заранее заданной иерархии. При неопределённости отдели устойчиво конкурирующие подходы от единичной судебной ошибки; при языке ценностей или достоинства потребуй защищаемое благо, носителя, конкурирующую гарантию, конкретный вред и remedy.
   Для построения и атаки конкретного российского конституционного довода используй `references/constitutional-argument-architecture.md`: отдели главный тезис, прескриптивный/дескриптивный/оценочный уровни, поверхность атаки, competence и consequences gates. Научная модель не заменяет официальный якорь и не устанавливает вес типа аргумента.
   Если спор касается уровня абстракции, правила и его основания, holding/analogy либо цели толкования, открой `references/legal-reasoning-model-branches.md`: запускай конкурирующие модели параллельно и сохраняй `model_conflict`, не выбирая школу голосованием. Для воспроизводимой реконструкции ratio, силы прецедента, различения и defeasible argument graph дополнительно используй `references/precedent-analogy-and-justification.md`; сходство, найденное retrieval, не является relevance rule. Для иностранного института или довода заполни `references/institutional-discourse-and-comparative-transfer.md`, а при вопросах доступа, предмета жалобы, взаимодействия институтов или эффекта решения — `references/constitutional-institutions-access-and-remedy.md`; сходство названия или функции не закрывает contextual transfer и российский competence gate.
8. Передай findings обратно в argument ledger. Если практика высших судов исследуется через CasusLegal, маршрутизируй проверенные кандидаты через `ksrf-practice-authority-builder`: сохрани тот же relation, добавь authority role, source status, transfer limit и adverse pass. Не собирай обязательный пакет `основной + усиливающий + сохраняющий + remedy`, если структура дела требует иного портфеля.

## Семейства как поисковые seeds

Текущий реестр включает practice split, certainty, constitutional meaning, proportionality, balance, effective remedy, procedural guarantees, equality, expectations, retroactivity, non-mechanical application, liability fairness, compensation, positive obligations, competence, legislative gaps, good faith, dignity, international standards и execution.

Список не закрыт. Новая гипотеза допустима, если она опирается на проверенные источники и проходит hard gates/critic review. Бремя доказывания, причинность, статистика, expert и amicus materials могут быть самостоятельным направлением исследования механизма, даже если в финальном аргументе работают как доказательственный слой.

## Справочники

- `references/pattern-matrix.md` и `references/decision-index.md` — candidate map и акты для проверки.
- `references/argument-techniques-from-decisions.md`, `references/hearing-derived-argument-patterns.md`, `references/hearing-constitutional-justifications.md`, `references/hearing-argument-techniques.md` — эвристики, вопросы и stress-tests, не обязательные схемы.
- `references/external-ks-complaint-webinar-methods.md` — профессиональная методика из вебинара о жалобе в КС РФ: нормативный барьер, четыре дефекта, неединичность практики, ранняя фиксация нормы, ходатайство о запросе суда, ответ на возврат Секретариата и red-team системных последствий; не официальный источник права.
- `references/evidence-maps.md`, `references/source-proof-impact-patterns.md`, `references/counterargument-playbook.md` — проверка материала и adverse case.
- `references/language-formulas.md` и `references/argument-package-builder.md` — drafting options после выбора портфеля.
- `references/constitutional-graph.md`, `references/constitutional_graph.json`, `references/position-retrieval-architecture.md` — candidate generation и обход связей.
- `../ksrf-complaint-cycle/references/offline-practice-core.md` — обязательный автономный baseline по маршруту, допустимости, drafting, filing и исполнению.
- `../ksrf-practice-authority-builder/SKILL.md` — превращение CasusLegal findings в проверяемый authority ledger и блоки аргумента.
- `references/complaint-methodology-sources.md` — provenance и журнал источников обновления; для runtime-работы не требуется.
- `references/constitutionalist-authority-corpus.md` и `constitutionalist-authority-corpus.json` — широкий корпус авторов и работ с маршрутами, статусом извлечения и предохранителями.
- `references/constitutional-methodology-verified-cards.md` — 19 source/legal и model-conflict-reviewed pre-promotion карточек широкой волны, их locators, пределы переноса, overlap-роль и нерешённые conflict-abstain условия; human conflict gate остаётся отдельным.
- `references/constitutional-methodology-reference-only-corpus.md` — остальные 84 source/legal-reviewed карточки с triggers, stop-условиями, контрпримером и российской правовой границей; только option generation и red-team, без изменения behavior.
- `references/constitutionalists-folder-methodology-deltas.md` — автономный разбор 24 PDF из папки «Конституционалисты»: три независимо аудированные `reference_only` дельты и карта 12 поглощённых находок без дублирования действующих методов. Открывай только при совпавшем исследовательском trigger; до отдельной current-law/conflict review, held-out evaluation и явного human approval справочник не меняет обязательный шаг, hard gate, stop condition, классификацию или output KSRF skills.
- `references/comparative-argument-coding.md` — воспроизводимая кодировка структуры и типов доводов, раздельная оценка наличия/веса и function-first gate для иностранного материала.
- `references/constitutional-argument-architecture.md` — главный тезис, трёхуровневая трасса, четыре типа, attack ledger, институциональная компетентность и последствия по российской научной методике.
- `references/constitutional-review-methods.md` — выбор между переносом позиции, атакой правоприменительного смысла, сохраняющим истолкованием, соразмерностью и вспомогательным методом, когда совпал этот методический trigger.
- `references/enrichment-artifact-contract.md` — структурная граница локального `expanded_pattern_registry.json` для скрипта обогащения; она не заменяет проверку источников и содержания.
- `references/legal-reasoning-model-branches.md` — правила/принципы, under-/over-inclusion, holding/analogy, лестница абстракции, purpose и hard-case branch set без выбора «правильной» школы.
- `references/institutional-discourse-and-comparative-transfer.md` — strongest-objection ledger и contextualized functionalism для иностранного материала; архитектурно-визуальные описания остаются `context_only`.
- `references/precedent-analogy-and-justification.md` — internal/external justification, эмпирический precedent questionnaire, competing analogy branches, universalization boundaries и defeasible graph с `model_conflict -> abstain`.
- `references/constitutional-institutions-access-and-remedy.md` — сравнительные matrices модели контроля, доступа, предмета жалобы, институционального ответа и фактического эффекта remedy; каждый российский вывод требует отдельного первичного якоря.
- `references/lawinfo-constitutional-methods-2023-2026.md` и `references/lawinfo_constitutional_method_cards.json` — 15 полнотекстовых российских методических карточек: субъективная заинтересованность, четыре семейства атак, определённость, пропорциональность, ценности, достоинство, anti-appeal, конфликт классификаций абсолютного права и пределы remedy; научная карточка не заменяет действующее право.
- `../ksrf-complaint-cycle/references/lawinfo-historical-complaint-procedure-2009-2024.md` — 38 исторических/вторичных статей как 13 bounded JH-M critic cards: нормативный предмет, screening/refusal, versioned exhaustion, роли доказательств, виды решений, private/public tracks, certainty, compensation/proportionality, force и execution; reference-only и без изменения behavior.
- `../ksrf-complaint-cycle/references/sko-complaint-methods-2017-2026.md` — полнотекстовые карточки двенадцати статей СКО и оставшийся разведочный lead из тех же номеров.

## Инструменты

Для анализа одного дела используй bundled references и автономное ядро. Read-only Qdrant/Neo4j и штатные scripts являются необязательным maintenance/retrieval слоем: если они доступны, перед retrieval строй query profile и сверяй качество на golden/hard-negative наборах; если отсутствуют, отметь только предел поиска аналогий. Не запускай глобальное обогащение корпуса, если пользователю нужен анализ одного дела.

`scripts/build_constitutionalist_authority_corpus.py` воспроизводит широкий реестр из библиографии Блохина, официальных указателей СКО/«Международного правосудия», локального discovery-корпуса Zakon.ru и проверенных методических карточек. Его результат не повышает статус источника автоматически.

## Вывод

Для каждого кандидата:

- `Candidate pattern/technique`;
- `Official decisions and locators`;
- `Что совпадает`;
- `Что различается`;
- `Relation to hypothesis`;
- `Transfer limit`;
- `Counterexample/refusal risk`;
- `Нужная проверка`;
- `Возможный language/remedy option`.

Отдельно перечисли `no close analogy found`, если это честный результат. Не превращай его в отрицательное юридическое заключение.
