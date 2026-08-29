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

`case_scoped` дополнительно требует непустые `norms[].version_date`, списки `judicial_meanings`, `mechanisms`, `consequences` и `application_evidence_refs` со ссылками на отдельные evidence-артефакты применения. Строка вместо списка отклоняется. Не помещай тексты непубличных актов в этот request.

`hypothesis_verification` требует непустые `hypotheses_under_test`, `fulltext_source_refs` и `adverse_search_required=true`. Эти поля задают предмет проверки, но сами не подтверждают гипотезу или полный текст.

Внешний поиск разрешён только при `privacy.class=public_abstracted` либо `public_norm_profile` и `privacy.external_queries_redacted=true`. Флаг redacted не делает частные данные публичными: PII-gate отдельно блокирует типичные ФИО, контакты, идентификаторы, номера дел и реквизиты. Элементы query-полей должны быть непустыми строками; объектные формы допустимы только для явно описанных публичных судебных формул, гипотез и локальных ссылок на evidence.

Для `case_scoped` и `hypothesis_verification` сетевой запуск требует точного `--approved-query-plan-hash` после человеческого просмотра `query-plan.json`. `search-run-config.json` фиксирует выбранных провайдеров, query IDs и границы выдачи; его hash обязан совпадать с `coverage-report.json`.

## Артефакты workspace

```text
request.snapshot.json
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
