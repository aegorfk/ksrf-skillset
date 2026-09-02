# Контур позиций применительно к делу заявителя

## Содержание

- [1. Intake всегда предшествует fingerprint](#1-intake-всегда-предшествует-fingerprint)
- [2. Fingerprint и обязательные признаки](#2-fingerprint-и-обязательные-признаки)
- [3. Query lifecycle: подтверждение до freeze](#3-query-lifecycle-подтверждение-до-freeze)
- [4. Полная карточка позиции](#4-полная-карточка-позиции)
- [5. Сопоставимость и applicant-relative relation](#5-сопоставимость-и-applicant-relative-relation)
- [6. Четыре adverse-корзины и предел вывода](#6-четыре-adverse-корзины-и-предел-вывода)
- [7. Нормативный мост](#7-нормативный-мост)
- [8. Статус, отчёт, validation и handoff](#8-статус-отчёт-validation-и-handoff)


Этот слой отвечает не на вопрос «какие акты подтверждают готовый тезис», а на вопрос «какой ограниченный вывод допустим после проверки раскрытого корпуса и его отношения к конкретному делу».

## 1. Intake всегда предшествует fingerprint

Сначала инвентаризируйте акты заявителя. Команда сохраняет приватную рабочую копию, публично безопасный manifest, SHA-256 и статус извлечения; она не отправляет материалы во внешний корпус.

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" intake \
  --workspace ./judicial-meaning-run \
  --inputs ./acts/
```

`case prepare` отклонит fingerprint, если `intake/applicant-manifest.jsonl` пуст, документ не инвентаризирован или для проверенного документального признака нет извлечённого текста. Скан сначала проходит явный OCR и постраничную ручную сверку.

## 2. Fingerprint и обязательные признаки

`case-answers.json` содержит:

- `issue` — нейтральный юридический вопрос без ответа;
- `norm_refs` — точные нормы и при необходимости редакции;
- `features` — материальные и процессуальные признаки;
- необязательно `query_axes` — предложенные формулировки по поисковым направлениям.

Обязательные `feature_id`:

- `norm_edition` — применимая редакция нормы;
- `applicant_case_meaning` — исходозначимый смысл в акте заявителя;
- `procedural_posture` — процессуальная стадия и результат.

Каждый признак имеет уникальный `feature_id`, `value`, `status` (`verified`, `unknown`, `disputed`), `material`, `query_terms` и `source`. Для документального `verified` нужны `document_id` из intake и `quote_locator`; желательно также сохранить `speaker` и точную `quote`. Если значение основано на явном выборе человека, используйте `source_type=user_decision` и `decision_id`, а не выдуманный документ. Неизвестный материальный признак и отсутствующее обязательное поле создают `missing_task` и блокируют сопоставимость.

```json
{
  "issue": "Допустимые пределы уменьшения выплаты",
  "norm_refs": ["ст. 135 ТК РФ"],
  "features": [
    {
      "feature_id": "norm_edition",
      "value": "редакция на дату спорной выплаты",
      "status": "verified",
      "material": true,
      "source": {
        "document_id": "applicant-document-sha256:<sha256>",
        "quote_locator": "абзац 12"
      },
      "query_terms": []
    },
    {
      "feature_id": "applicant_case_meaning",
      "value": "суд допустил уменьшение без проверяемого критерия",
      "status": "verified",
      "material": true,
      "source": {
        "document_id": "applicant-document-sha256:<sha256>",
        "quote_locator": "абзац 18"
      },
      "query_terms": ["уменьшение выплаты без критерия"]
    },
    {
      "feature_id": "procedural_posture",
      "value": "кассация оставила отказ без изменения",
      "status": "verified",
      "material": true,
      "source": {
        "document_id": "applicant-document-sha256:<sha256>",
        "quote_locator": "резолютивная часть"
      },
      "query_terms": []
    }
  ]
}
```

Используйте фактический `document_id` из manifest:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" case prepare \
  --workspace ./judicial-meaning-run \
  --answers ./case-answers.json
```

Создаются `case-fingerprint.json`, неизменяемая версия `casework/fingerprints/fingerprint-vN.json`, `query-suggestions.jsonl` и `casework-dependencies.json`. Новая ревизия fingerprint не переписывает старую: она делает прежние comparisons, applicant relations, нормативный мост, approval, report и handoff устаревшими.

## 3. Query lifecycle: подтверждение до freeze

`case prepare` формирует высокоотзывные предложения со статусом `suggested_unconfirmed`, reason code и provenance к текущему fingerprint. Направления: точная норма, язык суда, правовой механизм, контролируемый синоним, противоположное и более узкое прочтение, альтернативное основание, позднейшее законодательство, высшая инстанция; подтверждённые признаки могут добавить `case_feature`.

Просмотрите `query-suggestions.jsonl` и до freeze явно примите каждый нужный ID. `--query-id` можно повторять:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" query accept \
  --workspace ./judicial-meaning-run \
  --query-id query-1111111111111111 \
  --query-id query-2222222222222222 \
  --reviewer "И.И. Иванов" \
  --confirmed-at 2026-08-27T10:00:00Z

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" plan template \
  --workspace ./judicial-meaning-run

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" plan freeze \
  --workspace ./judicial-meaning-run \
  --plan ./judicial-meaning-run/research-plan.json
```

Принятые запросы получают `accepted_pre_freeze` и входят в `plan_sha256`. После freeze `query accept` запрещён. Новая проверочная формулировка добавляется только как `post_freeze_supplemental`; она входит в evidence trail, но имеет `changes_original_denominator=false` и не переопределяет исходную совокупность:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" query supplement \
  --workspace ./judicial-meaning-run \
  --lane opposite_reading \
  --query 'ст. 135 ТК РФ выплата не входит в заработную плату' \
  --reason 'Проверка противоположного исходозначимого прочтения' \
  --reviewer "И.И. Иванов" \
  --confirmed-at 2026-08-27T12:00:00Z
```

## 4. Полная карточка позиции

`position check` принимает не совпадение слов, а полнотекстовую карточку. Обязательны:

- идентичность и provenance: `position_card_id`, `chain_id`, `document_id`, `court_id`, `decision_date`, `official_url`, `document_sha256`;
- атрибуция: `speaker=court`, `proposition`, точная `quote`, `quote_locator`, `quote_verified=true`, `full_text_reviewed=true`;
- право и факты: `norm_edition_id`, непустые `material_facts`, структурированные `comparison_features`;
- исход: `reasoning_to_outcome`, `outcome_materiality`, `alternative_grounds`, `outcome`, `remedy`;
- классификация и review: `reading_family`, `coder`, `human_review=approved`.

Каждый `comparison_features[]` повторяет стабильный `feature_id` fingerprint, содержит проверенное `value`, `status=verified`, `material` и `source.document_id` этой карточки с `quote_locator`. Роль мотива:

- `necessary_to_outcome` — без мотива исход не объясняется;
- `independent_sufficient_ground` — самостоятельное достаточное основание;
- `contextual` — позиция суда есть, но исход не определяет;
- `unclear` — роль не установлена.

Довод стороны, упоминание нормы и чужая цитата без принятия судом не становятся позицией суда.

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" position check \
  --input ./position-card.json \
  --workspace ./judicial-meaning-run
```

Только валидная карточка добавляется в `position-cards.jsonl`.

## 5. Сопоставимость и applicant-relative relation

Сначала сравните все материальные признаки. При нескольких карточках обязательно укажите ID:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" compare \
  --applicant ./judicial-meaning-run/case-fingerprint.json \
  --candidate ./candidate-features.json \
  --workspace ./judicial-meaning-run \
  --position-card-id position-1 \
  --reviewer "И.И. Иванов" \
  --reviewed-at 2026-08-27T13:00:00Z
```

Состояния сравнения сохраняются как `matched`, `distinguishable` или `uncertain`; review — `approved` либо `pending_human_review`. Канонический реестр — `comparability-matrix.jsonl`; `case-comparison.json` — удобная копия последнего результата.

Матрица неизменяемо связывает текущие `fingerprint_sha256`, `applicant_features_sha256`, `candidate_features_sha256` и `position_card_sha256` в `comparison_id`. Подмена любого входа или новая ревизия fingerprint требует повторного сравнения.

После этого отдельно классифицируйте отношение reading family к позиции заявителя:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" relation classify \
  --position-card ./position-card.json \
  --comparison ./judicial-meaning-run/case-comparison.json \
  --applicant-position ./applicant-position.json \
  --workspace ./judicial-meaning-run \
  --reviewer "И.И. Иванов" \
  --reviewed-at 2026-08-27T13:10:00Z
```

Допустимые отношения: `supports`, `adverse`, `distinguishes`, `neutral`, `unresolved`. Реестр `applicant-relations.jsonl` сохраняет также `stale`, reviewer и хеши position card, comparison и applicant position. `uncertain`, pending review, contextual/unclear materiality, неутверждённая applicant position или stale binding дают только `unresolved`; такой результат сохраняется для аудита и возвращает ненулевой код.

Очередь может приоритизировать проверку, но не удалять кандидатов:

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" queue build \
  --candidates ./screening-candidates.jsonl \
  --resolutions ./candidate-resolutions.json \
  --quotas ./review-quotas.json \
  --workspace ./judicial-meaning-run
```

## 6. Четыре adverse-корзины и предел вывода

До тезиса независимо проверяются:

1. `opposite_reading` — противоположное прочтение;
2. `narrower_reading` — более узкое прочтение;
3. `alternative_ground` — тот же исход по самостоятельному основанию;
4. `later_authority` — позднейший закон, акт высшей инстанции или последующее применение позиции.

Для каждой корзины JSON-карты должны содержать: выполненные query IDs; список неразрешённых сегментов; текстовое влияние результата или пробела на максимально допустимый вывод. Корзина завершена только при непустом списке выполненных запросов, пустом списке unresolved и непустом `maximum_claim_effect`.

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" adverse build \
  --cards ./judicial-meaning-run/position-cards.jsonl \
  --searched-buckets opposite_reading narrower_reading alternative_ground later_authority \
  --completed-buckets opposite_reading narrower_reading alternative_ground later_authority \
  --executed-query-ids ./adverse-query-ids.json \
  --unresolved-segments ./adverse-unresolved.json \
  --maximum-claim-effects ./adverse-claim-effects.json \
  --workspace ./judicial-meaning-run
```

Ноль карточек в завершённой корзине означает только ноль находок по перечисленным запросам. `maximum_permitted_claim` берётся из текущих plan/analysis gates и сужается при любом пробеле; его нельзя повысить вручную в мосте.

## 7. Нормативный мост

`normative-bridge.json` содержит три самостоятельных звена и review binding:

1. `applicant_case_meaning` — исходозначимый смысл спорной нормы в деле заявителя;
2. `corpus_observation` — ограниченное наблюдение в сопоставимом корпусе с adverse и пробелами;
3. `constitutional_consequence` — конкретное последствие нормативного смысла для права;
4. `ordinary_remedy_analysis` — почему обычное средство защиты устраняет или не устраняет дефект.

Также обязательны `norm_ref`, текущий `fingerprint_sha256`, точный `maximum_permitted_claim`, ограниченное `claim_wording`, непустые supporting cards, явно заданный список adverse cards, reviewer/time и `human_review=approved`.

Supporting card допускается только при `speaker=court`, `necessary_to_outcome`, текущем одобренном `matched`-сравнении и relation `supports`. Adverse card требует одобренную карточку, `matched` и relation `adverse`.

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" bridge check \
  --input ./normative-bridge.json \
  --workspace ./judicial-meaning-run \
  --maximum-permitted-claim corroborated_observed_corpus
```

Частота, число решений или расхождение сами по себе не доказывают неконституционность.

## 8. Статус, отчёт, validation и handoff

```bash
KSRF_SKILLS_ROOT="${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}"
python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" status \
  --workspace ./judicial-meaning-run

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" report \
  --workspace ./judicial-meaning-run

python3 "$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py" validate \
  --workspace ./judicial-meaning-run \
  --require-thesis-ready
```

`status` вычисляется из файлов и текущих хешей; его нельзя выставить вручную. `report` по умолчанию создаёт автономные `report/index.html` и `report/manifest.json` без внешних ресурсов. Он показывает:

- текущий fail-closed статус, `maximum_permitted_claim`, pending tasks и stale artifacts;
- исторические `not_configured` и открытые route gaps;
- знаменатель и его точный scope;
- только карточки с текущими проверенными comparison/relation, но не скрывает общий denominator;
- цитаты, official URLs, adverse-status, materiality, remedy, безопасную формулировку и следующее действие.

Наличие HTML не означает `drafting_ready`. Handoff принимает `unproven_research_questions`, `approved_bounded_findings` и `authority_cards`; legacy `selected_authorities` только читается для совместимости. Проверка различает `valid`, `stale`, `tampered`, `incompatible`; импорт в JSONL-ledger атомарен и идемпотентен.

Даже current `approved_bounded_findings` остаётся входом центрального gate, а не filing authority. Для строки `practice_claim` получатель применяет [exact filing evidence binding](filing-evidence-binding.md): заново разрешает current workspace/result/wording/refresh, проверяет отдельные practice и selection approvals и полный host draft index.
