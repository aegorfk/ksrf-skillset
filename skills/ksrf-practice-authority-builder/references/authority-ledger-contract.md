# Контракт authority ledger

## Содержание

- [Назначение](#назначение)
- [JSON-структура](#json-структура)
- [Инварианты](#инварианты)
- [Связь с KSRF artifacts](#связь-с-ksrf-artifacts)


## Назначение

Храни ledger отдельно для каждого `case_id`. Публичный акт можно переиспользовать после новой проверки применимости; факты, документы и внутренние notes между делами не переносятся без sanitization decision.

## JSON-структура

```json
{
  "schema_version": "1.0",
  "case_id": "case-001",
  "mode": "research",
  "query_profile": {
    "hypothesis_id": "H1",
    "challenged_norm": "ч. ... ст. ...",
    "norm_version": "редакция и период",
    "applied_meaning": "проверяемый судебный смысл",
    "constitutional_rights": ["ст. ... Конституции РФ"],
    "harm_mechanism": "непосредственный механизм вреда",
    "judicial_application_evidence_ids": ["E1"],
    "desired_remedy": "узкая формула результата",
    "unknowns": []
  },
  "query_log": [
    {
      "query_id": "Q1",
      "lane": "norm_and_meaning",
      "tool": "mcp__casuslegal__casuslegal_search_practice",
      "query": "юридический вопрос",
      "executed_at": "2026-08-15T12:00:00+03:00",
      "status": "completed",
      "result_ids": ["A1"],
      "coverage_note": "проверены блоки КС РФ, ВС РФ и ВАС РФ"
    }
  ],
  "authorities": [
    {
      "authority_id": "A1",
      "hypothesis_ids": ["H1"],
      "court": "КС РФ",
      "act_type": "Постановление",
      "date": "YYYY-MM-DD",
      "number": "...",
      "case_number": null,
      "title": "краткое обозначение",
      "roles": ["constitutional_doctrine"],
      "relation": "supports",
      "proposition": "одно ограниченное утверждение",
      "position_summary": "краткое проверенное содержание",
      "source": {
        "casuslegal_url": "private research URL or null",
        "official_url": "official URL or null",
        "full_text_opened": true,
        "official_verified": false,
        "checked_at": "2026-08-15"
      },
      "quote": {
        "text": "",
        "locator": "абз./п./раздел либо null",
        "key_quote": false,
        "verified_against_official": false
      },
      "transfer": {
        "matches": ["совпадение механизма"],
        "differences": ["иная отрасль"],
        "norm_fit": "direct|systemic|analogical|none",
        "norm_version_fit": "yes|partial|no|unknown",
        "temporal_fit": "current|limited|superseded|unknown",
        "remedy_fit": "direct|adapted|none|unknown",
        "limit": "чего акт не доказывает"
      },
      "risks": [],
      "verification_status": "full_text_opened",
      "drafting_ready": false
    }
  ],
  "adverse_pass": {
    "performed": true,
    "query_ids": ["Q5"],
    "authority_ids": [],
    "no_result_note": "после проверенных запросов близкая adverse-позиция не найдена"
  },
  "drafting_blocks": [],
  "human_approval": {
    "status": "pending",
    "approved_by": null,
    "reason": null
  }
}
```

## Инварианты

- `authority_id` и `query_id` уникальны внутри ledger.
- `relation`: только `supports`, `weakens`, `distinguishes`, `blocks`.
- `roles`: только значения из skill; неизвестная роль требует обновления контракта.
- Цитата с непустым `text` требует `locator` и `source.full_text_opened=true`.
- `key_quote=true` требует `official_verified` и `verified_against_official` перед drafting.
- `drafting_ready=true` требует proposition, полный текст, проверенный transfer limit, завершенный adverse pass и `verification_status` не ниже `full_text_opened`.
- `authorities[].transfer.limit` должен быть строкой. При любом другом JSON-типе
  валидатор сообщает структурную ошибку и завершает проверку без вызова строковых
  методов на исходном значении; standalone CLI возвращает обычный код ошибки
  валидации без traceback.
- `--require-drafting` дополнительно требует `human_approval.status=approved` и хотя бы один drafting block.
- `--public` запрещает URL с access/query token и предназначен только для обезличенного артефакта.

## Связь с KSRF artifacts

Authority record может порождать `ResearchFinding`:

- `authority_id` становится evidence/source id;
- `proposition` становится `thesis`;
- `relation` переносится без переименования;
- `source.official_url` и реквизиты образуют `source_anchor`;
- `quote.locator` становится `locator`;
- `transfer.limit` входит в `limitations`;
- `verification_status` сопоставляется с `candidate`, `verified`, `rejected` или `superseded`.

Не повышай status автоматически только потому, что JSON валиден.
