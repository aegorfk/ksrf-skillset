---
name: ksrf-argument-patterns
description: Скилл строит и проверяет конституционно-правовые гипотезы, универсальные доводы за и против и узкие формулировки проблемы без исходного исследовательского корпуса. Применяется при анализе текста нового дела; отдельный режим проверяет аналогии и конкретные судебные позиции. Методика не является закрытой типологией и не определяет готовность жалобы.
---

# Паттерны аргументации КС РФ как исследовательская библиотека

## Сначала выбери режим

**Новое дело → гипотеза (по умолчанию).** Открой
[автономную методику](references/universal-argument-workflow.md) и применимые
[универсальные операции](references/universal-methods.json). Достаточны
предоставленные материалы нового дела; исходный корпус, индекс и поиск
будущего постановления не нужны. Выдели нормативный механизм, сильнейшее
возражение и факт, меняющий вывод. Неподтверждённое обозначай условно;
не требуй известного аналога и не подгоняй дело под прежние 12 карточек.
Для необязательной буквальной проверки связей используй `scripts/check_argument.py`.
Когда нужно уточнить недостающую посылку, проверить чувствительность к фактам,
сравнить варианты или проследить изменение довода по актам, открой
[проверку рассуждения и формулировок](references/reasoning-lab-workflow.md).
Она работает по материалам нового дела без исследовательского корпуса.

**Аналогия или цитируемая позиция.** Если нужно именно сослаться на реальный
акт, действует маршрут проверки источника ниже. Его требования к официальной
практике не являются предварительным условием автономной методической
гипотезы, но обязательны перед приписыванием суду конкретного тезиса.

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

## Порядок работы с аналогиями и источниками

1. Получи нейтральный профиль из `ksrf-explore-arguments`: норма, судебный смысл, механизм, вред, стадия, предполагаемый remedy и неизвестные звенья.
2. Сформулируй несколько поисковых представлений:
   - точная норма и системная связка;
   - механизм вреда;
   - право/институциональная гарантия;
   - доказательственный носитель;
   - remedy;
   - лучший контраргумент.
3. Используй `references/pattern-matrix.md`, `references/constitutional-graph.md`, hearing materials, `references/external-ks-complaint-webinar-methods.md` и ручной маршрут поиска позиций как карты кандидатов. Не обязан выбирать ни одного семейства. Вебинарный материал используй только как профессиональный checklist и red-team слой, а не как официальный источник позиции КС РФ.
4. Для каждого кандидата открой `references/decision-index.md` и официальный акт. Проверь:
   - что позиция принадлежит КС РФ, а не стороне;
   - норму, редакцию и временной контекст;
   - mechanism/harm/remedy;
   - отрицательную или сохраняющую формулу;
   - последующее изменение регулирования.
5. Запиши candidate finding по контракту `../ksrf-explore-arguments/references/artifact-contracts.md` с relation `supports`, `weakens`, `distinguishes` или `blocks`.
6. Ищи минимум один контрпример или более узкую позицию для сильной аналогии. Лексическое, векторное или графовое сходство не доказывает переносимость.
   При работе с реальными жалобами используй [дополнительные проверки переноса](references/additional-complaint-boundaries.md): сравни самостоятельные основания отказа, круг участников, норму и требуемое последствие; заимствуй метод постановки вопроса, а не факты или готовый вывод другого дела.
7. Если гипотезе нужна доктринальная методика, сначала используй встроенные `references/constitutional-methodology-verified-cards.md` и `references/constitutional-methodology-reference-only-corpus.md` в пределах их статуса и guardrails. Открывай исходную работу только для прямой цитаты, атрибуции нового тезиса или выхода за пределы встроенной карточки. Если работа недоступна, поставь `source_unavailable`: методическую карточку можно использовать как внутренний вопрос или red-team ход, но нельзя приписывать автору неподтверждённую формулу. Для критики позиции высшего суда проверь доктринальную память, системные связи, право/привилегию и усмотрение/доказываемый факт. Когда нужно воспроизводимо разобрать мотивировку или иностранный пример, используй `references/comparative-argument-coding.md`: код типа не определяет юридический вес, а иностранный материал остаётся `ResearchFinding` до отдельного российского якоря. Не вставляй фамилию ради усиления риторики.
   Если срабатывает Lawinfo-триггер, примени соответствующие LI-M карточки. Для каждого существенного довода проведи текстовую, интенциональную, consistency- и pragmatic-атаку; у семейств нет заранее заданной иерархии. При неопределённости отдели устойчиво конкурирующие подходы от единичной судебной ошибки; при языке ценностей или достоинства потребуй защищаемое благо, носителя, конкурирующую гарантию, конкретный вред и remedy.
   Для построения и атаки конкретного российского конституционного довода используй `references/constitutional-argument-architecture.md`: отдели главный тезис, прескриптивный/дескриптивный/оценочный уровни, поверхность атаки, competence и consequences gates. Научная модель не заменяет официальный якорь и не устанавливает вес типа аргумента.
   Если спор касается уровня абстракции, правила и его основания, holding/analogy либо цели толкования, открой `references/legal-reasoning-model-branches.md`: запускай конкурирующие модели параллельно и сохраняй `model_conflict`, не выбирая школу голосованием. Для воспроизводимой реконструкции ratio, силы прецедента, различения и defeasible argument graph дополнительно используй `references/precedent-analogy-and-justification.md`; сходство, найденное retrieval, не является relevance rule. Для иностранного института или довода заполни `references/institutional-discourse-and-comparative-transfer.md`, а при вопросах доступа, предмета жалобы, взаимодействия институтов или эффекта решения — `references/constitutional-institutions-access-and-remedy.md`; сходство названия или функции не закрывает contextual transfer и российский competence gate.
8. Передай findings обратно в argument ledger. Если практика высших судов исследуется через CasusLegal, маршрутизируй проверенные кандидаты через `ksrf-practice-authority-builder`: сохрани тот же relation, добавь authority role, source status, transfer limit и adverse pass. Не собирай обязательный пакет `основной + усиливающий + сохраняющий + remedy`, если структура дела требует иного портфеля.

## От нижестоящего акта к переносимому доводу

Когда задача начинается с текста дела, сначала используй автономный режим
выше. [Приёмы контролируемого переноса](references/transfer-methods.md) и
[их условия](references/transfer-methods.json) — необязательные специализации:
выдели механизм, необходимые посылки, опровергающие случаи и самостоятельные
основания отказа. Это автономная методика постановки вопроса, а не набор
ответов по исходам дел. При необходимости проверь полноту доказательных
условий через `scripts/check_transfer.py`; результат candidate не доказывает
истинность посылок или готовность жалобы. Новая evaluator-derived методика
от 2026-09-05 не допускается в исторический EVAL и не имеет обратной даты.

## Семейства как поисковые seeds

Текущий реестр включает practice split, certainty, constitutional meaning, proportionality, balance, effective remedy, procedural guarantees, equality, expectations, retroactivity, non-mechanical application, liability fairness, compensation, positive obligations, competence, legislative gaps, good faith, dignity, international standards и execution.

Список не закрыт. Новая гипотеза допустима, если она опирается на проверенные источники и проходит hard gates/critic review. Бремя доказывания, причинность, статистика, expert и amicus materials могут быть самостоятельным направлением исследования механизма, даже если в финальном аргументе работают как доказательственный слой.

## Превращение приёма в проверяемый абзац

Используй [карточку довода и предлагаемую редакцию](../ksrf-complaint-cycle/references/complaint-writing-loop.md): тезис, точный фрагмент основания, применимость, сильнейшее возражение, ответ и ограниченный вывод. Объясняй отличие упоминания, применения и причинной роли нормы. Карточка с совпавшей цитатой не подтверждает юридический вывод; машинные пробелы и незаполненные основания сохраняются для проверки.

## Справочники

- `references/pattern-matrix.md` и `references/decision-index.md` — candidate map и акты для проверки.
- `references/argument-techniques-from-decisions.md`, `references/hearing-derived-argument-patterns.md`, `references/hearing-constitutional-justifications.md`, `references/hearing-argument-techniques.md` — эвристики, вопросы и stress-tests, не обязательные схемы.
- `references/external-ks-complaint-webinar-methods.md` — профессиональная методика из вебинара о жалобе в КС РФ: нормативный барьер, четыре дефекта, неединичность практики, ранняя фиксация нормы, ходатайство о запросе суда, ответ на возврат Секретариата и red-team системных последствий; не официальный источник права.
- `references/evidence-maps.md`, `references/source-proof-impact-patterns.md`, `references/counterargument-playbook.md` — проверка материала и adverse case.
- `references/language-formulas.md` и `references/argument-package-builder.md` — drafting options после выбора портфеля.
- `references/constitutional-graph.md` и `references/constitutional_graph.json` — навигация по связям нормы, вреда, права, теста и remedy; `references/position-retrieval-architecture.md` — ручной поиск, сопоставление, официальная проверка и adverse-pass без зависимости от проектной инфраструктуры.
- `../ksrf-complaint-cycle/references/offline-practice-core.md` — обязательный автономный baseline по маршруту, допустимости, drafting, filing и исполнению.
- `../ksrf-practice-authority-builder/SKILL.md` — превращение CasusLegal findings в проверяемый authority ledger и блоки аргумента.
- `../ksrf-complaint-cycle/references/strategic-complaint-design.md` — проверяемая архитектура стратегического решения, доказательственных слоёв, сравнительных групп, amicus и последствий; журнал источников пользователю не требуется.
- `references/constitutionalist-authority-corpus.md` и [`references/constitutionalist-authority-corpus.json`](references/constitutionalist-authority-corpus.json) — широкий корпус авторов и работ с маршрутами, статусом извлечения и предохранителями.
- `references/constitutional-methodology-verified-cards.md` — 19 source/legal и model-conflict-reviewed pre-promotion карточек широкой волны, их locators, пределы переноса, overlap-роль и нерешённые conflict-abstain условия; human conflict gate остаётся отдельным.
- `references/constitutional-methodology-reference-only-corpus.md` — остальные 84 source/legal-reviewed карточки с triggers, stop-условиями, контрпримером и российской правовой границей; только option generation и red-team, без изменения behavior.
- `references/constitutionalists-folder-methodology-deltas.md` — автономный разбор 24 PDF из папки «Конституционалисты»: три независимо аудированные `reference_only` дельты и карта 12 поглощённых находок без дублирования действующих методов. Открывай только при совпавшем исследовательском trigger; до отдельной current-law/conflict review, held-out evaluation и явного human approval справочник не меняет обязательный шаг, hard gate, stop condition, классификацию или output KSRF skills.
- [Сопоставление нормативного смысла](../ksrf-complaint-cycle/references/norm-meaning-continuity.md) — отдельная интеграция от 2026-09-05 только для `bondar-norm-meaning-continuity-07`: открывай, если применённая норма изменена, отменена, заменена, перенумерована либо изменился её судебный смысл. Исторические статусы двух других дельт и 103-карточного корпуса сохраняются; результат сравнения не решает допустимость.
- `references/comparative-argument-coding.md` — воспроизводимая кодировка структуры и типов доводов, раздельная оценка наличия/веса и function-first gate для иностранного материала.
- `references/constitutional-argument-architecture.md` — главный тезис, трёхуровневая трасса, четыре типа, attack ledger, институциональная компетентность и последствия по российской научной методике.
- `references/constitutional-review-methods.md` — выбор между переносом позиции, атакой правоприменительного смысла, сохраняющим истолкованием, соразмерностью и вспомогательным методом, когда совпал этот методический trigger.
- `references/legal-reasoning-model-branches.md` — правила/принципы, under-/over-inclusion, holding/analogy, лестница абстракции, purpose и hard-case branch set без выбора «правильной» школы.
- `references/institutional-discourse-and-comparative-transfer.md` — strongest-objection ledger и contextualized functionalism для иностранного материала; архитектурно-визуальные описания остаются `context_only`.
- `references/precedent-analogy-and-justification.md` — internal/external justification, эмпирический precedent questionnaire, competing analogy branches, universalization boundaries и defeasible graph с `model_conflict -> abstain`.
- `references/constitutional-institutions-access-and-remedy.md` — сравнительные matrices модели контроля, доступа, предмета жалобы, институционального ответа и фактического эффекта remedy; каждый российский вывод требует отдельного первичного якоря.
- `references/lawinfo-constitutional-methods-2023-2026.md` и `references/lawinfo_constitutional_method_cards.json` — 15 полнотекстовых российских методических карточек: субъективная заинтересованность, четыре семейства атак, определённость, пропорциональность, ценности, достоинство, anti-appeal, конфликт классификаций абсолютного права и пределы remedy; научная карточка не заменяет действующее право.
- `../ksrf-complaint-cycle/references/lawinfo-historical-complaint-procedure-2009-2024.md` — 38 исторических/вторичных статей как 13 bounded JH-M critic cards: нормативный предмет, screening/refusal, versioned exhaustion, роли доказательств, виды решений, private/public tracks, certainty, compensation/proportionality, force и execution; reference-only и без изменения behavior.
- `../ksrf-complaint-cycle/references/sko-complaint-methods-2017-2026.md` — полнотекстовые карточки двенадцати статей СКО и оставшийся разведочный lead из тех же номеров.

## Встроенный реестр и дополнительный поиск

Для анализа одного дела используй готовые справочники из этого набора. `references/constitutionalist-authority-corpus.md` помогает выбрать тематический маршрут, а `references/constitutionalist-authority-corpus.json` показывает работы, алиасы и статус проверки записи.

Реестр — только карта поиска. Перед цитированием открой первичную публикацию, проверь автора, тезис и точную страницу или раздел. Если нужного материала в реестре нет, зафиксируй пробел и продолжи обычный поиск: отсутствие записи не доказывает отсутствие позиции. Пересборка реестра не входит в работу с конкретным делом.

## Вывод автономного режима

Дай условную узкую формулировку проблемы и цепочку «норма / смысл → механизм
вреда → конституционное основание», сильнейшее возражение, решающий факт и
изменение вывода при его обратном значении. Отдели установленное текстом от
предположений и недостающих доказательств; предложи ограниченное последствие.
Если нормативная связь не установлена, прямо скажи об этом. Не выдумывай
официальную позицию и не требуй найденного аналога, чтобы выполнить этот режим.

## Вывод режима аналогий

Для каждого кандидата:

- `Паттерн или приём-кандидат`;
- `Официальный источник и locator`;
- `verification_status` и `relation` по контракту `ResearchFinding`;
- `Что совпадает` и `Что различается`;
- `Предел переноса`;
- `Неблагоприятный результат или риск отказа`;
- `Происхождение и охват поиска`, включая запросы, дату и пробелы;
- `Нужная проверка`;
- `Возможный вариант формулировки или способа защиты`.

Отдельно перечисли `no close analogy found`, если это честный результат. Не превращай его в отрицательное юридическое заключение.
