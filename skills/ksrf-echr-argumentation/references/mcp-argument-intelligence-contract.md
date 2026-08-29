# HUDOC MCP: контракт аргументационного поиска

Этот контракт связывает локальный HUDOC connector с исследованием жалобы в КС
РФ. Он описывает discovery и проверку источника, но не создаёт позицию ЕСПЧ,
российское право или разрешение на drafting reuse.

## Содержание

- [Connector-first маршрут](#connector-first-маршрут)
- [ECHRArgumentPacket](#echrargumentpacket)
- [Разделение actor lanes](#разделение-actor-lanes)
- [Аргументационные функции](#аргументационные-функции)
- [Lifecycle и перенос в КС РФ](#lifecycle-и-перенос-в-кс-рф)
- [KSRF transfer boundary](#ksrf-transfer-boundary)

## Connector-first маршрут

1. Если доступен skill `hudoc-echr-connector`, сначала вызови
   `mcp__hudoc_echr__hudoc_stats`. Сохрани generation, версии knowledge,
   research и privacy, `current/searchable/stale` counters, FTS/privacy gates,
   `semantic_discovery_status` и blockers.
2. При неполном knowledge cycle, ненулевом stale/error либо непройденном
   FTS/privacy gate разрешён только bounded FTS discovery через
   `mcp__hudoc_echr__hudoc_search_practice`. В ответе укажи фактическое
   покрытие. Пустая выдача означает только «не найдено в текущей проекции».
3. Dense/hybrid и поиск похожих актов допустимы только при
   `semantic_discovery_status=ready_unpromoted` и полном generation-bound
   audit. Semantic profile, similarity и RRF rank не являются цитатой или
   правовым выводом.
4. Ищи раздельно по `source_actor`, `source_function` и `source_role`.
   Нефильтрованный paragraph hit остаётся candidate до sentence-level
   attribution.
5. Перед точной цитатой обязательно вызови
   `mcp__hudoc_echr__hudoc_get_case_details` и гидратируй весь нужный фрагмент.
   Snippet из поисковой выдачи не цитируй как контекст акта.

Если connector недоступен, используй version-checked CLI из
`local-hudoc-knowledge-base.md` и прямо отметь отсутствие MCP. Не имитируй
connector output и не трактуй локальную ошибку доступа как отсутствие практики.

## ECHRArgumentPacket

На каждый проверяемый фрагмент создай отдельный пакет:

```text
packet_id:
itemid:
matter_key:
application_number:
decision_date:
document_family:
language:
official_hudoc_url:
source_sha256:
artifact_sha256:
page:
paragraph:
sentence_or_char_locator:
exact_text:
source_actor:
source_function:
source_role:
source_form:
speaker_verified:
court_treatment:
court_treatment_response_packet_id:
court_treatment_response_locator:
court_treatment_response_exact_text:
court_treatment_response_source_sha256:
court_treatment_review_ref:
argument_function:
relation:
test_family_and_step:
result_class:  # applicant_pleading_move|court_reasoning_method|court_authority|case_example_only
method_signature:
authority_status:
substantive_rule_changed:
substantive_russian_rule_changed:
temporal_effect:
currentness_review:
adverse_and_distinguishing:
transfer_limit:
russian_official_anchor_status:
russian_official_anchor_ref:
russian_official_anchor_url:
russian_official_anchor_requisites:
russian_official_anchor_locator:
russian_official_anchor_checked_at:
ksrf_transfer_packet_id:
lifecycle_stage:
reuse_target:
promotion_eligible:
human_approval_status:
human_approval_record_id:
human_approval_input_sha256:
human_approval_scope:
human_approval_at:
held_out_binding:
  report_id:
  manifest_sha256:
  input_sha256:
  run_sha256:
  report_sha256:
  report_envelope_sha256:
skill_approval_bundle:  # только для skill_update_approved
  promotion_contract_version:
  approval_subject_sha256:
  bundle_sha256:
  trusted_registry_binding:
    registry_id:
    registry_version:
    snapshot_sha256:
    snapshot_artifact_sha256:
    valid_from:
    valid_until:
  base_manifest_artifact_sha256:
  base_tree_sha256:
  base_skill_blob_sha256:
  base_file_artifact_sha256_by_path:
  diff_artifact_sha256:
  fixture_manifest_artifact_sha256:
  fixture_artifact_sha256_by_id:
  validation_report_artifact_sha256:
  reviewer_attestation_artifact_sha256:
  reviewer_human_id:
  approver_attestation_artifact_sha256:
  approver_human_id:
blockers:
```

Для точной цитаты обязательны `itemid`, application number/date, document
family, официальный HUDOC URL, source/artifact SHA, page либо paragraph,
sentence/char locator и `exact_text`. Неполный набор даёт
`unhydrated_quote_candidate`, а не цитату.

## Разделение actor lanes

- `applicant`, `government` и `third_party` — submissions. Для них обязательны
  `source_form=reproduced_in_public_act`, фактический reproduction mode,
  `original_application_in_source=false` и
  `complaint_completeness=unknown_from_public_act`.
- `court_majority` — только sentence-level reasoning/outcome большинства.
  Наличие текста стороны в том же параграфе не меняет actor.
- `separate_opinion` — research signal, counterargument или adverse lead. Оно не
  является reasoning/holding большинства.
- `editorial`, `summary`, `press` и `communicated_case` помогают discovery, но
  не голосуют как итоговая мотивировка.

Для submission `court_treatment` имеет фактическое значение
`accepted|rejected|qualified|not_addressed|unclear`. Значения
`accepted|rejected|qualified` допустимы только при ссылке на отдельный hydrated
`court_majority` response packet: обязательны его packet id, locator, exact text
и source SHA. `not_addressed` требует отдельного review record с зафиксированным
охватом акта; при неполной проверке либо отсутствии доказуемого ответа используй
`unclear`, а не вывод из исхода дела. Submission packet и majority-response
packet никогда не склеиваются в один actor lane.

## Аргументационные функции

Допустимые method-only функции — это вопросы и структура проверки, а не нормы:

- actor-response triangle: довод стороны -> возражение -> treatment большинства;
- norm/meaning -> domestic application/causation -> right -> defect/harm ->
  test/alternative/safeguards/remedy;
- positive obligation: `trigger -> scope -> content -> breach`;
- раздельные `scope -> interference -> justification`;
- less-restrictive alternative, procedural safeguards и remedy как отдельные
  поля;
- adverse/currentness/temporal/distinguishing pass;
- separate opinion как research signal;
- различение judgment/decision/communicated/summary.

Эти функции можно применять как `research_checklist_only`, но они не доказывают,
что Суд установил соответствующий универсальный тест.

## Lifecycle и перенос в КС РФ

`ECHRArgumentPacket` проходит только последовательность:

`candidate -> verified_case_finding -> cross_case_reusable -> skill_update_approved`.

Raw assertion, vector hit, cluster label и единичный убедительный фрагмент не
пропускают ни одну стадию. Для Court-authority transfer нужны проверенная
мотивировка большинства, минимум два независимых matter для reusable pattern,
adverse/currentness/temporal review, transfer limit, действующий российский
официальный конституционный anchor и отдельное human approval.

Статус российского anchor не самодостаточен: для drafting reuse обязательны
его стабильный evidence ref, официальный URL, реквизиты, locator и дата
проверки, а также ссылка на связанный `KSRFTransferPacket`. Аналогично
`cross_case_reusable` и `skill_update_approved` нельзя выставить одним enum.
Immutable lifecycle approval record с id/scope/timestamp и SHA-256 input bundle
необходим для `cross_case_reusable`, но сам по себе недостаточен для изменения
скилла. `skill_update_approved` дополнительно требует типизированный
`skill_approval_bundle` из пакета выше: exact bytes и content-addressed SHA
base tree/files, diff, fixtures, passing report, frozen held-out, immutable
public trust-registry snapshot и две attestations разных доверенных людей.
Несовпадение bytes, identity, key provenance, subject либо scope возвращает
пакет в `blocked`.

Приём заявителя веди отдельно как `applicant_pleading_move`. Method-only reuse
требует того же приёма минимум в двух независимых matters, точного публичного
воспроизведения, зафиксированного court treatment, adverse/currentness/temporal
и transfer review и отдельного human approval. Исключение из российского anchor
gate действует только при одновременных:

- `authority_status=non_authority`;
- `reuse_target=research_checklist_only`;
- `substantive_rule_changed=false`.

Отсутствие любого значения возвращает полный Russian-anchor gate. Ни один
method-only приём не может менять substantive drafting rule.

Метод рассуждения большинства веди отдельно как `court_reasoning_method`, а не
как `court_authority`. Для межделового reuse нужны exact majority locators как
минимум в двух независимых matters, совпадающий method signature, passing
held-out, adverse/currentness/temporal/transfer review и отдельное human
approval. Разрешённая классификация фиксирована:

- `authority_status=comparative_authority`;
- `reuse_target=research_checklist_or_argument_structure_only`;
- `substantive_rule_changed=false`;
- `substantive_russian_rule_changed=false`.

Такой объект может добавить вопрос, порядок test steps, burden, alternative,
safeguard или remedy в исследовательский checklist. Он не создаёт российскую
норму, официальный российский anchor, универсальный holding ЕСПЧ или готовое
правило для жалобы.

Для `skill_update_approved` generic approval record, одной строки с именем,
одного input-bundle SHA или одного `diff_sha256` недостаточно.
Approval bundle обязан хранить exact bytes и SHA базового skill manifest, diff,
fixture manifest и passing validation report; отчёт должен быть связан с теми
же base/diff/fixture SHA и frozen held-out. Reviewer и approver подтверждают
один approval-subject разными immutable attestations и не могут быть одним
лицом. Несовпадение любых bytes, identity либо scope возвращает пакет в
`blocked`.

## KSRF transfer boundary

В `KSRFTransferPacket` отдельно свяжи оспариваемую российскую норму или
обязательный судебный смысл, доказанное применение и причинность, право с
официальным российским anchor, механизм дефекта и индивидуальный вред, test
steps, альтернативу, safeguards/remedy, fourth-instance boundary и
adverse/distinguishing findings. Неизвестное остаётся `unknown`.

Applicant и separate-opinion packets могут породить вопрос, counterargument или
research task. Для filing sentence comparative support даёт только проверенный
majority packet в пределах holding, и он всё равно не заменяет российский
официальный anchor. Любой пакет без required gate имеет
`promotion_eligible=false` и `drafting_reuse_status=blocked`.
