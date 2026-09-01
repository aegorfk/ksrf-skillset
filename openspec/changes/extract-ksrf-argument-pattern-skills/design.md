# Дизайн

## Проход по корпусу

Проход по корпусу намеренно сделан детерминированным и локальным:

- источник: `ТЗ/Постановления КС РФ`;
- скрипт сопровождения репозитория: `tools/extract_ksrf_argument_patterns.py`;
- выход: `analysis_results/ksrf_argument_patterns`;
- извлечение текста из PDF: сначала PyPDF2, затем fallback на pdfplumber;
- порядок: от старых к новым по году и номеру постановления.

Первый проход использует семейства маркеров, а не LLM-классификацию. Это делает результат воспроизводимым и дешевым, но все равно дает корпусную карту для последующей человеческой и юридической проверки.

## Форма скилла

Изначально используется один основной скилл:

- `ksrf-argument-patterns`

Это сохраняет workflow цельным, пока таксономия еще обсуждается. Справочники отделены, поэтому позже скилл можно разбить на более узкие, например:

- practice-split-finder;
- proportionality-builder;
- effective-remedy-checker;
- constitutional-meaning-drafter.

## Реестр паттернов

Текущий реестр содержит 20 семейств:

- practice-split;
- legal-certainty;
- constitutional-meaning;
- proportionality;
- interest-balance;
- effective-remedy;
- procedural-guarantees;
- equality-differentiation;
- legitimate-expectations;
- retroactivity;
- non-mechanical-application;
- liability-fairness;
- property-compensation;
- social-state-positive-obligation;
- federalism-competence;
- legislative-gap;
- good-faith-abuse;
- constitutional-identity-human-dignity;
- international-standards;
- reconsideration-execution.

## Направление автоматизации

Каждый паттерн в итоге должен давать инструмент поддержки дела, а не только инструкцию для текста. Примеры:

- поиск разнобоя нижестоящей практики для `practice-split`;
- детектор неопределенности нормы для `legal-certainty`;
- проверка проигнорированных доводов для `effective-remedy` и `procedural-guarantees`;
- проверка таймлайна для `legitimate-expectations` и `retroactivity`;
- проверка индивидуализации для `non-mechanical-application` и `liability-fairness`.

## Слой обогащения

Слой обогащения превращает реестр паттернов в инфраструктуру подготовки текста:

- пакеты аргументов: комбинации основного, усиливающего, сохраняющего и remedial-паттерна;
- контраргументы Секретариата: предсказуемые возражения о допустимости и более безопасные запасные рамки;
- доказательственные карты: необходимые факты, документы, проверки судебных актов, опровергающие обстоятельства и automation hooks по каждому паттерну;
- формулы языка: переиспользуемые формулы требований и конституционно-правового смысла в стиле КС РФ, извлеченные из корпуса детерминированными regex-маркерами;
- конституционный граф: переносимый JSON/Markdown-граф, связывающий паттерны, статьи Конституции, типы норм, типы вреда, постановления, доказательственные карты, automation hooks и семейства формул.

Первая реализация использует обычные JSON и Markdown, а не внешнюю графовую базу. Это сохраняет систему локальной, проверяемой и удобной для последующего импорта в Neo4j, SQLite, NetworkX или другой графовый слой.
