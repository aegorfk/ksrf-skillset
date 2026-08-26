# Локальный корпус HUDOC: порядок использования

## Что считать источником

Локальный TXT/JSONL — воспроизводимый поисковый слой над публичным PDF HUDOC, а не новый официальный акт. Для финального finding сохраняй официальный `itemid`, HUDOC URL, SHA-256 PDF, язык, тип документа и точный locator. Если вывод важен для жалобы, сверяй citation window с официальным PDF либо с TXT, чей SHA и pipeline version совпадают с processing registry.

Не смешивай:

- `judgment`, `decision`, `advisory_opinion`, `execution_resolution`;
- `communicated_case`, где опубликованы изложение и вопросы, но нет итогового решения;
- `summary` и press material, которые помогают искать, но не заменяют мотивировку;
- `applicant_submission`, `government_submission`, `third_party_submission`, `court_facts`, `court_reasoning`, `court_outcome` и `separate_opinion`.

Оригинальная жалоба обычно не опубликована в HUDOC. Воспроизведённые в акте доводы заявителя не называй полным текстом complaint.

## Стабильные слои

При стандартной локальной установке корень архива задаётся отдельно от skill. Используй:

- `metadata/corpus_processing.sqlite3` — canonical matter/document/variant, checkpoint, QA и verified findings;
- `text/<year>/<itemid>.txt` — UTF-8, границы страниц отмечены form-feed;
- `pages/<year>/<itemid>.jsonl` — страницы/абзацы, source roles, offsets и extraction provenance;
- `analysis/<year>/<itemid>.json` — только extractive candidates;
- `research/v1/` — отдельная candidate-only проекция; для нового прохода допускается только `hudoc-research-extractive-v6` с совпадающими source/artifact SHA, а v5 и записи прежних research versions остаются stale provenance-only и не участвуют в promotion;
- `findings/<year>/<finding_id>.json` — вручную проверенные findings;
- `metadata/corpus_progress.json` и `metadata/hudoc_corpus_processing.log` — прогресс и журнал.

Во время активного Airflow batch проверяй состояние только штатной командой `status` или по атомарному `corpus_progress.json`. Не открывай processing SQLite напрямую с macOS одновременно с контейнером: bind-mounted SQLite не является межхостовым status API.

Статусы текста:

- `ready` — автоматические проверки пройдены; всё равно проверяй locator для существенного вывода;
- `qa_required` — обычно OCR: не используй для правового тезиса до языковой/визуальной проверки;
- `quarantine` — не используй до устранения причины и повторной QA;
- `pending`, `processing`, `retry` — постоянный текст ещё не готов.

## Promotion gate

Работай по цепочке:

1. `candidate`: эвристически найденное окно; не доказанный тезис.
2. `verified_case_finding`: человек сверил itemid, PDF/TXT SHA, роль источника, страницу/абзац, тезис и ограничения.
3. `cross_case_reusable`: один и тот же приём подтверждён минимум в двух независимых matters. Единичный акт остаётся только `case_example_only` и не может получить reusable status.
4. `skill_update_approved`: cross-case gate пройден, adverse search документирован, российский anchor и transfer limits заполнены, человек одобрил перенос.

Перед promotion обязательно заполни:

- российский официальный конституционный или нормативный якорь, который ещё требуется;
- relation к конкретной KSRF hypothesis;
- factual/institutional differences;
- temporal jurisdiction и текущий эффект для дел против России;
- transfer limit;
- adverse review: найденное adverse authority либо честный `checked_none_found` с областью поиска.

Проверяй в finding как минимум `verification_status`, `lifecycle_stage`, `russian_anchor_status` и `drafting_reuse_status`. Значения `not_verified` или `blocked_missing_russian_anchor` разрешают хранить проверенный source finding, но запрещают выдавать его как drafting-ready pattern или менять substantive skill rule. Даже технически допустимая запись не заменяет юридическую и человеческую проверку. Case-specific факты не превращай в общий приём, а разные приёмы не объединяй только ради числа источников.

Исключение из Russian-anchor gate допускается только для method-only записи при одновременных `authority_status=non_authority`, `reuse_target=research_checklist_only` и `substantive_rule_changed=false`. Она всё равно требует human review, independent matters, exact public-act reproduction, court treatment и adverse/currentness/temporal/transfer review. Во всех остальных случаях российский якорь обязателен; отсутствие любого из трёх флагов блокирует reuse.

## Stop rules

Остановись и верни `candidate`/`qa_required`, если locator не находится, роль источника сомнительна, OCR не проверен или SHA расходится. Для substantive Court-authority reuse верни `blocked`, если нет независимого cross-case подтверждения, российского якоря, adverse review, transfer limit или human approval. Method-only исключение ограничено точным тройным контрактом выше и никогда не отменяет human approval. При конфликте ENG/FRE/перевода сохрани оба варианта и не синтезируй уверенный тезис до ручного разрешения.
