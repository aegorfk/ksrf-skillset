# Самодостаточный публичный корпусный кеш

## Содержание

- [1. Privacy boundary](#1-privacy-boundary)
- [2. Инициализация, ingest и поиск](#2-инициализация-ingest-и-поиск)
- [3. Воронка полного текста](#3-воронка-полного-текста)
- [4. Treatment: последующее обращение с авторитетной позицией](#4-treatment-последующее-обращение-с-авторитетной-позицией)
- [5. Run pins и переносимый public-only пакет](#5-run-pins-и-переносимый-public-only-пакет)
- [6. Обновление](#6-обновление)


Публичный кеш — локальный повторно используемый слой официальных актов. Он не заменяет workspace конкретного дела и не принимает акты заявителя, локальные файлы, авторизационные данные или иной private material.

## 1. Privacy boundary

Разрешённые роли seed:

- `official_enumerator_observation`;
- `official_user_seed`;
- `official_authority_seed`;
- `discovery_only` — только метаданные для обнаружения, без сохранения raw snapshot как доказательства.

До записи отклоняются `applicant_private`, `public=false`, `file://`, URL с логином/паролем, localhost, непубличным IP literal или secret-bearing query key (`token`, `key`, `secret`, `password`, `auth`, `signature` и эквиваленты). Не помещайте в URL персональные данные, временные подписанные ссылки или session IDs даже под нестандартным именем параметра. Fragment удаляется при канонизации.

Raw bytes разрешённого официального источника сохраняются content-addressed; snapshot и run pins неизменяемы. Материалы заявителя остаются только в его case workspace.

## 2. Инициализация, ingest и поиск

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache init \
  --root ./cassation-public-cache

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache register-seed \
  --root ./cassation-public-cache \
  --url 'https://2kas.sudrf.ru/modules.php?name=sud_delo' \
  --role official_user_seed
```

Возьмите `seed_id` из JSON-ответа. `parser-manifest.json` должен раскрывать как минимум фактически использованные adapter/parser versions. Добавляйте только уже полученные публичные bytes и, при наличии, извлечённый текст:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache ingest \
  --root ./cassation-public-cache \
  --seed-id seed-sha256:<sha256> \
  --raw ./official-act.pdf \
  --content-type application/pdf \
  --fetched-at 2026-08-27T10:00:00Z \
  --parser-manifest ./parser-manifest.json \
  --text ./official-act.txt \
  --document-id 2kas-act-123 \
  --chain-id 2kas:case-123 \
  --query-lane higher_authority

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache search \
  --root ./cassation-public-cache \
  --query 'премия статья 135' \
  --limit 20
```

SQLite хранит seeds, observations, immutable snapshots, run pins, индексированный текст, воронку полного текста и treatment history. Для акта, который будет источником treatment, вместе с `--text` явно передай канонические `--document-id`, `--chain-id` и `--query-lane`: quality-export должен связать review именно с этим индексированным полным текстом и судебной цепочкой. Поисковый hit возвращает snapshot/document/chain candidate, query lane, source URL/role и locator; это discovery evidence, пока не завершено юридическое полнотекстовое кодирование. Используется FTS5; при его отсутствии включается раскрытый детерминированный fallback, а при последующем появлении FTS5 тексты индексируются без повторной загрузки.

`corpus_evidence_digest` связывает не только seeds и snapshots, но и множество уникальных пар `seed_id` ↔ `snapshot_id` из observations. Новая distinct-привязка snapshot к другому seed (включая seed другой source-role) материальна и меняет digest. Повторное получение тех же bytes тем же seed создаёт лишь ещё одно observation той же пары: различия только в `fetched_at`, `content_type` или parser metadata не меняют evidence digest. Эти metadata остаются в истории и могут влиять на планирование свежести, но не выдают идентичный re-fetch за новое содержание или новый source binding.

## 3. Воронка полного текста

Каждая независимая цепочка проходит без пропусков:

`enumerated` → `card` → `document_link` → `payload_validated` → `full_text_extracted` → `indexed` → `screened` → `coded` → `approved_independent_chain`.

Отдельные состояния ошибки или ручного ожидания: `blocked`, `retryable_error`, `official_page_no_text`, `unextractable`, `ocr_pending`, `human_verification_pending`. Ошибка не становится успешным этапом. Переход после устранения ошибки разрешён только в предусмотренный следующий проверяемый этап.

Записывайте source/court/period/enumerator dimensions уже на первом событии:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache funnel record \
  --root ./cassation-public-cache \
  --chain-id 2kas:case-123 \
  --status enumerated \
  --snapshot-id snapshot-sha256:<sha256> \
  --source-role official_user_seed \
  --court-id 2kas \
  --period-id post-2019 \
  --enumerator-id ksoyu_daily_v2

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache funnel record \
  --root ./cassation-public-cache \
  --chain-id 2kas:case-123 \
  --status card \
  --snapshot-id snapshot-sha256:<sha256>

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache funnel report \
  --root ./cassation-public-cache
```

Повторяйте `record` для каждого реально достигнутого этапа. Отчёт показывает текущие состояния, переходы и разрезы по source role, court, period и enumerator; URL/PDF не подменяют число независимых одобренных цепочек.

`source-role` должна совпадать с ролью seed, через observation которого получен effective snapshot. Если нужен `official_enumerator_observation`, сначала зарегистрируй и ingest именно seed этой роли. Подмена роли при funnel record или перенос роли на snapshot другого seed отклоняются.

## 4. Treatment: последующее обращение с авторитетной позицией

Связь акта с постановлением КС РФ, разъяснением ВС РФ или иным authority сначала создаётся как candidate. `target-identity.json` — структурированная идентичность цели, например номер, дата и official URL.

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache treatment discover \
  --root ./cassation-public-cache \
  --source-chain-id 2kas:case-123 \
  --source-court-id 2kas \
  --target-authority-id ksrf:23-p:2023 \
  --target-kind ksrf_decision \
  --target-identity ./target-identity.json \
  --treatment-type applies \
  --snapshot-id snapshot-sha256:<sha256>
```

Допустимые типы: `applies`, `follows`, `distinguishes`, `limits`, `rejects`, `does_not_reach`, `supersedes`, `unclear`. `source-chain-id`, `source-court-id`, `target-authority-id` и `target-kind` должны быть непустыми каноническими идентификаторами: без лишних пробелов и управляющих/форматирующих символов. Candidate не имеет доказательственной силы.

`discover` защищает чтение текущего snapshot, повтор уже существующего кандидата, проверку predecessor/successor, создание treatment и его `candidate_created` одной зарезервированной SQLite-транзакцией. Точный повтор того же ordinary или replacement candidate безопасно возвращает уже сохранённый статус и не дублирует историю; несовпадающая строка или история не исправляется молча, а блокирует операцию.

Для `verified` одновременно нужны:

- индексированный официальный полный текст, чей `snapshot_id` и `chain-id` совпадают с candidate;
- совпадающий authority ID и вручную подтверждённая structured identity;
- speaker именно `court`, точная найденная в индексированном тексте цитата и locator;
- канонический reviewer и `reviewed-at` в полной форме RFC 3339 с секундами и часовым поясом, не в будущем и не раньше неизменяемого `created_at` candidate;
- отсутствие `decision-reason`, потому что это не отклонение.

Команда:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache treatment review \
  --root ./cassation-public-cache \
  --treatment-id treatment-sha256:<sha256> \
  --decision verified \
  --reviewer "И.И. Иванов" \
  --quote 'точная цитата суда' \
  --locator 'абзац 24' \
  --speaker court \
  --confirmed-target-authority-id ksrf:23-p:2023 \
  --target-identity-confirmed \
  --reviewed-at 2026-08-27T11:00:00Z
```

Для `rejected` причина обязательна, но выдумывать цитату не нужно. Review всё равно требует индексированный официальный полный текст той же цепочки. Если цитата не используется, не передавай `--quote`, `--locator` и `--speaker`; если используется, она должна присутствовать в полном тексте, иметь locator и speaker `court`:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache treatment review \
  --root ./cassation-public-cache \
  --treatment-id treatment-sha256:<sha256> \
  --decision rejected \
  --reviewer "И.И. Иванов" \
  --decision-reason 'Целевой акт не рассматривается судом в мотивировке' \
  --reviewed-at 2026-08-27T11:00:00Z
```

После завершения review создай полный quality-export:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache treatment quality-export \
  --root ./cassation-public-cache \
  --output ./treatment-quality-set.json

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache treatment list \
  --root ./cassation-public-cache \
  --verified-only

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache treatment history \
  --root ./cassation-public-cache \
  --treatment-id treatment-sha256:<sha256>
```

Review и его история неизменяемы: сохранённый `review_decision` остаётся `verified` или `rejected`. Новая оценка создаёт новый treatment; для явной замены используй `--supersedes-treatment-id` при `discover`, не редактируй прежнюю запись. Replacement разрешён только для уже завершённой записи с теми же `source_chain_id` и `target_authority_id`, и у прежней записи может быть только один непосредственный replacement.

Проверка snapshot/index, официального источника, source chain, candidate и его исходной истории, запись решения и новая неизменяемая запись истории выполняются в одной зарезервированной SQLite-транзакции. Если кэш уже занят другой записью, команда возвращает код `2`, пишет понятную ошибку в stderr и не делает автоматических повторов: дождись завершения другой операции и повтори команду явно. Такая ошибка не выбирает решение проверяющего и не означает юридического одобрения. Прямая замена файла в content-addressed object store не блокируется SQLite; поэтому целостность файла проверяется при review и ещё раз последующими quality/live-cache gates.

Как только создан единственный replacement candidate, прежний treatment экспортируется с эффективным `status=superseded`, сохраняя исходный `review_decision` и его доказательства. Replacement остаётся `candidate`, поэтому prefiling блокируется до нового review. После него population содержит старый `superseded` и новый `verified` либо `rejected`. Ветка, цикл, отсутствующий predecessor, несовпадение взаимных ссылок или source/target identity, а также `reviewed_at < created_at` не разрешаются эвристически: quality-export сохраняет затронутые IDs как candidate/blocker.

`quality-export` включает каждый treatment ID, включая candidate и resolved rows, которые не проходят content-bound проверку. Такой resolved row понижается в экспортируемый `candidate` с `quality_blockers`; он не исчезает из population. Envelope связан с текущим кешем полями `corpus_evidence_digest`, `treatment_population_sha256`, `integrity_issue_ids`, `treatment_ids` и `set_sha256` и предназначен для `quality prefiling-refresh`. Непустой `integrity_issue_ids` раскрывает повреждённый snapshot/index или нарушение ссылочной целостности и блокирует завершение. Consumer делит полную population ровно на четыре непересекающиеся группы: pending candidate, `verified`, `rejected`, `superseded`. Произвольный JSON-массив или `treatment list --verified-only` не является допустимым входом prefiling.

## 5. Run pins и переносимый public-only пакет

Закрепите точный набор первичных snapshots за публичным запуском:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache pin-run \
  --root ./cassation-public-cache \
  --run-id public-run-2026-08-27 \
  --snapshot snapshot-sha256:<sha256>

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache export-run \
  --root ./cassation-public-cache \
  --run-id public-run-2026-08-27 \
  --output ./public-package
```

Пакет сохраняет public seeds, content-addressed objects, snapshots, observations, indexed-text provenance (`document_id`, chain candidate, query lane), исходные run pins, полную funnel state/event history связанных цепочек и treatment review history. Дополнительные публичные snapshots, необходимые для воспроизведения связанной истории, могут войти в пакет, но не становятся pins исходного run.

Импорт сначала fail-closed проверяет manifest digest, object/content hashes, идентификаторы, URL/roles, observations, text provenance, pins, непрерывность funnel и неизменяемость treatment history; лишь затем выполняет идемпотентную запись:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache import-run \
  --root ./restored-public-cache \
  --input ./public-package
```

Roundtrip должен сохранять evidence digest, поиск с provenance, funnel и verified treatment. Изменённый объект, manifest, пропущенный этап, private URL или противоречащая история отклоняются целиком.

## 6. Обновление

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache refresh-plan \
  --root ./cassation-public-cache \
  --as-of 2026-08-27T12:00:00Z \
  --max-age-seconds 604800 \
  --coverage-requirements ./coverage-requirements.json \
  > ./refresh-plan.json
```

`coverage-requirements.json` — непустой JSON-массив или JSONL. Каждый элемент задаёт хотя бы одно из измерений `court_id`, `period_id`, `enumerator_id`, `source_role`; другие поля, пустые/неканонические значения и неподдерживаемые source roles запрещены. Producer детерминированно удаляет дубликаты, сохраняет requirements в plan и создаёт `coverage_gap` только для точно заявленного scope, по которому нет позднего официального наблюдения: каждая попавшая в scope цепочка должна иметь стадию `full_text_extracted` или позднее, совпадающую официальную seed-role, допустимый официальный URL и целый snapshot; для `indexed` и следующих стадий нужен также целый индексированный текст. Одна успешная цепочка не скрывает blocked, раннюю, discovery-only или повреждённую соседнюю цепочку того же scope — gap остаётся.

`refresh-plan` не запускает сеть и не обходит защиту. Помимо устаревших public seeds и раскрытых gaps, он фиксирует полный `treatment_ids`, `treatment_population_sha256` и текущий `evidence_digest`. Evidence digest теперь охватывает все treatment rows и всю review history, а не только verified records. Поэтому новый candidate, новое review-событие или новый snapshot делает прежний refresh/treatment pair потенциально устаревшим.

Для prefiling сначала создай `treatment-quality-set.json`, затем, не изменяя кеш, `refresh-plan.json`. Оба producer-артефакта должны иметь одинаковые corpus/population bindings. Consumer требует `--corpus-root`, открывает существующий кеш без записи и заново строит оба артефакта в одной согласованной read transaction. При открытии и после чтения он сверяет SQLite 3 header, отсутствие `-wal`, `-shm`, `-journal` и статический fingerprint файла базы (device/inode, размер, `mtime_ns`, SHA-256 bytes); изменение означает TOCTOU и блокирует результат. Повреждение content-addressed object/index, symlink-компонент database/object-store или нарушение внешних ключей также блокируют проверку; для активной базы подготовь отдельную согласованную копию в `DELETE` mode. Полный вызов и коды `0`/`2`/`3` приведены в [руководстве quality-слоя](practice-quality.md#предподачная-актуальность-producer--consumer).
