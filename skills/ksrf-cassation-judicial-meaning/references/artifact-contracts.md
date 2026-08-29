# Контракт исследовательского запуска, версия 1.0

## Содержание

- [1. Артефакты дела и поиска](#1-артефакты-дела-и-поиска)
- [2. Артефакты корпуса](#2-артефакты-корпуса)
- [3. Applicant-relative workbench](#3-applicant-relative-workbench)
- [4. Approval, report и handoff](#4-approval-report-и-handoff)
- [5. Временной контракт](#5-временной-контракт)
- [6. Стабильные идентификаторы и неизменяемость](#6-стабильные-идентификаторы-и-неизменяемость)
- [7. Handoff envelope](#7-handoff-envelope)


Все изменяемые данные конкретного дела лежат в выбранном пользователем workspace, а не в каталоге установленного скилла. Повторно используемый публичный кеш имеет отдельный root и никогда не принимает applicant-private artifacts.

## 1. Артефакты дела и поиска

| Артефакт | Назначение | Gate |
|---|---|---|
| `intake/applicant-private.jsonl` | Локальный извлечённый текст и private provenance актов заявителя | fingerprint |
| `intake/applicant-manifest.jsonl` | Публично безопасные хеши, роли и extraction status | fingerprint |
| `applicant-chain.json` | Стадии, факты, нормы, speakers, исходы и неясности | plan freeze |
| `case-fingerprint.json` | Текущая ревизия нейтрального вопроса, норм и признаков | case-relative review |
| `casework/fingerprints/fingerprint-vN.json` | Неизменяемая история fingerprint | stale audit |
| `casework-dependencies.json` | Missing tasks и состояние зависимых applicant-relative артефактов | comparability |
| `query-suggestions.jsonl` | `suggested_unconfirmed` запросы с reason codes и provenance | query review |
| `query-decisions.jsonl` | Принятые человеком `accepted_pre_freeze` запросы | plan freeze |
| `supplemental-queries.jsonl` | Раскрытые `post_freeze_supplemental`, не меняющие исходный знаменатель | evidence review |
| `research-plan.json` | Редактируемый шаблон Evidence Acquisition Plan | plan freeze |
| `plans/plan-vN.json` | Неизменяемый план и SHA-256 | collection |
| `research-questions.jsonl` | Только neutral questions/hypotheses under test | collection |
| `queries.jsonl` | Исполняемые обычные, adverse и supplemental дорожки | collection |
| `run.json` | Текущий `run_id`, `plan_sha256` и runtime binding | collection |

`intake` создаёт `applicant-chain.json` с `run_id=null`: исследовательский запуск ещё не существует. Первый `collect` создаёт `run_id` и атомарно привязывает chain к нему. `case prepare` до intake запрещён.

Принятые до freeze query suggestions копируются в замораживаемый план и входят в `plan_sha256`. После freeze новый поиск записывается как supplemental с `changes_original_denominator=false`; он не переопределяет совокупность задним числом.

## 2. Артефакты корпуса

| Артефакт | Назначение | Gate |
|---|---|---|
| `corpus.sqlite3` | Транзакционный источник collection state | после freeze |
| `exports/coverage.json` | Страницы, terminal states, denominator и пробелы по режиму/суду/дате | coverage review |
| `exports/sources.jsonl` | Official URLs, raw/text hashes и provenance | coding |
| `exports/case-chains.jsonl` | Независимые цепочки и merge/split review | analysis |
| `screening-candidates.jsonl` | Все кандидаты по замороженным дорожкам | coding |
| `coding-decisions.jsonl` | Полнотекстовые юридические коды, speaker, цитаты и решения об исключении | adverse review |
| `adverse-review.json` | Общий corpus adverse-pass | analysis |
| `analysis.json` | Независимые цепочки, временные матрицы, denominator scope и предел вывода | thesis review |
| `thesis-candidates.jsonl` | Только post-corpus кандидаты | thesis review |

Каждый screening candidate разрешается по паре `chain_id + document_id`: одобренная полнотекстовая позиция либо одобренное полнотекстовое исключение. Пока `screening_resolution_complete=false`, evidence review и `drafting_ready` блокируются.

Первый `analyze` создаёт measurements, пустой `thesis-candidates.jsonl` и шаблон общего `adverse-review.json`. Кандидаты появляются только после `review --decision evidence_reviewed` с завершёнными adverse/coverage review и повторного `analyze`.

## 3. Applicant-relative workbench

| Артефакт | Назначение | Gate |
|---|---|---|
| `position-cards.jsonl` | Полные одобренные карточки кассационных позиций | comparison |
| `comparability-matrix.jsonl` | Текущее сравнение каждой карточки с fingerprint | relation |
| `case-comparison.json` | Удобная копия последнего сравнения, не самостоятельный источник правды | relation |
| `applicant-position.json` | Проверенная классификация reading families со стороны заявителя | relation |
| `applicant-relations.jsonl` | `supports/adverse/distinguishes/neutral/unresolved` по каждой карточке | adverse |
| `review-queue.json` | Приоритет и все unresolved candidates без удаления | coding review |
| `case-adverse-review.json` | Четыре case-relative adverse buckets, query IDs, unresolved и claim effects | bridge |
| `normative-bridge.json` | Три звена, ordinary remedy, supporting/adverse cards и bounded wording | drafting ready |

Карточка позиции содержит полный `comparison_features[]`; текстовый label не заменяет структуру. Текущая строка comparison связывает:

- `fingerprint_sha256`;
- `applicant_features_sha256`;
- `candidate_features_sha256`;
- `position_card_sha256`;
- полученный из них и результата review `comparison_id`.

Relation дополнительно связывает `comparison_sha256` и `applicant_position_sha256`. Исправить карточку или fingerprint можно, но зависимая связь тогда перестаёт совпадать с текущим hash binding и не учитывается как approved. Новое review не должно маскировать факт stale-инвалидации.

Все состояния имеют значение: `matched`, `distinguishable`, `uncertain`; `approved`, `pending_human_review`; `supports`, `adverse`, `distinguishes`, `neutral`, `unresolved`; `stale=true/false`. Нельзя фильтровать незавершённые состояния из denominator или очереди только потому, что они не поддерживают тезис.

## 4. Approval, report и handoff

| Артефакт | Назначение |
|---|---|
| `human-decision.json` | Решение человека, привязанное к текущим plan/evidence hashes |
| `validation-report.json` | Состояние всех gates и хеши проверенного набора |
| `report/index.html` | Автономный локальный отчёт без внешних ресурсов |
| `report/manifest.json` | Hash binding отчёта к plan/evidence/fingerprint |
| `handoffs/*.json` | Content-bound envelope для соседнего скилла |
| `handoff-inbox.jsonl` | Атомарный идемпотентный ledger импортов |

Case-relative `drafting_ready` требует одновременно: готовый fingerprint; замороженный план; завершённые collection/coding/comparison/relation/adverse/coverage/analysis gates; валидный нормативный мост; human approval; текущие approval/validation hashes; кандидат, не превышающий `maximum_permitted_claim`.

Default report всегда выводит открытые route и historical gaps, pending task counts, stale artifacts и точный denominator scope. Он раскрывает только текущие reviewed comparison/relation как findings, но сохраняет общий denominator карточек, чтобы положительные позиции не выглядели всем корпусом.

## 5. Временной контракт

`temporal_strata` и `interpretive_events` в плане необязательны. Если они заданы, страты непрерывно и без пересечений покрывают период; событие связывает соседние страты, а `effective_date` совпадает с началом следующей и подтверждается официальной ссылкой. Поля входят в SHA-256 плана.

`analysis.json` сохраняет `reading_family_by_year`, `reading_family_by_stratum`, `interpretive_event_findings`, `temporal_unassigned_chain_ids`, `temporal_analysis_complete` и `denominator_scope`. Знаменатель ячейки — только `approved_independent_coded_chains`; нулевая страта остаётся видимой.

`emergent_reading_candidate` означает впервые наблюдаемую после события новую семью без смешанного постсобытийного массива. `mixed_post_event` означает совместное наблюдение прежней и новой семей. Пробел enumeration, пустая сторона, неназначенная дата или неодобренная сопоставимость дают `insufficient_temporal_evidence`, а не тезис о динамике.

## 6. Стабильные идентификаторы и неизменяемость

- `plan_id`/`plan_sha256`: SHA-256 канонического frozen JSON без volatile-полей.
- `fingerprint_sha256`: SHA-256 нейтрального issue, norm refs и нормализованных features.
- `source_id`: SHA-256 роли источника и канонического URL.
- `snapshot_id`: SHA-256 raw bytes.
- `document_id`: SHA-256 нормализованного текста, иначе raw bytes.
- `chain_id`: официальный `host + case_uid`; fallback — `host + case_id + delo_id + new`; неуверенная связь получает `needs_merge_split_review`.
- `coding_id`: SHA-256 chain/document, codebook version и revision.
- `comparison_id`: content-derived ID текущего fingerprint, карточки, признаков и review provenance.

Frozen plan, versioned fingerprint, raw snapshot, run pins, treatment review history и handoff не переписываются. Исправление создаёт новую версию или новую content-bound запись. Текущие реестры comparison/relation могут заменять строку по `position_card_id`, но gate принимает её только при совпадении всех сохранённых хешей.

## 7. Handoff envelope

Минимальные поля: `schema_version`, `handoff_id`, `created_at`, `source_skill`, `target_skill`, `run_id`, `plan_sha256`, `evidence_sha256`, `payload_type`, `payload`, `limitations`. Для reviewed payload также обязателен текущий fingerprint binding.

Типы:

- `unproven_research_questions` — только вопросы и ограничения, без findings или complaint wording;
- `approved_bounded_findings` — drafting-ready bounded findings, supporting IDs, явный adverse list и `maximum_permitted_claim`;
- `authority_cards` — проверенные карточки, reviewer, `review_state=approved` и максимум вывода.

Legacy `selected_authorities` допускается только при чтении старого envelope. Повторная передача того же `handoff_id` идемпотентна. Проверка возвращает `valid`, `stale`, `tampered` или `incompatible`; ошибка импорта не изменяет corpus, approval или inbox.
