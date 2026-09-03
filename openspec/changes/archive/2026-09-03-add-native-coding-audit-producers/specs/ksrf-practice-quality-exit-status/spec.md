## ADDED Requirements

### Requirement: Native coding-audit preparation is provenance-bound and atomic

The installed runtime MUST provide `quality coding-audit-prepare` to read one existing workspace and publish a new deterministic audit-input bundle only when the latest research plan is valid, frozen, and self-digesting; the ordinary screening frame, approved primary coding, and stored full texts map exactly by canonical chain/document identity; and every projected exact primary coding record validates against its identified full text. Each captured text MUST match the source row's store-normalized `text_sha256`, and `document_id` MUST equal `document-sha256:<text_sha256>`, so the derived candidate identity changes with text content. Multiple source rows for one chain/document identity MUST collapse to one audit candidate only when their full-text SHA-256 and recomputed screening matches are identical, and the closed audit row MUST preserve their sorted positive source IDs. Conflicting duplicates MUST fail. Candidate IDs MUST be derived as `audit-candidate-sha256:<sha256>` from the exact canonical object containing `schema_version`, frozen `plan_sha256`, `chain_id`, and content-addressed `document_id`.

The producer MUST require an absent destination under an existing real parent outside the source workspace, with containment checked by both resolved path and existing-directory identity so case aliases cannot bypass it; MUST stage all files in that parent and publish them with one atomic no-replace directory transition; MUST NOT overwrite or mutate source artifacts; and MUST leave neither a destination nor partial bundle after a pre-publication failure. A platform without an atomic no-replace primitive MUST fail closed. The bundle MUST contain the closed audit screening frame, exact primary records, frozen audit plan, non-substantive secondary-review queue, visibly pending secondary-coding templates, and a self-digesting manifest that binds source bytes, candidate/source-text identities, and every generated content file.

#### Scenario: Valid workspace becomes a reproducible bundle

- **WHEN** a workspace has one valid self-digesting frozen plan and exact screening, approved coding, and stored full-text coverage after safe identical-source collapse
- **THEN** the producer derives stable candidate IDs, rechecks every projected quote against the bound full text, and publishes the complete bundle in the absent output directory
- **AND** repeating preparation from identical source bytes at another absent path produces byte-identical content files and manifest
- **AND** no network, legal conclusion, approval, adjudication, or filing occurs

#### Scenario: Identity or full-text binding is not exact

- **WHEN** a screening, primary, or source record is missing, duplicated, extra, noncanonical, ambiguously mapped, has stale text/document hashes, is bound to another candidate, or any primary or alternative-ground quote does not occur in the bound full text
- **THEN** the command returns input error code `2` with an actionable diagnostic
- **AND** it publishes no destination and does not alter the workspace

#### Scenario: Plan or destination is unsafe

- **WHEN** the latest plan is absent, unfrozen, invalid, or has a mismatched digest, or the destination exists, is inside the source workspace through its ordinary path or a filesystem alias, has an unsafe parent, races into existence, or cannot be published with atomic no-replace semantics
- **THEN** the command returns code `2` without a partial bundle or overwrite

#### Scenario: Generated secondary work remains pending

- **WHEN** the producer creates the independent-review queue and secondary-coding templates
- **THEN** the queue exposes identity and content digests but no primary substantive coding answer
- **AND** every template is marked `human_review=pending`, `quote_verified=false`, and `full_text_reviewed=false`
- **AND** supplying an unchanged generated template to coding reliability cannot satisfy the independent-review gate

## MODIFIED Requirements

### Requirement: Coding reliability uses a closed content-bound audit

The system MUST validate the exact frozen audit-plan field set and self-digest, authoritative primary and secondary coding-record contracts, stable canonical candidate identities, content hashes, independent reviewer identities, and closed adjudication records. Every coding-reliability JSON and JSONL input MUST use strict UTF-8 JSON with unique keys at every nesting level and MUST reject `NaN` and infinities before evaluating the gate. Invalid records MUST remain visible in the corresponding `invalid_*` and `unresolved_candidate_ids` collections and MUST prevent completion.

The installed guidance MUST publish the exact `audit-decisions.jsonl` and `adjudications.jsonl` object shapes. It MUST identify `quality coding-audit-prepare` outputs as the first-party screening, primary, plan, queue, and pending-template inputs while stating that completed secondary decisions and adjudications remain separately human-authored contract-specific inputs. Compatible exact expert/manual inputs MUST remain supported. All valid record hashes MUST use SHA-256 over UTF-8 JSON serialized with sorted keys, compact separators, `ensure_ascii=false`, and `allow_nan=false`; collection digests MUST sort records by their canonical record digest before hashing the canonical array. A syntactically escaped lone surrogate that cannot be canonically encoded MUST remain an invalid visible record and MAY use a deterministic escaped-ASCII fingerprint only for diagnostics; that fingerprint MUST NOT validate a content hash or make the record eligible.

The audit plan MUST select the general and false-exclusion samples by independent canonical SHA-256 ranks. `sample_size` and `exclusion_sample_size` MUST be upper bounds when the corresponding frame is smaller, the two selected lists MAY overlap, and `required_candidate_ids` MUST equal their sorted set union.

#### Scenario: Secondary coding is bound to the audited candidate

- **WHEN** an outer audit record selects one required candidate but the nested content-bound secondary coding names another candidate
- **THEN** reliability records the required candidate in `invalid_binding_candidate_ids`, `invalid_audit_record_ids`, and `unresolved_candidate_ids`
- **AND** returns `complete=false` and process code `3`

#### Scenario: Equally incomplete records cannot simulate agreement

- **WHEN** primary or secondary coding omits a field required by the authoritative coding-record contract
- **THEN** the corresponding candidate is recorded as invalid and unresolved
- **AND** matching absent values do not count as agreement

#### Scenario: Missing primary coding remains visible

- **WHEN** a canonical candidate appears in the frozen screening frame but has no primary coding record
- **THEN** the plan records that candidate in `invalid_primary_record_ids`
- **AND** reliability cannot become complete even if no secondary disagreement is visible

#### Scenario: Unicode identity must be canonical and visible

- **WHEN** an identifier, coder, adjudicator, or mandatory coding text contains a Unicode format/control/surrogate payload that is not permitted visible multiline text
- **THEN** the record is invalid and remains visible in the applicable diagnostic collection
- **AND** ordinary canonical visible Unicode text is preserved rather than ASCII-folded
- **AND** an escaped lone surrogate cannot turn the result into an input exception or completed audit

#### Scenario: Adjudication is exact and chronological

- **WHEN** an adjudication contains an extra or unaudited resolved field, mismatched coding hashes, an orphan candidate, a reviewer equivalent to a coder, a reduced timestamp, or a future timestamp
- **THEN** the candidate remains unresolved
- **AND** reliability cannot become complete

#### Scenario: Sample maxima can overlap

- **WHEN** a false-exclusion candidate is selected by both independent ranks or either eligible frame is smaller than its configured maximum
- **THEN** both sample lists preserve their independently selected IDs
- **AND** required candidates are their sorted set union without requiring disjointness or exact configured lengths

#### Scenario: Ambiguous JSON cannot pass the human-review gate

- **WHEN** the audit plan, primary coding, audit decision, or adjudication contains a repeated key at any nesting level or a non-finite JSON constant
- **THEN** coding reliability returns input error code `2` before assessing agreement
- **AND** it emits no completed reliability result
