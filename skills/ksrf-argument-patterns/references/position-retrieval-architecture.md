# Retrieval похожих позиций КС РФ

Этот справочник описывает целевую архитектуру поиска похожих правовых позиций КС РФ для новых жалоб. Он привязан к проектному OpenSpec change `build-ksrf-position-retrieval`.

## Стек

- Qdrant: векторный поиск по смысловым чанкам Постановлений КС РФ.
- Neo4j: графовая структура нормы, конституционных статей, паттернов, приемов, тестов, вреда и remedy.
- Локальные embeddings: Sentence Transformers-compatible bi-encoder или другой локальный backend с русским языком.
- Локальный reranker: Sentence Transformers-compatible CrossEncoder или другой локальный cross-encoder.
- Лексический поиск: точные формулы КС РФ, номера постановлений, статьи Конституции, устойчивые выражения.

Внешние inference-сервисы по умолчанию не используются.

Если Docker/Qdrant server временно недоступен, для локального smoke и небольшого индекса можно использовать persistent local mode `qdrant-client` через `KSRF_QDRANT_PATH=.ksrf-retrieval/qdrant-local`. Это не заменяет серверный Qdrant для длительной работы, но позволяет проверить полный цикл индексации и поиска без контейнера.

## Что индексировать

Не индексируй PDF целиком одним вектором. Делить постановление нужно на юридические чанки:

- `case_context`: факты и процессуальная история;
- `challenged_norm`: оспариваемая норма и контекст регулирования;
- `applicant_arguments`: доводы заявителя;
- `court_question`: вопрос перед КС РФ;
- `legal_position`: переносимая позиция КС РФ;
- `constitutional_test`: тест проверки;
- `constitutional_meaning`: выявленный или исключенный конституционно-правовой смысл;
- `remedy`: последствия, пересмотр, обязанность законодателя, временный порядок;
- `dissent_or_concurrence`: особые мнения, если они нужны и явно промаркированы.

Самые ценные чанки для поиска: `legal_position`, `constitutional_test`, `constitutional_meaning`, `remedy`.

## Оперативные источники обнаружения

Для новых актов и тематических подборок можно использовать публичные каналы и юридические медиа как discovery layer, но не как финальную правовую опору. После выгрузки `@ksrf_ru` (`ТЗ/Каналы/ksrf_ru_posts.txt`, 3180 публичных постов за 2020-08-05 - 2026-06-10) добавлен такой порядок:

- пост Telegram хранится как `discovery_source` с URL, датой, ID и текстом;
- из поста извлекаются номер акта, дата, тип акта, ссылки на официальный PDF/страницу КС РФ, краткая фабула, оспариваемая норма, outcome и remedy-маркеры;
- если пост ссылается только на медиа или экспертный комментарий, он не индексируется как `legal_position` до сверки с официальным текстом;
- посты о тематических сборниках правовых позиций отправляются в отдельную очередь: найти официальный сборник, скачать, распарсить список актов, связать с уже индексированными решениями;
- экспертные комментарии сохраняются как `commentary_context` и могут помогать объяснению пользователю, но не повышают юридический score кандидата без совпадения по официальному акту.

## Метаданные чанка

Минимальный payload для Qdrant и связки с Neo4j:

```json
{
  "chunk_id": "...",
  "decision_number": "14-П/1998",
  "decision_year": 1998,
  "section": "constitutional_test",
  "text": "...",
  "norms": ["..."],
  "constitution_articles": ["ст. 19", "ст. 46", "ст. 55"],
  "patterns": ["proportionality", "effective-remedy"],
  "techniques": ["measure-limitation", "saving-negative-formula"],
  "formulas": ["в той мере, в какой", "не предполагает"],
  "harm_types": ["чрезмерное бремя", "иллюзорная защита"],
  "remedy_types": ["constitutional-meaning", "reconsideration"],
  "graph_node_ids": ["..."]
}
```

## Граф нормы и Конституции

Для нового дела строй цепочку:

```text
оспариваемая норма
  -> буквальный смысл
  -> смысл, приданный судами
  -> последствие для заявителя
  -> затронутое право / принцип
  -> статья Конституции
  -> тест КС РФ
  -> конституционно-правовой смысл или предел неконституционности
  -> remedy
```

Эта цепочка нужна и для текста жалобы, и для retrieval-запроса.

## Балансирование норм

Балансируй не “норма против нормы”, а интересы:

```text
норма A -> защищает интерес A -> ограничивает право B
норма B -> защищает интерес B -> ограничивает право A
конституционный баланс возможен только при гарантиях
```

Проверки баланса:

- легитимная цель;
- пригодность меры;
- необходимость;
- тяжесть бремени;
- менее обременительные альтернативы;
- процессуальные гарантии;
- компенсация или смягчение последствий;
- сохранение существа права.

## Пайплайн поиска

1. Разбери новое дело в query profile: норма, смысл судов, вред, статьи Конституции, паттерны, приемы, remedy.
2. Запусти лексический поиск по точным формулам и статьям.
3. Запусти Qdrant vector search по чанкам.
4. Расширь кандидатов в Neo4j по статьям, паттернам, приемам, вреду, remedy и балансировочным путям.
5. Объедини и убери дубли.
6. Переранжируй локальным CrossEncoder.
7. Покажи пользователю не только score, а юридическое объяснение.

## Локальная реализация в `ks_parser_lower_court_marker`

Если работаешь в проекте `/Users/aegorfk/Documents/ks_parser_lower_court_marker`, используй уже созданный контур:

```bash
docker compose -f docker-compose.ksrf-retrieval.yml up -d
python3 scripts/index_ksrf_position_retrieval.py --recreate-qdrant --batch-size 32
python3 scripts/query_ksrf_position_retrieval.py "обратная сила ухудшила положение и лишила судебной защиты" --top-k 5
```

Для LLM-semantic разбиения через локальный Ollama/OpenAI-compatible backend используй отдельную коллекцию:

```bash
ollama serve
ollama pull qwen2.5:7b
python3 scripts/index_ksrf_position_retrieval.py \
  --chunking semantic-llm \
  --semantic-model qwen2.5:7b \
  --incremental-upload \
  --qdrant-collection ksrf_position_semantic_chunks \
  --recreate-qdrant \
  --batch-size 8 \
  --semantic-cache-dir .ksrf-retrieval/semantic-cache \
  --semantic-progress-file .ksrf-retrieval/semantic-index-progress.json
```

Если semantic backend не поднят, не подменяй silently semantic-index deterministic-индексом: прямо укажи, что semantic collection ещё не построена.

Фоновый прогон должен быть resumable: LLM-разметка хранится по постановлениям в `.ksrf-retrieval/semantic-cache`, а последний загруженный документ фиксируется в `.ksrf-retrieval/semantic-index-progress.json`. Для длительного локального запуска удобно держать Ollama и индексатор в detached `screen`; текущий heartbeat смотри через `tail -f .ksrf-retrieval/semantic-index.log`.

Практический дефолт splitter-а на Mac 16 GB: `qwen2.5:7b`. `qwen3:4b` помещается в память, но thinking-режим может быть слишком вязким для массового JSON-splitting; если используешь Qwen3, обязательно проверяй smoke на `--limit 1`.

Сервисы и дефолты:

- Qdrant: `http://localhost:6333`, коллекция `ksrf_position_chunks`.
- Qdrant semantic collection: `ksrf_position_semantic_chunks`.
- Neo4j Browser: `http://localhost:7474`, Bolt `bolt://localhost:7687`, пользователь `neo4j`, пароль из `.env.example`.
- Embedding model: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`.
- Reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`.
- Локальный Langfuse для golden/eval: `http://localhost:3001`, проект `KSRF Retrieval Eval`.

CLI-поиск объединяет Qdrant, локальный lexical leg по формулам КС РФ, Neo4j-контекст и локальный reranker. Для быстрой диагностики можно отключить reranker через `--no-rerank`, но для реального подбора позиций оставляй reranker включенным.

## MCP-доступ к базам

В глобальном Codex config должны быть подключены stdio MCP:

- `ksrf-qdrant`: `tools/mcp/ksrf_qdrant_server.py`;
- `ksrf-neo4j`: `tools/mcp/ksrf_neo4j_server.py`.

Используй MCP-инструменты так:

- `qdrant_status` - проверить коллекции и counts;
- `qdrant_collection_info` - проверить vector store metadata;
- `qdrant_sample_points` - посмотреть payload по постановлению или секции;
- `qdrant_search_text` - найти похожие chunks по тексту;
- `neo4j_status` - проверить labels, relationship types и counts;
- `neo4j_decision_graph` - получить граф по номеру постановления;
- `neo4j_readonly_cypher` - выполнить read-only Cypher.

Для визуального просмотра:

- Qdrant Dashboard: `http://localhost:6333/dashboard`, коллекция `ksrf_position_chunks` или `ksrf_position_semantic_chunks`;
- Neo4j Browser: `http://localhost:7474`, запрос `MATCH p=(d:KSRFDecision {number: "24-П/2017"})-[:HAS_CHUNK]->(c:KSRFPositionChunk)-[r]->(n) RETURN p LIMIT 150`.
- 2D-карта vectors: `python3 scripts/export_ksrf_vector_map.py --collection ksrf_position_semantic_chunks --output analysis_results/ksrf_semantic_vector_map.html`.

## Оценка retrieval

Golden dataset хранится в `evals/ksrf_retrieval_golden.jsonl`. Запускай:

```bash
LANGFUSE_HOST=http://localhost:3001 \
LANGFUSE_PUBLIC_KEY=pk-lf-ksrf-local \
LANGFUSE_SECRET_KEY=sk-lf-ksrf-local \
python3 scripts/evaluate_ksrf_retrieval.py --top-k 10
```

Минимальные метрики: hit rate at K и MRR. До использования результата для жалобы вручную проверь expected decisions и цитаты. DeepEval/LLM-judge добавляется после ручной валидации golden dataset, иначе judge будет закреплять ошибки разметки.

Стартовый smoke-baseline deterministic collection (`--no-rerank --top-k 5 --candidate-limit 20`) дал `hit@5 = 0.4`, `MRR = 0.4` на 5 кейсах. Это диагностическая точка, а не целевая метрика: пополняй golden hard-cases и сравнивай deterministic vs semantic collection.

## Enrichment-слой корпуса

Для оптимальной работы по жалобам поверх chunks строится отдельный слой:

```bash
python3 scripts/build_ksrf_corpus_enrichment.py
```

Артефакты:

- `analysis_results/ksrf_argument_cards.jsonl` - карточки переносимой позиции: `source_anchor`, `quote_locator`, переносимое правило, constitutional chain, паттерны, приемы, формулы, вред, remedy и кандидаты цитат;
- `analysis_results/ksrf_hard_negatives.jsonl` - пары похожих, но потенциально непереносимых карточек для ручной разметки и retrieval-eval;
- `analysis_results/ksrf_corpus_quality_report.json` - отчет по покрытию корпуса: chunks, decisions, cards, hard negatives, section distribution, missing source anchors, missing constitutional articles, long chunks.

Текущий полный прогон после bounded source splitting:

- chunks: `21692`;
- argument cards: `19433`;
- hard-negative candidates: `500`;
- separate opinion chunks: `304`;
- chunks over 3500 chars: `0`;
- missing source anchors: `0`;
- missing local constitutional articles: `0.8481`;
- missing decision-level constitutional articles: `0.0812`.

Используй argument card как drafting-aid, а не как готовую цитату. Перед финальным текстом жалобы найди `quote_locator` в text-файле постановления и проверь полный контекст. Если hard-negative pair похож на выбранный authority, явно объясни, почему выбранная позиция переносима, а соседняя похожая позиция нет.

Для уже построенной deterministic Qdrant collection можно без переэмбеддинга дозаполнить payload:

```bash
python3 scripts/backfill_ksrf_qdrant_payload_anchors.py --collection ksrf_position_chunks
python3 scripts/backfill_ksrf_qdrant_decision_context.py --collection ksrf_position_chunks
```

Первый backfill добавляет `source_anchor` и `quote_locator`; второй добавляет `decision_constitution_articles`. Для новых полных индексов эти поля пишутся сразу.

## Профиль новой жалобы

Перед retrieval запускай:

```bash
python3 scripts/profile_ksrf_complaint_query.py "описание проблемы и применения нормы судами"
```

Профиль должен включать: норму, статьи Конституции, вред, паттерны, приемы, графовую формулу, retrieval query и перечень недостающих материалов.

Retrieval CLI показывает argument card при точном совпадении `chunk_id`:

```bash
python3 scripts/query_ksrf_position_retrieval.py "поворот к худшему правовая определенность судебная защита" --top-k 5
```

В выводе проверяй `Якорь источника`, `Карточка аргумента`, `Конституционная цепочка` и `Пределы`.

## Формат ответа по похожей позиции

```markdown
**Позиция:** ...
**Почему похожа:** ...
**Графовая связь:** норма -> вред -> статья Конституции -> паттерн -> remedy
**Что переносимо:** ...
**Что не переносимо:** ...
**Какие цитаты проверить:** ...
**Как использовать в жалобе:** ...
```

## Правило осторожности

Векторная близость сама по себе не делает постановление релевантной опорой. Сильный кандидат должен совпадать хотя бы по нескольким структурным признакам: статья Конституции, тип вреда, паттерн, прием, тест, remedy или балансировочная конфигурация.
