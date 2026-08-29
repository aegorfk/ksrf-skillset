## ADDED Requirements

### Requirement: KSRF skills SHALL route HUDOC discovery through a coverage-aware connector

Перед поиском скилл SHALL получать статус локальной проекции. FTS MAY использоваться при неполном покрытии только с явными current/searchable/stale counters. Dense/hybrid SHALL использоваться только после полного generation-bound gate.

#### Scenario: Knowledge cycle incomplete
- **WHEN** `inventory_cycle_complete=false` либо FTS/privacy gate не пройден
- **THEN** поиск ограничивается bounded FTS discovery
- **AND** пустая выдача не описывается как отсутствие практики ЕСПЧ
- **AND** результат остаётся `promotion_eligible=false`

### Requirement: Every exact quotation SHALL be hydrated and actor-separated

Точная цитата SHALL происходить из карточки акта и включать официальный HUDOC URL, itemid, application number/date, document family, locator и SHA. Actor/function/form/treatment SHALL быть сохранены раздельно. `accepted|rejected|qualified` SHALL ссылаться на отдельный hydrated majority-response packet с locator, exact text и source SHA. `not_addressed` SHALL иметь review ref с охватом акта; иначе treatment SHALL быть `unclear`.

#### Scenario: Applicant wording reproduced in a judgment
- **WHEN** фрагмент атрибутирован заявителю
- **THEN** он SHALL маркироваться как `source_form=reproduced_in_public_act`
- **AND** SHALL NOT называться original application либо holding Суда

#### Scenario: Separate opinion contains a strong test
- **WHEN** тест найден в отдельном мнении судьи
- **THEN** он SHALL использоваться только как research signal/counterargument
- **AND** SHALL NOT маркироваться как reasoning большинства

### Requirement: ECHR material SHALL transfer through a typed constitutional-question packet

`ECHRArgumentPacket` SHALL связывать source identity, exact provenance, actor/function, treatment, argument function, `result_class`, `method_signature`, authority/substantive flags, adverse/currentness/temporal limits и российский официальный конституционный anchor. Российский anchor SHALL включать evidence ref, официальный URL, реквизиты, locator, checked-at и связь с `KSRFTransferPacket`; один status SHALL NOT считаться доказательством. Для reusable/skill lifecycle пакет SHALL также нести frozen held-out binding, а для `skill_update_approved` — typed exact-byte approval bundle и раздельные reviewer/approver attestations.

#### Scenario: Comparative standard lacks a Russian anchor
- **WHEN** фрагмент ЕСПЧ проверен, но официальный российский конституционный anchor отсутствует
- **THEN** пакет MAY поддерживать исследовательскую гипотезу
- **AND** drafting reuse SHALL быть blocked

### Requirement: Applicant techniques SHALL use a separate method-only lifecycle

Приём заявителя SHALL NOT становиться содержательным правилом. Method-only reuse SHALL требовать повторения минимум в двух независимых matters, точного публичного воспроизведения, court treatment, adverse/currentness/temporal/transfer review и отдельного human approval. Human approval SHALL иметь immutable record id, scope, timestamp и SHA-256 одобренного input bundle; lifecycle enum без этой привязки SHALL fail closed.

#### Scenario: One persuasive applicant submission
- **WHEN** найден только один case-specific фрагмент
- **THEN** он SHALL остаться `verified_case_finding` либо candidate
- **AND** SHALL NOT обновлять substantive drafting rule

### Requirement: Majority reasoning methods SHALL remain separate from Court authority

Повторяемая архитектура рассуждения большинства MAY стать `court_reasoning_method` только при наличии exact majority locators минимум в двух независимых matters, passing held-out, adverse/currentness/temporal/transfer review и отдельного human approval. Такой объект SHALL сохранять `authority_status=comparative_authority`, `reuse_target=research_checklist_or_argument_structure_only`, `substantive_rule_changed=false` и `substantive_russian_rule_changed=false`. Он SHALL NOT заполнять российскую норму, официальный российский anchor либо готовое материально-правовое правило.

#### Scenario: Similar majority reasoning appears in two cases
- **WHEN** два независимых дела используют сопоставимую последовательность проверки
- **THEN** она MAY расширить research checklist или структуру аргумента после всех method gates
- **AND** SHALL NOT называться российским правилом либо универсальным holding ЕСПЧ

### Requirement: Skill approval SHALL bind exact reviewed bytes

`skill_update_approved` SHALL требовать content-addressed base skill tree и exact base-file bytes, exact diff bytes, fixture manifest и exact fixture bytes, passing validation report, frozen held-out binding, immutable public trust-registry snapshot/key provenance и разные immutable reviewer/approver attestations по одному approval subject. Validation report SHALL быть связан с теми же base/diff/fixture/held-out/registry SHA. Generic lifecycle record, строковые имена, enum approval, один input SHA либо один синтаксически валидный digest SHALL NOT разрешать обновление.

#### Scenario: Approval names a diff digest but omits its bytes
- **WHEN** lifecycle payload содержит reviewer name и `diff_sha256`, но exact-byte artifact chain отсутствует либо не совпадает
- **THEN** skill transition SHALL fail closed
- **AND** canonical/global skill SHALL NOT изменяться

### Requirement: Local resolvers SHALL bind current extraction and privacy versions

Resolver SHALL принимать только `hudoc-knowledge-indexer-v3.8`, `hudoc-research-extractive-v7` и `hudoc-knowledge-privacy-sanitizer-v2`, а также SHALL сообщать partial coverage и generation.

#### Scenario: Stale privacy projection is present
- **WHEN** строка принадлежит старой или отсутствующей privacy версии
- **THEN** она SHALL NOT считаться текущим безопасным discovery result

### Requirement: ECHR-specific QA SHALL fail closed

QA SHALL блокировать exact quote без hydration, applicant/separate-opinion text как Court holding, отсутствующий adverse/currentness review и filing sentence без российского официального anchor.

#### Scenario: Draft cites an unhydrated applicant snippet as a Court holding
- **WHEN** источник не имеет case-detail locator либо actor lane не совпадает с заявленной ролью
- **THEN** ECHR QA SHALL вернуть blocking defect
- **AND** SHALL потребовать гидратацию, исправление attribution и российский официальный anchor до drafting reuse

#### Scenario: Forged treatment or approval status
- **WHEN** пакет заявляет `court_treatment=accepted`, verified Russian anchor либо `skill_update_approved` без соответствующего response/anchor/approval evidence ref
- **THEN** ECHR QA SHALL вернуть blocking defect
- **AND** SHALL NOT разрешать drafting reuse или обновление скилла
