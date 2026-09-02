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
  --text ./official-act.txt

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache search \
  --root ./cassation-public-cache \
  --query 'премия статья 135' \
  --limit 20
```

SQLite хранит seeds, observations, immutable snapshots, run pins, индексированный текст, воронку полного текста и treatment history. Поисковый hit возвращает snapshot/document/chain candidate, query lane, source URL/role и locator; это discovery evidence, пока не завершено юридическое полнотекстовое кодирование. Используется FTS5; при его отсутствии включается раскрытый детерминированный fallback, а при последующем появлении FTS5 тексты индексируются без повторной загрузки.

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
  --source-role official_enumerator_observation \
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

Допустимые типы: `applies`, `follows`, `distinguishes`, `limits`, `rejects`, `does_not_reach`, `supersedes`, `unclear`. Candidate не имеет доказательственной силы. Для `verified` нужны совпадающий authority ID, подтверждённая structured identity, speaker именно `court`, точная цитата, locator, reviewer и ISO timestamp:

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

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache treatment list \
  --root ./cassation-public-cache \
  --verified-only

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" cache treatment history \
  --root ./cassation-public-cache \
  --treatment-id treatment-sha256:<sha256>
```

Review и его история неизменяемы. Новая оценка создаёт новый treatment; для явной замены используйте `--supersedes-treatment-id` при `discover`, не редактируйте прежнюю запись.

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
  --max-age-seconds 604800
```

`refresh-plan` только перечисляет устаревшие public seeds и раскрытые coverage requirements; он не запускает безграничную сеть и не обходит защиту. Повторное получение тех же bytes не меняет evidence digest; новый snapshot делает зависимый анализ потенциально устаревшим.
