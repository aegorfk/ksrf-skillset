# Контракт исследовательского запуска, версия 1.0

Все изменяемые данные лежат в выбранном пользователем workspace, а не в каталоге установленного скилла.

## Обязательные артефакты

| Артефакт | Назначение | До какого этапа обязателен |
|---|---|---|
| `intake/applicant-manifest.jsonl` | Хеши, роли и статус извлечения актов заявителя | question review |
| `applicant-chain.json` | Стадии, факты, нормы, speakers, исходы и неясности | plan freeze |
| `research-questions.jsonl` | Только нейтральные вопросы и hypotheses under test | plan freeze |
| `queries.jsonl` | Замороженные обычные и adverse поисковые дорожки | collection |
| `plans/plan-vN.json` | Неизменяемый Evidence Acquisition Plan и SHA-256 | collection |
| `run.json` | Текущий `run_id` и хеш замороженного плана | collection |
| `corpus.sqlite3` | Транзакционный источник состояния | всегда после freeze |
| `exports/coverage.json` | Страницы, статусы и пробелы по режиму/суду/дате | coverage review |
| `exports/sources.jsonl` | Официальные URL, raw/text hashes и provenance | coding |
| `exports/case-chains.jsonl` | Независимые цепочки и merge/split review | analysis |
| `coding-decisions.jsonl` | Полнотекстовые юридические коды и цитаты | adverse review |
| `adverse-review.json` | Дорожки, результаты и ограничения adverse-pass | analysis |
| `thesis-candidates.jsonl` | Только post-corpus кандидаты | thesis review |
| `human-decision.json` | Решение человека, привязанное к хешам | drafting ready |
| `validation-report.json` | Пройденные и непройденные gates | handoff |

`intake` создаёт `applicant-chain.json` с `run_id=null`, поскольку исследовательский запуск ещё не существует. При первом `collect` runtime создаёт `run_id`, записывает его в `run.json` и атомарно привязывает к нему `applicant-chain.json`.

Первый `analyze` создаёт `analysis.json`, пустой `thesis-candidates.jsonl` и заполняемый шаблон `adverse-review.json`. Кандидаты тезисов появляются только после команды `review --decision evidence_reviewed`, в которой человек подтвердил завершение adverse- и coverage-review, и повторного `analyze`.

## Стабильные идентификаторы

- `plan_id`: SHA-256 канонического JSON без volatile-полей.
- `source_id`: SHA-256 роли источника и канонического URL.
- `snapshot_id`: SHA-256 raw bytes.
- `document_id`: SHA-256 нормализованного текста, иначе raw bytes.
- `chain_id`: официальный `host + case_uid`; fallback — `host + case_id + delo_id + new`; неуверенная связь получает статус `needs_merge_split_review`.
- `coding_id`: SHA-256 chain/document, codebook version и revision.

Менять frozen plan на месте нельзя. Поправка создаёт `plan-vN+1`, сохраняет историю и делает зависимые анализ/approval `stale`.

## Handoff envelope

Минимальные поля: `schema_version`, `handoff_id`, `created_at`, `source_skill`, `target_skill`, `run_id`, `plan_sha256`, `evidence_sha256`, `payload_type`, `payload`, `limitations`. Повторная передача того же `handoff_id` идемпотентна. Ошибка передачи не изменяет corpus или approval.
