---
name: ksrf-argument-patterns
description: Находить, проверять и ограничивать перенос аргументативных аналогий из Постановлений и заседаний КС РФ. Используй как необязательную библиотеку гипотез, поисковых терминов, контрпримеров и формул, когда нужно проверить новую конституционно-правовую линию; не используй как закрытую типологию или обязательное обоснование жалобы.
---

# Паттерны аргументации КС РФ как исследовательская библиотека

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

Для доктринального и сравнительного поиска используй `references/constitutionalist-authority-corpus.md` как маршрут, а `constitutionalist-authority-corpus.json` как полный реестр авторов, работ, алиасов, тематических направлений и статусов готовности. Начинай с `method_integrated`, затем `full_text_available` и `triangulated_academic`. `academic_indexed` и `bibliographic_lead` требуют открытия самой работы; `discovery_only` — только поисковый lead, а не авторитет для жалобы.

## Порядок работы

1. Получи нейтральный профиль из `ksrf-explore-arguments`: норма, судебный смысл, механизм, вред, стадия, предполагаемый remedy и неизвестные звенья.
2. Сформулируй несколько поисковых представлений:
   - точная норма и системная связка;
   - механизм вреда;
   - право/институциональная гарантия;
   - доказательственный носитель;
   - remedy;
   - лучший контраргумент.
3. Используй `references/pattern-matrix.md`, `constitutional-graph.md`, hearing materials и retrieval architecture как карты кандидатов. Не обязан выбирать ни одного семейства.
4. Для каждого кандидата открой `references/decision-index.md` и официальный акт. Проверь:
   - что позиция принадлежит КС РФ, а не стороне;
   - норму, редакцию и временной контекст;
   - mechanism/harm/remedy;
   - отрицательную или сохраняющую формулу;
   - последующее изменение регулирования.
5. Запиши candidate finding по контракту `../ksrf-explore-arguments/references/artifact-contracts.md` с relation `supports`, `weakens`, `distinguishes` или `blocks`.
6. Ищи минимум один контрпример или более узкую позицию для сильной аналогии. Лексическое, векторное или графовое сходство не доказывает переносимость.
7. Если гипотезе нужна доктринальная методика, выбери в корпусе автора по маршруту, открой указанную работу и запиши точный тезис, locator, функцию, предел переноса и контраргумент. Не вставляй фамилию ради усиления риторики.
8. Передай findings обратно в argument ledger. Не собирай обязательный пакет `основной + усиливающий + сохраняющий + remedy`, если структура дела требует иного портфеля.

## Семейства как поисковые seeds

Текущий реестр включает practice split, certainty, constitutional meaning, proportionality, balance, effective remedy, procedural guarantees, equality, expectations, retroactivity, non-mechanical application, liability fairness, compensation, positive obligations, competence, legislative gaps, good faith, dignity, international standards и execution.

Список не закрыт. Новая гипотеза допустима, если она опирается на проверенные источники и проходит hard gates/critic review. Бремя доказывания, причинность, статистика, expert и amicus materials могут быть самостоятельным направлением исследования механизма, даже если в финальном аргументе работают как доказательственный слой.

## Справочники

- `references/pattern-matrix.md` и `decision-index.md` — candidate map и акты для проверки.
- `references/argument-techniques-from-decisions.md`, `hearing-derived-argument-patterns.md`, `hearing-constitutional-justifications.md`, `hearing-argument-techniques.md` — эвристики, вопросы и stress-tests, не обязательные схемы.
- `references/evidence-maps.md`, `source-proof-impact-patterns.md`, `counterargument-playbook.md` — проверка материала и adverse case.
- `references/language-formulas.md` и `argument-package-builder.md` — drafting options после выбора портфеля.
- `references/constitutional-graph.md`, `constitutional_graph.json`, `position-retrieval-architecture.md` — candidate generation и обход связей.
- `../ksrf-complaint-cycle/references/offline-practice-core.md` — обязательный автономный baseline по маршруту, допустимости, drafting, filing и исполнению.
- `references/complaint-methodology-sources.md` — provenance и журнал источников обновления; для runtime-работы не требуется.
- `references/constitutionalist-authority-corpus.md` и `constitutionalist-authority-corpus.json` — широкий корпус авторов и работ с маршрутами, статусом извлечения и предохранителями.

## Инструменты

Используй штатные scripts и доступные read-only Qdrant/Neo4j tools для inspection/retrieval. Перед retrieval по новой жалобе строй query profile и сверяй качество на golden/hard-negative наборах. Если semantic collection или исходный корпус отсутствуют, используй bundled references и автономное ядро, а отсутствие retrieval отметь только как предел поиска аналогий. Не запускай глобальное обогащение корпуса, если пользователю нужен анализ одного дела.

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
