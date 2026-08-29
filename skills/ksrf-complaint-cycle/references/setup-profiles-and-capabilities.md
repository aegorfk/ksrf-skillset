# Профили сетапа и capability doctor

## Принцип

Сетап показывает операционные возможности, а не перспективу жалобы. Никакой профиль не превращает юридический `unknown` в `pass`.

При состоянии `skills_only` сначала покажи все три профиля. Если пользователь ещё не выбрал профиль, назови `basic` рекомендуемым безопасным default и проведи его диагностику, но не скрывай существование `research` и `expert`. Нельзя объявлять environment готовым по общему описанию: опирайся на текущий machine-readable doctor report.

## `basic`

Минимальный локальный путь:

- Python и проверенный KSRF skillset;
- локальное чтение PDF/DOCX/изображений;
- OCR для сканов;
- Chrome/Chromium и Playwright для ручной/визуальной проверки;
- локальный matter workspace;
- прямой официальный поиск и ручной импорт;
- python-docx, LibreOffice/soffice, pypdf, pdftoppm и Pillow для реального filing pack.

Отсутствие Casus Legal, Firecrawl, ГАРАНТ, HUDOC, Qdrant, Neo4j, Langfuse или DeepEval не блокирует первичный local-basic анализ.

## `research`

Включает `basic` и необязательные расширения:

- Casus Legal либо иной discovery практики;
- Firecrawl как транспорт/поисковая зацепка, но не official authority;
- ГАРАНТ Коннект либо иной provider истории редакций как enrichment;
- локальный HUDOC и официальная проверка через HUDOC;
- полнотекстовый поиск, Qdrant и/или Neo4j как воспроизводимые проекции;
- официальные коллекторы КС РФ, pravo.gov.ru, судов общей юрисдикции, ВС РФ и релевантных банков.

## `expert`

Включает `research` и:

- Langfuse для trace;
- DeepEval и versioned rubric;
- outcome-blind input-only benchmark;
- независимый clean-context reviewer;
- consent-controlled private corpus;
- именованный human reviewer для promotion и release.

## Статусы проверки

- `ready` — capability доказан текущим probe.
- `degraded` — работает частично; указан предел.
- `blocked` — обязательная capability профиля не работает.
- `not_configured` — конфигурации нет.
- `unavailable` — bounded access check не удался.
- `interactive_required` — нужен браузер/ручной шаг, в том числе CAPTCHA.
- `unknown` — доказательств недостаточно.

Никогда не называй `unavailable` или `interactive_required` результатом `not_found`.

## Дополнительные инструменты по capability, а не по бренду

- История редакций: официальный amendment chain + optional provider comparison.
- OCR: OCRmyPDF/Tesseract или эквивалентный локальный стек.
- Извлечение сложных документов: Docling как optional parser; raw bytes остаются источником.
- PDF QA: LibreOffice, pypdf, pdftoppm; qpdf/veraPDF могут усиливать техническую проверку.
- Наблюдаемость/eval: Langfuse + DeepEval либо воспроизводимый эквивалент.
- Retrieval: FTS как baseline; Qdrant/Neo4j только rebuildable discovery projection.

Doctor не устанавливает эти компоненты автоматически, не создаёт аккаунты и не включает connector без прямого согласия.
