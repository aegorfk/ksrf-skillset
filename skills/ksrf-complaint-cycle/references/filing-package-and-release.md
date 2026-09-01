# Реальный filing package и release gate

## Structured complaint

Рабочая structured-complaint модель `1.1` содержит обязательные разделы жалобы, `matter_id`, `draft_id`, source/version bindings, norm passport IDs, plural selected issue option IDs, approvals, formal check и `SentenceEvidenceMap`. Filing-package manifest `1.1` всегда несёт relief projections, массив receipts и nullable host-authoritative index receipt: в диагностическом `blocked` manifest допустимы `unbound`, пустой receipt-массив и `null` index, но любой ready-статус требует только `bound`-строки, current receipts версии `1.1.0` и current index. Manifest `1.0` остаётся только историческим JSON и должен быть пересобран перед новым release approval. Singular `issue_option_id` остаётся только диагностическим alias и не создаёт membership для нескольких линий.

Для каждого filing-significant предложения запиши:

- stable sentence ID;
- роль: факт, мотив суда, текст нормы, holding, application finding, practice claim, adverse authority, remedy;
- evidence IDs и locators;
- support status;
- предел формулировки.

Для роли `requested_remedy` дополнительно обязательны same-claim `claim_id`, `issue_option_id`, `norm_passport_id`, canonical unique `application_record_ids` и `relief_binding_sha256`. Любая строка в разделе `requested_remedy` нормализуется именно с этой ролью: caller не может превратить просьбу в `narrative`. Legacy-строка сериализуется с `relief_binding_status=unbound`, остаётся редактируемым черновиком и не проходит release gate; полная строка получает `bound` только из реально сохранённых binding-полей.

Перед render, release, approval и повторной проверкой manifest host-attested `ReliefEvidenceBindingAuthority` заново возвращает exact issue/application/passport/source snapshots, content-bound trusted gate receipts и полный current index строк просительной части из реестра draft. Runtime пересчитывает fingerprints и проверяет одну claim/norm/edition graph; payload-флаги `verified`, `passed` или `filing_ready` не заменяют authority. Manifest сохраняет проверенные relief-binding receipts и index receipt в release basis.

### Контракт `ReliefEvidenceBindingAuthority`

Line resolver получает один request с `matter_id`, `draft_id`, strict unique `sentence_id`, exact text/hash, `claim_id`, `issue_option_id`, `norm_passport_id`, canonical application/evidence IDs и `relief_binding_sha256`. Он получает deep copy: попытка адаптера изменить request блокирует выпуск. Отдельный index resolver получает только `{schema_version, matter_id, draft_id}` и возвращает полный независимый от manifest реестр current remedy-линий; отсутствие любого обязательного элемента блокирует строку или весь индекс.

| Блок resolution | Обязательное содержание | Локальная перепроверка |
|---|---|---|
| `issue_option` + `issue_gate_receipt` | Current `IssueCandidate` schema `1.0.0`; `passed`; content fingerprint; полный `approval_requests`; exact-key `trusted_approval_ids` | `issue_approval_requests(candidate)` должен полностью совпасть, включая `adverse_authority`, `remedy`, `selection`, условный `anti_fourth_instance` и все asserted `practice:*` |
| `norm_version_passport` + `norm_version_gate_receipt` | Current passport schema `1.0.0`; `passed`; content fingerprint; полный `approval_request`; trusted approval ID | Полное равенство с `norm_version_review_approval_request(passport)` и наличие выбранной edition; все nested source/timepoint/provider IDs проверяются до coercive helpers |
| `application_records` + receipt на каждый record | Exact record set schema `1.0.0`; `passed`; content fingerprint; полный application `approval_request`; trusted approval ID; preservation rule и его gate receipt | Raw record/span stages, IDs и locators — canonical strings; затем `assess_application_chain(records)`, полное равенство с `application_review_approval_request(...)`; preservation binding и request сверяются через `preservation_rule_review_approval_request(...)` |
| `claim_evidence` | Только current same-claim evidence: exact ID, claim, norm и edition, status, content SHA-256, verification revision/verifier/time, usable locator | Полная projection и её fingerprint входят в receipt `1.1.0`; изменение SHA, locator, verifier или времени при том же revision делает manifest stale |
| Верхний resolution | `status=verified` и exact `relief_binding_sha256` | Payload IDs/flags не повышают статус; resolver считается host trust boundary, но его graph и requests всё равно пересчитываются локально |
| `resolve_relief_evidence_binding_index` | Canonical sorted unique entries `{sentence_id, section_code=requested_remedy, role=requested_remedy, relief_binding_sha256}`, index SHA, authority revision и RFC3339 checked time | Точный set сравнивается с каждой текущей manifest projection; удалить, добавить или переименовать одну линию вместе с её receipt нельзя скрыть пересчётом manifest hash |

Host adapter должен получать receipts из действующих trusted ledgers/gates и remedy index из authoritative current draft registry, а не строить его из переданного manifest. Все nested graph IDs и locator kind/value должны уже быть canonical strings до deserialization; `str(...)`, trim или deduplication на trust boundary запрещены. Непустая произвольная строка fingerprint или caller-declared approval ID не соответствует этому контракту.

Unsupported или overclaimed sentence не проходит в release draft.

## Артефакты

Release pack содержит реальные:

- `constitutional-complaint.docx`;
- `constitutional-complaint.pdf`;
- опись приложений и включённые файлы/инструкции;
- sentence evidence map;
- unresolved-risk register;
- `filing-package-manifest.json`;
- page previews/visual-review record;
- SHA-256 каждого файла.

План export job или строка `DOCX ready` без файла не является артефактом.

## Проверка DOCX/PDF

- обязательные разделы и headings;
- единая первая страница и стили;
- отсутствие placeholders;
- совпадение filing-significant текста после PDF conversion;
- page count и читаемость;
- clipping, overlap, blank unexpected pages, broken tables, orphan headings, margins и pagination;
- совпадение ссылок на приложения с описью;
- renderer и version в manifest.

Если LibreOffice, pypdf, pdftoppm или visual review недоступны, release остаётся blocked с точным remediation.

## Статусы

- `working_draft` — разрешены blockers/placeholders, не готово к выпуску.
- `blocked` — legal/evidence/operational/release gate не закрыт.
- `ready_for_expert_review` — файлы технически собраны, но human legal approval не завершён.
- `ready_for_human_signing_filing` — gates закрыты; остаются только внешние действия человека.

## Инвалидация

Изменение source hash/locator/verifier/time, NormVersionPassport, application record, issue selection, состава remedy index, sentence text, enclosure или formal-rule freshness отменяет прежний release approval и требует нового manifest.

Release approval связывается с fingerprint полного стабильного manifest: source/passport/issue bindings, approvals, formal check, sentence evidence map, hashes и metadata артефактов, опись, visual QA, blockers, `human_only_actions` и `filing_performed`. Исключаются только самохэши, approval projection и локальные пути. Approval должен существовать до проверки, иметь host attestation аутентифицированного reviewer и проходить повторную проверку binding, expiry и revocation по trusted clock. Caller-supplied reviewer, JSONL без проверяемой attestation, обычный TTY и самозаявленный verifier не повышают статус.

## Человеческая граница

Skill не применяет УКЭП, не платит пошлину, не отправляет пакет, не утверждает факт подачи. Финал — проверенный комплект и checklist для заявителя/представителя. Внешнее событие фиксируется только после фактического подтверждения человеком.
