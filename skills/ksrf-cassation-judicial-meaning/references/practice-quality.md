# Quality-слой анализа судебного смысла

Эти артефакты отвечают на разные вопросы и не сворачиваются в один score. `complete` означает завершённость заявленного ограниченного протокола, а не доказанность «хаоса», неработоспособности закона, неконституционности или готовности жалобы к подаче.

## Содержание

- [Движение смысла внутри цепочки](#движение-смысла-внутри-цепочки)
- [Профиль неопределённости](#профиль-неопределённости)
- [Надёжность кодирования](#надёжность-кодирования)
- [Предподачная актуальность](#предподачная-актуальность-producer--consumer)
- [Коды завершения](#коды-завершения-обязательных-проверок)
- [Связь с handoff](#связь-с-handoff)
- [Миграция прежних артефактов](#миграция-ранее-созданных-v1-артефактов)

## Движение смысла внутри цепочки

`chain-stage-observations.jsonl` хранит отдельные reviewed-наблюдения по каждой инстанции. Не передавай их в агрегатор, который выбирает одну карточку на независимую цепочку: межинстанционная траектория и межделовое сравнение — разные единицы анализа.

Обязательные различия:

- `source_stage` — где находится текст-доказательство;
- `position_actor_stage` — какому суду принадлежит позиция;
- `evidence_role` — `actor_primary_text` либо `later_court_report`;
- `treatment_of_prior` — `originates`, `expressly_adopts`, `follows`, `limits`, `rejects`, `does_not_reach`, `leaves_result_without_endorsing`, `unclear`;
- `outcome_materiality` и самостоятельные альтернативные основания;
- document hash, точная цитата/locator и provenance ручной проверки.

Оставление результата без изменения не означает принятия мотивировки нижестоящего суда. Пересказ более ранней позиции в кассационном акте остаётся `later_court_report`, если нет первичного текста соответствующего автора позиции.

## Профиль неопределённости

`practice-uncertainty-profile.json` содержит ровно девять независимых измерений:

1. `comparable_reading_plurality`;
2. `fact_sensitivity`;
3. `court_distribution`;
4. `temporal_distribution`;
5. `chain_endorsement`;
6. `outcome_materiality`;
7. `higher_authority_treatment`;
8. `coverage_limits`;
9. `coding_reliability`.

Каждое измерение хранит state, независимые chain IDs, evidence refs, unknowns, claim effect и limitations. Поля `score`, `overall_score`, `index` и их смысловые аналоги запрещены. Профиль описывает доказательственную картину; нормативный мост и human approval остаются отдельными воротами.

## Надёжность кодирования

### 1. Подготовь первичные входы штатной командой

После завершённых `screen` и одобренного человеком `code` создай новый каталог аудита:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
JM="$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py"
AUDIT_BUNDLE="./coding-audit-inputs"

python3 "$JM" quality coding-audit-prepare \
  --workspace ./research-workspace \
  --sample-size 20 \
  --exclusion-sample-size 10 \
  --output-dir "$AUDIT_BUNDLE"
```

Команда работает без сети, не меняет исследовательский рабочий каталог и принимает только отсутствующий `--output-dir` вне workspace, но внутри уже существующего обычного каталога. Принадлежность к workspace проверяется и по пути, и по файловой идентичности родителей, поэтому иной регистр имени на macOS не позволяет записать пакет внутрь рабочей папки. Сначала команда проверяет SHA замороженного плана, совпадение каждого захваченного текста — включая не попавшие в отбор документы — с `text_sha256` и content-addressed `document_id`, заново применяет поисковые запросы к тем же полным текстам, требует полного сопоставления результатов отбора и одобренной первичной разметки по `chain_id + document_id`, а затем снова сверяет основную и каждую указанную альтернативную цитату с соответствующим текстом. Повторные записи источника одной пары объединяются только при одинаковом SHA полного текста и одинаковом повторно вычисленном наборе совпадений; иначе подготовка блокируется как неоднозначная. Перед публикацией runtime повторяет снимок всех входов, а каталог переносит атомарно с запретом замены даже при гонке. Любая ошибка оставляет рабочий каталог неизменным и не публикует частичный результат.

В новом каталоге появятся ровно такие рабочие файлы:

- `screening-candidates.audit.jsonl` — полная закрытая рамка с производными `audit-candidate-sha256:…`, SHA плана, исходными `source_ids` и повторно проверенными совпадениями;
- `primary-decisions.audit.jsonl` — первичная разметка, спроецированная в точный 20-полевой audit-контракт и повторно проверенная по полному тексту;
- `coding-audit-plan.json` — замороженные детерминированные выборки общей рамки и исключений;
- `secondary-review-queue.jsonl` — идентичность кандидата и хеши содержимого для независимого проверяющего без метки, цитаты, вывода или другого содержательного ответа первого кодировщика;
- `secondary-coding-template.jsonl` — только идентичность и версия справочника кодирования; все содержательные поля пусты, `human_review="pending"`, `quote_verified=false` и `full_text_reviewed=false`;
- `coding-audit-inputs-manifest.json` — SHA исходного frozen-плана, screening, primary и реестра источников, SHA канонического реестра текстов, полная рамка и обязательная выборка кандидатов, размер и SHA каждого из пяти файлов содержимого, а также собственный `manifest_sha256`; поля `human_approval_created=false` и `legal_readiness=false` прямо запрещают считать пакет одобрением или готовностью жалобы.

Рамка и первичные решения охватывают всех кандидатов; очередь и пустые шаблоны содержат только `required_candidate_ids` из замороженного audit-плана. Так независимый проверяющий получает ровно выбранную работу, а полнота исходного знаменателя остаётся проверяемой.

Каталог — воспроизводимый первичный пакет, а не результат независимой проверки. Неизменённый `secondary-coding-template.jsonl` намеренно не проходит `coding-reliability`. Второй человек должен независимо прочитать полный текст, заполнить все поля, указать другого `coder`, проверить цитату и затем сформировать отдельный четырёхполевой `audit-decisions.jsonl`. При реальном расхождении отдельный человек готовит `adjudications.jsonl`. Команда подготовки не выполняет вторую разметку, разрешение расхождений, юридическое одобрение или подачу жалобы.

### 2. Экспертный ручной путь остаётся совместимым

Если уже есть точные специальные входы по контракту, `quality coding-audit-plan` продолжает работать как прежде. В этом пути `screening-candidates.jsonl` перечисляет всю замороженную рамку (минимальная строка — `{"candidate_id":"candidate-1"}`), а `primary-decisions.jsonl` содержит для каждого ID ровно закрытую запись кодирования из определения `coding_audit_decision.secondary_coding` в `schemas/practice-quality.v1.json`.

Обычные результаты `screening-candidates.jsonl` и `coding-decisions.jsonl` не являются такими ручными audit-входами: в них нет производного audit-level `candidate_id`, а карточка кодирования имеет другую оболочку. Не переименовывай их и не дописывай SHA после проверки — используй штатную команду либо подготовь точные специальные записи под контролем человека.

Во всех audit-digests используется одна канонизация: JSON кодируется в UTF-8 через `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`, затем считается SHA-256 полученных bytes и записывается как 64 строчных hex-символа. Для digest JSONL runtime сначала сортирует прочитанные записи по каноническому SHA каждой записи, затем применяет ту же канонизацию к полученному JSON-массиву. Порядок ключей и пробелы исходного файла не влияют на digest; изменение значения влияет.

Исключение существует только для диагностики уже невалидного значения: escaped lone surrogate из синтаксически допустимого JSON невозможно закодировать в канонический UTF-8. Такая запись остаётся видимой в `invalid_*` и `unresolved_candidate_ids`, а для её сортировки и diagnostic ID используется детерминированный compact JSON с `ensure_ascii=true`. Этот служебный отпечаток не подтверждает переданный content hash и не может сделать запись допустимой или завершить аудит.

`quality coding-reliability` читает план, primary, audit и adjudication как строгий UTF-8 JSON/JSONL: повторный ключ на любом уровне, `NaN`, `Infinity` или `-Infinity` дают ошибку входа `2`, а не результат проверки. Допустимые формы файлов не меняются: один объект, массив объектов или JSONL там, где они уже поддерживались.

Для экспертного ручного пути выполни:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
JM="$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py"

python3 "$JM" quality coding-audit-plan \
  --screening-candidates ./screening-candidates.jsonl \
  --primary-decisions ./primary-decisions.jsonl \
  --plan-sha256 "$FROZEN_SEARCH_PLAN_SHA256" \
  --sample-size 20 \
  --exclusion-sample-size 10 \
  --output ./coding-audit-plan.json
```

`coding-audit-plan.json` связывает точный search-plan hash, канонический digest всех screening-кандидатов, digest полной первичной разметки, детерминированную общую выборку и отдельную выборку исключений. `sample_size` и `exclusion_sample_size` — независимые верхние пределы: фактический список короче, если соответствующая рамка меньше, а один кандидат может попасть в обе выборки. `required_candidate_ids` — их отсортированное объединение без повторов, а не сумма длин. Secondary review не заменяет primary cards и должен называть тот же `candidate_id`, что внешний audit record.

Каждая строка `audit-decisions.jsonl` — объект ровно с четырьмя полями, без дополнительных ключей:

```json
{"candidate_id":"candidate-1","primary_coding_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","secondary_coding":{"candidate_id":"candidate-1","chain_id":"chain-1","document_id":"document-1","label":"core_merits","speaker":"court","proposition":"Суд применил проверяемое толкование.","quote":"Точная цитата из полного текста.","quote_locator":"абзац 24","norm_edition_id":"edition-1","reasoning_to_outcome":"Толкование стало необходимым основанием исхода.","reading_family":"family-1","relation":"supports","remedy":"оставить судебный акт без изменения","coder":"secondary-reviewer","codebook_version":"v1","material_facts":["Существенный факт дела"],"alternative_grounds":[],"human_review":"approved","quote_verified":true,"full_text_reviewed":true},"secondary_coding_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
```

`primary_coding_sha256` — digest точной закрытой primary-записи этого `candidate_id`; `secondary_coding_sha256` — digest ровно вложенного объекта `secondary_coding`. Вложенная запись должна иметь показанный полный набор полей, пройти тот же coding-contract, называть тот же candidate/chain/document/codebook и иметь другого coder. Значения `aaaa…` и `bbbb…` в примере — только обозначения: в рабочем файле их заменяет реально рассчитанный digest, а не произвольная строка.

Каждая строка `adjudications.jsonl` — объект ровно с семью полями:

```json
{"candidate_id":"candidate-1","primary_coding_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","secondary_coding_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","resolved_fields":{"label":"core_merits"},"adjudicator":"adjudicator-reviewer","reviewed_at":"2026-08-27T12:00:00Z","human_review":"approved"}
```

Adjudication нужен только для фактического расхождения. `resolved_fields` должен содержать ровно все и только различавшиеся поля из закрытого набора `label`, `speaker`, `norm_edition_id`, `reading_family`, `relation`, `reasoning_to_outcome`, `alternative_grounds`, `remedy`; оба hashes должны совпадать с конкретной парой разметок, а adjudicator должен отличаться от обоих coders. Новые или неаудируемые поля, частичное разрешение и adjudication без расхождения блокируют завершение.

После независимой разметки выполни (для штатного пакета оставь plan и primary внутри него):

```bash
python3 "$JM" quality coding-reliability \
  --audit-plan "$AUDIT_BUNDLE/coding-audit-plan.json" \
  --primary-decisions "$AUDIT_BUNDLE/primary-decisions.audit.jsonl" \
  --audit-decisions ./audit-decisions.jsonl \
  --adjudications ./adjudications.jsonl \
  --output ./coding-reliability.json
```

При ручном пути замени первые две ссылки на свой `coding-audit-plan.json` и свой точный `primary-decisions.jsonl`.

`coding-reliability.json` становится `complete=true`, только когда closed contract плана и его digest действительны, текущая primary-разметка совпадает с замороженной, второй coder действительно независим, вся frozen sample размечена полными coding records, а каждое существенное расхождение разрешено content-bound adjudication. `reviewed_at` adjudication должен быть полной датой и временем RFC 3339 с секундами и часовым поясом и не может находиться в будущем. Неполные, лишние, дублирующиеся, неканонические или связанные с другим candidate записи сохраняются в соответствующих `invalid_*` и `unresolved_candidate_ids`, а не имитируют согласие.

Вывод хранит входные digests, точные массивы required/audited/missing/invalid/unresolved candidate IDs, `field_disagreements`, `false_exclusion_diagnostics` и digest adjudication-файла. Сами adjudication-записи и выведенные из них итоговые coding records в отчёт не копируются. Единого коэффициента юридической готовности нет.

## Предподачная актуальность: producer → consumer

Не составляй refresh plan или список treatments вручную. `quality prefiling-refresh` принимает только артефакты, сформированные публичным кешем из одного и того же текущего состояния.

### 1. Объяви проверяемый охват

Создай `coverage-requirements.json` как непустой JSON-массив либо эквивалентный JSONL. Каждый объект задаёт хотя бы одно измерение из `court_id`, `period_id`, `enumerator_id`, `source_role`:

```json
[
  {
    "court_id": "2kas",
    "period_id": "post-2019",
    "enumerator_id": "ksoyu_daily_v2",
    "source_role": "official_enumerator_observation"
  }
]
```

Другие поля запрещены. Значения должны быть непустыми каноническими идентификаторами: без начальных/конечных или схлопываемых пробелов и без управляющих/форматирующих символов. Для `source_role` разрешены только `official_enumerator_observation`, `official_user_seed`, `official_authority_seed`, `discovery_only`. Дубликаты producer удаляет детерминированно. Каждый `coverage_gap` может относиться только к одному из явно заявленных requirements и повторяет его scope; отсутствие наблюдения не превращается в ноль практики. Scope считается наблюдённым только когда все записи `funnel_state`, попавшие в точный scope, имеют совпадающую официальную seed-role и допустимый официальный URL на стадии `full_text_extracted` или позднее, с целым content-addressed snapshot; начиная с `indexed` дополнительно требуется целый индексированный текст. Одна успешная цепочка не скрывает соседнюю раннюю, blocked, discovery-only или повреждённую цепочку того же scope: requirement остаётся gap.

### 2. Сними полный treatment-quality-set

```bash
python3 "$JM" cache treatment quality-export \
  --root ./cassation-public-cache \
  --output ./treatment-quality-set.json
```

Это полный снимок population, а не выборка «удобных» verified-записей. Envelope содержит:

- `corpus_evidence_digest` текущего кеша;
- отсортированный полный `treatment_ids`;
- `treatment_population_sha256` по всем treatment rows и всей неизменяемой review history;
- `integrity_issue_ids` для повреждённых объектов, индекса или нарушенной ссылочной целостности, обычно пустой;
- `items`, где каждый ID присутствует ровно один раз и имеет эффективный status `candidate`, `verified`, `rejected` или `superseded`;
- `set_sha256` по всему envelope без самого `set_sha256`.

Candidate или повреждённая resolved-запись остаётся видимой как `candidate` с `quality_blockers`. Удалить pending row из файла нельзя: это нарушит полный набор и заблокирует prefiling.

`review_decision` хранит неизменяемое исходное решение человека — только `verified` или `rejected`. Если для завершённой записи создан единственный replacement candidate через `supersedes_treatment_id`, прежняя запись получает только эффективный export-status `superseded`, но её `review_decision`, review history и доказательства не переписываются. Новый candidate одновременно входит в pending, поэтому gate остаётся незавершённым до его собственного review. После review замещённая запись остаётся в `superseded`, а replacement входит в `verified` или `rejected`. Ветка из нескольких replacements, цикл, отсутствующая взаимная ссылка, смена source/target identity или нарушение хронологии переводят затронутые записи в fail-closed candidate/blocker, а не выбирают победителя молча.

Контракты `verified` и `rejected`, включая привязку к индексированному официальному полному тексту, описаны в [публичном корпусном кеше](public-corpus-cache.md#4-treatment-последующее-обращение-с-авторитетной-позицией).

### 3. Сформируй refresh plan

Не изменяя кеш между quality-export и refresh-plan, выполни:

```bash
python3 "$JM" cache refresh-plan \
  --root ./cassation-public-cache \
  --as-of "$CHECKED_THROUGH_RFC3339" \
  --max-age-seconds 604800 \
  --coverage-requirements ./coverage-requirements.json \
  > ./refresh-plan.json
```

`refresh-plan.json` закрыт по полям и content-bound через `plan_id`. Он содержит текущий `evidence_digest`, полный `treatment_ids`, тот же `treatment_population_sha256`, заявленные `coverage_requirements`, stale/unfetched `entries` и только выводимые из requirements `coverage_gaps`.

Если кеш изменился после одного из двух producer-вызовов, заново создай оба артефакта. Не исправляй digest или ID вручную.

### 4. Выполни prefiling gate

```bash
python3 "$JM" quality prefiling-refresh \
  --baseline-corpus-digest "$BASELINE_CORPUS_DIGEST" \
  --current-corpus-digest "$CURRENT_CORPUS_DIGEST" \
  --subject-evidence-sha256 "$CURRENT_WORKSPACE_EVIDENCE_SHA256" \
  --refresh-plan ./refresh-plan.json \
  --treatments ./treatment-quality-set.json \
  --corpus-root ./cassation-public-cache \
  --checked-through "$CHECKED_THROUGH_RFC3339" \
  --filing-cutoff "$FILING_CUTOFF_RFC3339" \
  --reviewer "$REVIEWER" \
  --reviewed-at "$REVIEWED_AT_RFC3339" \
  --claim-id claim-1 \
  --claim-id claim-2 \
  --output ./pre-filing-refresh.json
```

`baseline/current-corpus-digest` принимают либо 64 строчных hex-символа, либо значение `corpus-evidence-sha256:<64 hex>` из кеша. `subject-evidence-sha256` — ровно 64 строчных hex-символа. Нужен хотя бы один `--claim-id`; каждый ID должен быть уникальным и каноническим.

Для завершённого результата timestamps имеют полную форму RFC 3339 с секундами и часовым поясом. `filing_cutoff` здесь — контрольный момент начала финального окна подготовки к подаче, а не вычисленный процессуальный срок. `refresh-plan.as_of` должен точно совпадать с `checked_through`, `reviewed_at` не раньше `checked_through`, а `checked_through` не раньше `filing_cutoff`; `as_of`, `checked_through` и `reviewed_at` не могут находиться в будущем. Сокращённая дата/время — ошибка входа; отсутствующий timezone или несовместимая хронология не могут дать `complete=true`.

`--corpus-root` обязателен и указывает на тот же существующий публичный кеш. Consumer открывает его только для чтения, не создаёт и не мигрирует таблицы, не запускает сеть и не исправляет данные. До чтения он проверяет обычный SQLite 3 header, отсутствие `-wal`, `-shm` и `-journal`, затем фиксирует статический fingerprint файла базы (device/inode, размер, `mtime_ns` и SHA-256 bytes). Те же header, sidecars и fingerprint проверяются после согласованной read transaction: их изменение означает TOCTOU и блокирует результат. Отсутствующая схема, symlink в database/object-store, повреждённый snapshot/index или нарушение внешних ключей также дают fail-closed результат. Для безопасной проверки активного WAL-кеша сначала сделай отдельную согласованную копию в SQLite `DELETE` mode.

В одной read transaction consumer заново строит refresh plan и treatment-quality-set из live-кеша, сверяет digest до и после чтения и требует одновременно:

- plan corpus digest равен current corpus digest;
- treatment-set corpus digest равен тому же current corpus digest;
- treatment IDs из plan и set совпадают полностью;
- population SHA из plan и set совпадает;
- `set_sha256`, `plan_id`, coverage-requirements digest и gap-subset корректны;
- live plan и live treatment set совпадают по каноническому JSON с переданными producer-артефактами, а `integrity_issue_ids` пуст;
- union четырёх непересекающихся partition — `pending_treatment_ids`, `verified_treatment_ids`, `rejected_treatment_ids`, `superseded_treatment_ids` — ровно равен полной population.

Результаты: `current_no_material_change`, `bounded_current_with_disclosed_gaps`, `refresh_incomplete`, `material_change_requires_reanalysis`. Новый treatment меняет corpus/population binding; unresolved candidate блокирует прежний вывод. Неизменившийся раскрытый coverage gap допускает только `bounded_current_with_disclosed_gaps` и не исчезает из отчёта.

## Коды завершения обязательных проверок

Команды `quality coding-reliability` и `quality prefiling-refresh` возвращают:

- `0` — только когда top-level `complete` является Boolean `true`;
- `2` — неверные параметры, отсутствующий/повреждённый входной файл, нарушенный обязательный envelope или ошибка записи результата;
- `3` — входы удалось оценить, но проверка неполна, устарела или имеет блокеры и вернула `complete=false`.

При коде `3` полный JSON остаётся в stdout. Если указан `--output`, тот же результат записывается туда до возврата кода `3`; caller должен разобрать причины и остановить следующий автоматический шаг. Код `0`, включая `bounded_current_with_disclosed_gaps`, означает только завершение этой ограниченной проверки и не является юридическим одобрением или разрешением подать жалобу.

## Связь с handoff

Если claim зависит от trajectory, uncertainty, reliability или refresh, portable v2 result обязан включить content hashes соответствующих артефактов. Для `prefiling_refresh` handoff повторяет closed-contract проверку: сверяет `refresh_id`, requirements digest и принадлежность gap заявленному scope, corpus/population/set bindings, полную непересекающуюся классификацию treatment IDs, timestamps и точное множество `claim_ids`. В handoff допускается только `complete=true`; `affected_claim_ids`, pending IDs и blocking diagnostics должны быть пусты.

Изменение связанного артефакта делает зависимые claims stale. Reviewed result строится кассационным CLI из текущего workspace; caller не может передать собственный findings JSON. Перед включением reviewed finding в жалобу центральный host снова открывает current workspace, проверяет exact ready claim и полный refresh, связывает final wording с exact finding IDs и затем применяет отдельный [filing evidence binding](filing-evidence-binding.md). Quality hash внутри portable result не заменяет current host resolution.

## Миграция ранее созданных v1-артефактов

Файлы `practice-quality.v1.json` и `case-relative-workbench.v1.json`, а также top-level `schema_version: "1.0"`, сохранены ради стабильных путей установленного skillset. Их closed contracts намеренно усилены in place: старые audit/refresh/treatment/prefiling/handoff артефакты без новых обязательных полей и bindings больше не считаются текущими.

После обновления skillset заново создай, в таком порядке:

1. `coding-audit-plan.json` и `coding-reliability.json`, если они участвуют в выводе;
2. `treatment-quality-set.json` и `refresh-plan.json` из неизменённого состояния текущего public cache;
3. `pre-filing-refresh.json` для полного множества claim IDs;
4. reviewed handoff и trust receipts, содержащие новый quality artifact hash.

Не дописывай отсутствующие поля и SHA вручную: новый runtime должен пересчитать их из первичных данных. Старые файлы остаются audit-readable как исторические материалы, но не дают текущего `complete=true` и не проходят новый handoff gate.
