# Контракты исследования доктрины

## Содержание

- [DoctrineResearchRequest](#doctrineresearchrequest)
- [Артефакты workspace](#артефакты-workspace)
- [DoctrineSourceRecord](#doctrinesourcerecord)
- [DoctrineProposition](#doctrineproposition)
- [NormativeDefectCandidate](#normativedefectcandidate)
- [ConstitutionalHypothesisCard](#constitutionalhypothesiscard)
- [CoverageReport](#coveragereport)

## DoctrineResearchRequest

Минимальный JSON:

```json
{
  "schema_version": "1.0",
  "matter_id": "public-or-pseudonymous-id",
  "mode": "exploratory_norm",
  "as_of_date": "2026-08-29",
  "jurisdiction": "RU",
  "languages": ["ru", "en"],
  "norms": [
    {
      "citation": "точная ссылка на норму",
      "citation_variants": ["сокращённая ссылка", "полная ссылка"],
      "title": "название статьи или положения",
      "version_date": null,
      "public_text_excerpt": "только публичный фрагмент"
    }
  ],
  "judicial_meanings": [],
  "disputed_elements": [],
  "mechanisms": [],
  "consequences": [],
  "adjacent_norms": [],
  "subject_terms": [],
  "date_range": {"from": 1992, "to": 2026},
  "material_types": ["journal-article", "book-chapter", "dissertation"],
  "provider_access": {},
  "privacy": {
    "class": "public_abstracted",
    "external_queries_redacted": true,
    "prohibited_external_terms": []
  }
}
```

Это standalone-вход: он сохраняет обычное планирование `exploratory_norm`, но его максимум — `standalone_exploratory_discovery_only`, а `promotion_eligible` всегда `false`.

Inbound-маршрут из портфеля добавляет контекст:

```json
{
  "doctrine_route_context": {
    "schema_version": "doctrine-route-context/1.1",
    "portfolio_id": "portfolio-id",
    "portfolio_artifact": {
      "artifact_id": "portfolio-artifact-id",
      "sha256": "sha256 exact portfolio bytes",
      "size_bytes": 12345
    },
    "issue_option_id": "issue-option-id",
    "trust_receipts": ["doctrine-trust-receipt/1.0 object"]
  }
}
```

Receipt — не строка и не самозаявленный hash. Полный машинный контракт находится в [doctrine-trust-receipt-1.0.schema.json](schemas/doctrine-trust-receipt-1.0.schema.json). Signed claims связывают роль receipt, `matter_id`, canonical request без trust-material, issue option, точные portfolio/artifact hashes и sizes, evidence role, `as_of_date`, corpus generation/manifest, coverage report, reviewed query plan, hypothesis set, freshness policy и revocation-registry generation. Скрипт пересчитывает `signed_claims_sha256` и canonical hash всего receipt.

Эта структурная проверка не аутентифицирует подпись. Pass может выдать только защищённый verifier по [doctrine-verifier-attestation-1.0.schema.json](schemas/doctrine-verifier-attestation-1.0.schema.json): он обязан проверить trusted issuer/key, Ed25519 signature, exact bytes, scope, freshness, revocation, corpus/coverage и query-plan bindings, а attestation должна прийти через доверенный host channel, не из request. Текущая версия скилла такого verifier не имеет; поэтому любой conditional route остаётся `blocked`, `promotion_eligible=false`, `maximum_permitted_claim=candidate_only_untrusted_declarations`. Выходной контракт: [doctrine-route-1.1.schema.json](schemas/doctrine-route-1.1.schema.json).

`case_scoped` дополнительно требует непустые `norms[].version_date`, списки `judicial_meanings`, `mechanisms`, `consequences` и `application_evidence_refs`. Каждая application-ссылка — объект с `evidence_id`, exact `sha256`, `size_bytes`, `provenance=official_application_record` и `trust_receipt`. Даже идеально сформированный request-carried receipt не закрывает gate без защищённого verifier. Не помещай тексты непубличных актов в request.

`hypothesis_verification` требует непустые `hypotheses_under_test`, объектные `fulltext_source_refs` с exact bytes, `provenance=lawful_fulltext_artifact` и role-bound trust receipt, а также adverse receipt с corpus/coverage/query-plan и hypothesis bindings. `adverse_search_required=true` и строка `adverse_search_status=pass` остаются только декларациями и без защищённой проверки недостаточны.
Во всех trust receipt `signed_claims.receipt_role` обязан быть строкой; неправильный тип блокируется
структурной проверкой до role-specific ветвления.

Внешний поиск разрешён только при `privacy.class=public_abstracted` либо `public_norm_profile` и `privacy.external_queries_redacted=true`. Флаг redacted не делает частные данные публичными: PII-gate отдельно блокирует типичные ФИО, контакты, идентификаторы, номера дел и реквизиты. Элементы query-полей должны быть непустыми строками; объектные формы допустимы только для явно описанных публичных судебных формул, гипотез и локальных ссылок на evidence.
При внешнем поиске `privacy.class` должен быть строкой; контейнеры и другие значения неправильного типа блокируются до проверки допустимого enum.

Для `case_scoped` и `hypothesis_verification` сетевой запуск требует точного `--approved-query-plan-hash` после человеческого просмотра `query-plan.json`. `search-run-config.json` фиксирует выбранных провайдеров, query IDs и границы выдачи; его hash обязан совпадать с `coverage-report.json`.

## Артефакты workspace

```text
request.snapshot.json
route-decision.json
norm-problem-profile.json
provider-capabilities.snapshot.json
provider-routing.json
query-plan.json
search-run-config.json
search-log.jsonl
source-ledger.jsonl
problem-candidates.json
coverage-report.json
qa-report.json
acquisition-queue.json
```

Скрипт первой версии создаёт поисковые и библиографические артефакты. Человек или вызывающий агент после чтения полного текста добавляет `propositions.jsonl`, `controversy-map.json`, `defect-candidates.json` и `hypothesis-handoff.json`.

`validate` обязан завершаться структурированным `status=fail`, если присутствующий workspace-артефакт не разбирается как строгий JSON/JSONL (включая UTF-8-безопасные строки и конечные числа) или имеет недопустимый контейнер/тип в проверяемом поле. Такой сбой не должен превращаться в traceback или оставлять старый `qa-report.json` со статусом `pass`; это защитный parse/type gate, а не полная JSON Schema-проверка всех необязательных полей. Команды `search` и `rerank` блокируют повреждённые артефакты, которые используют на preflight (связанный план, снимок запроса, ledger или coverage), с кодом выхода 2 до сетевого запроса или изменения результатов.

При `--offline-fixtures` синтаксически повреждённый или не кодируемый fixture — это ошибка конкретного провайдера (`OFFLINE_FIXTURE_INVALID`): она записывается в `search-log.jsonl`, не считается успешным ответом и оставляет `bounded_search_complete=false`. Автоматического перехода к сети или к запасному fixture после обнаружения повреждённого файла нет.

Все CLI-команды, принимающие `request.json`, используют тот же строгий parse gate: повреждённый, не UTF-8-кодируемый или содержащий не конечные числа вход блокируется контролируемой ошибкой `invalid JSON artifact: request.json` (код 2), без traceback. Для команд с `--workspace` такая ошибка также перезаписывает устаревший `qa-report.json` в `status=fail`.

При `load_request` поле `mode` проверяется как строковый enum. Массивы, объекты и другие контейнеры в этом поле блокируются обычной ошибкой валидации запроса, а не исключением проверки множества.
Переопределение `provider_access.<provider>.status` также должно быть строкой; контейнеры и другие значения неправильного типа блокируются контролируемой ошибкой до построения маршрута провайдера.

## DoctrineSourceRecord

Обязательные поля после discovery:

- `source_id`, `source_family_id`;
- `title`, `authors`, `year`, `publication_type`, `venue`;
- DOI/EDN/ISBN/ISSN, если доступны;
- `discovered_by`, `query_ids`, landing/full-text URLs;
- `access_status`, `license_status`;
- `verification_status`;
- `problem_labels` только как эвристические discovery labels;
- компоненты `reading_priority`, не являющиеся оценкой авторитетности.

В `source-ledger.jsonl` `verification_status` обязан быть строкой; для сетевых metadata-записей
валидатор принимает только `metadata_only` или `abstract_checked`, не преобразуя контейнеры или
другие типы в строку.
Если поле `access_status` присутствует, оно также обязано быть строкой: неправильный тип не должен
управлять очередью доступа и приводит к ошибке QA.

При полном чтении добавь:

- SHA-256 исходного файла и извлечённого текста;
- редакцию нормы, фактически обсуждаемую автором;
- страницы/разделы;
- библиографию проверенной версии;
- связь с препринтом, репозиторной и журнальной версиями.

## DoctrineProposition

```json
{
  "proposition_id": "dp-...",
  "source_id": "src-...",
  "page_locator": "с. 10–11",
  "quote_window": "короткий проверенный фрагмент",
  "faithful_paraphrase": "узкий пересказ",
  "claim_type": "current_law_interpretation",
  "function": "identifies_boundary_problem",
  "norm_relation": "относится к условию или элементу нормы",
  "relation": "supports",
  "limits": ["предел применимости"],
  "does_not_prove": ["применение нормы в деле", "неконституционность"],
  "verification_status": "page_verified"
}
```

Допустимые `claim_type`: `current_law_interpretation`, `judicial_practice_description`, `normative_critique`, `empirical`, `historical`, `comparative`, `de_lege_ferenda`.

Допустимые `relation`: `supports`, `weakens`, `distinguishes`, `blocks`, `context_only`.

## NormativeDefectCandidate

Фиксируй:

- точные норму и редакцию;
- применённый судебный смысл либо статус `not_case_scoped`;
- решающий узел регулирования;
- научный спор и связанные proposition IDs;
- локализацию: `text`, `scope_boundary`, `exception`, `interaction`, `procedure`, `evidence`, `consequence`, `transition`, `remedy`, `judicial_meaning`, `facts_only`, `unknown`;
- причинную цепочку;
- альтернативное обычное толкование;
- сильнейшее альтернативное объяснение;
- falsifier;
- незакрытые официальные проверки;
- статус `candidate_only`, `conditional` или `rejected`.

## ConstitutionalHypothesisCard

Карточка не является готовым тезисом жалобы. Она содержит:

- `defect_candidate_id`;
- норму, редакцию и evidence IDs применения;
- supporting/adverse proposition IDs;
- возможный конституционный мост;
- вред и outcome causation;
- official anchors, которые ещё требуется найти;
- competence и anti-fourth-instance risks;
- узкий возможный remedy;
- falsifier и gaps;
- статус `candidate`, `conditional`, `rejected` или `ready_for_official_validation`.

## CoverageReport

Разделяй:

- `bounded_search_complete` — выбранные запросы и доступные адаптеры завершились без ошибок;
- `coverage_complete` — полнота всей релевантной доктрины; для открытого федеративного поиска по умолчанию `false`;
- выполненные и пропущенные provider-классы;
- metadata/abstract/full-text/page-verified counts;
- глубину выдачи и citation chaining;
- adverse-pass;
- временное покрытие;
- недоступные платные источники и manual follow-ups.

Даже bounded saturation не разрешает формулировку «в научной литературе отсутствует позиция».
