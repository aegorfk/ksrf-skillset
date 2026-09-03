# ksrf-practice-quality-exit-status Specification

## Purpose
TBD - created by archiving change align-practice-quality-exit-status. Update Purpose after archive.
## Requirements
### Requirement: Filing-significant quality gates fail closed at process level

The installed `judicial_meaning.py quality coding-reliability` and `judicial_meaning.py quality prefiling-refresh` commands MUST return process success only when the final assessment contains top-level Boolean `complete=true`. They MUST return code `3` for a valid assessment with `complete=false` or any non-Boolean/missing completion signal, and MUST retain code `2` for argument, input, envelope, or output-I/O errors.

#### Scenario: Completed bounded assessment succeeds

- **WHEN** either quality command produces exact top-level `complete=true`
- **THEN** it returns code `0`
- **AND** emits the full JSON result on stdout
- **AND** code `0` does not claim corpus completeness, legal approval, or filing authority

#### Scenario: Incomplete or stale assessment blocks automation

- **WHEN** a structurally consumable assessment produces `complete=false`
- **THEN** the command returns code `3`
- **AND** emits the full actionable JSON on stdout with empty stderr
- **AND** writes the identical result first when `--output` is supplied
- **AND** performs no implicit network access, review, filing, approval, or remediation

#### Scenario: Invalid input remains distinct

- **WHEN** required arguments, a supplied file, an exact envelope, or output writing violates the CLI contract
- **THEN** the command returns code `2` with a diagnostic on stderr
- **AND** does not emit or persist a partial success report

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

### Requirement: Refresh planning starts from explicit coverage requirements

`cache refresh-plan` MUST require a non-empty JSON/JSONL collection of coverage requirement objects. Each object MUST contain only one or more of `court_id`, `period_id`, `enumerator_id`, and `source_role`; every value MUST be a non-empty canonical identifier, and `source_role` MUST be supported by the public-corpus contract. The producer MUST deduplicate and sort requirements and MUST emit a gap only for the exact scope of a declared requirement that lacks a matching official role and URL at `full_text_extracted` or later with an intact snapshot and, for `indexed` or later, intact indexed text.

#### Scenario: Declared scope is preserved

- **WHEN** the caller supplies valid coverage requirements
- **THEN** the refresh plan preserves the normalized unique requirements
- **AND** every `coverage_gap` scope is an exact member of that requirement set
- **AND** an unobserved segment is disclosed rather than counted as zero practice

#### Scenario: Lossy or invented coverage fails closed

- **WHEN** requirements are empty, malformed, contain unsupported dimensions/roles, noncanonical values, or control/format characters
- **THEN** the producer returns input error code `2` without a plan
- **AND WHEN** a consumer plan contains a gap outside its declared requirements
- **THEN** prefiling returns `complete=false` and code `3`

#### Scenario: Successful sibling does not hide blocked scope member

- **WHEN** one funnel chain in a declared scope reaches an intact late official stage but another matching chain is blocked, early, discovery-only, or corrupt
- **THEN** the requirement remains a disclosed `coverage_gap`
- **AND** the successful sibling cannot make the scope observed by itself

### Requirement: Corpus evidence binds material observation relationships

The corpus evidence digest MUST include the sorted distinct set of `seed_id`/`snapshot_id` pairs represented by observations. Adding a new pair, including a binding to another seed or source role, MUST be material. Re-fetch-only observation metadata for an already represented pair MAY remain outside the evidence digest so identical bytes from the same seed are not represented as new evidence.

#### Scenario: Observation is rebound to another source

- **WHEN** an existing snapshot gains an observation from a different canonical seed
- **THEN** the distinct seed/snapshot binding set changes
- **AND** the corpus evidence digest changes even when snapshot bytes are identical

#### Scenario: Identical re-fetch metadata is not material evidence

- **WHEN** the same seed observes the same snapshot again with only `fetched_at`, content type, or parser metadata changed
- **THEN** the observation history remains auditable
- **AND** the distinct binding set and corpus evidence digest do not change solely for that metadata

### Requirement: Public cache exports the complete treatment-quality population

The public cache MUST provide `cache treatment quality-export --root ... --output ...` as the authoritative prefiling treatment producer. The exact envelope MUST include the current corpus evidence digest, a sorted unique list of every treatment ID, a population SHA over all treatment rows and all immutable review history, deterministic `integrity_issue_ids`, one item for every listed ID in the same order, and a canonical `set_sha256` over the unsigned envelope. Every item MUST have exactly one effective status from `candidate`, `verified`, `rejected`, or `superseded`.

#### Scenario: Pending and defective rows remain visible

- **WHEN** the cache contains a candidate or a resolved row whose source/review provenance cannot be validated
- **THEN** quality-export includes its ID and emits that item as `status=candidate` with `quality_blockers`
- **AND** never drops the row from the population

#### Scenario: Partial or forged set is rejected

- **WHEN** an item or ID is omitted, duplicated, reordered inconsistently, added, or any corpus/population/set binding is changed
- **THEN** the treatment-set contract is invalid
- **AND** prefiling cannot become complete

#### Scenario: Invisible cache corruption is retained

- **WHEN** a content-addressed snapshot or indexed text fails its digest, an object-store component is symlinked, or immutable review history violates a foreign key
- **THEN** quality-export reports a deterministic integrity issue
- **AND** live prefiling cannot become complete

### Requirement: Treatment review is status-specific and content-bound

Every resolved treatment MUST be based on indexed official full text bound to the candidate snapshot and source chain, a canonical reviewer, immutable matching review history, and a non-future aware RFC 3339 review timestamp with seconds that is not earlier than immutable candidate `created_at`. A verified decision MUST additionally have a matching court quote and locator, exact confirmed target-authority ID, confirmed structured target identity, and no rejection reason. A rejected decision MUST have a canonical decision reason; it MAY omit quote, locator, and speaker together, but a supplied quote MUST be a matching court quote with locator. The raw `review_decision` MUST remain the immutable `verified` or `rejected` decision even when the item's effective exported status becomes `superseded`.

#### Scenario: Verified relation is promoted

- **WHEN** source snapshot, indexed text, source chain, official URL, court quote, locator, target identity, reviewer, timestamp, and review history all agree
- **THEN** quality-export emits a content-bound `verified` item with `quote_verified=true` and `full_text_reviewed=true`

#### Scenario: Rejected candidate does not require an invented quote

- **WHEN** a human reviews indexed official full text for the same source chain and rejects the candidate with a canonical reason but no quote
- **THEN** quality-export MAY emit a content-bound `rejected` item with null quote/locator/speaker and `quote_verified=false`
- **AND** the rejection remains distinct from a pending candidate

#### Scenario: Review provenance does not agree

- **WHEN** any mandatory source, identity, quote, timestamp, or history binding is absent or inconsistent
- **THEN** the producer does not promote the row as resolved quality evidence
- **AND** prefiling remains blocked through the visible candidate item

#### Scenario: Unique replacement preserves the prior review

- **WHEN** a single candidate explicitly supersedes a completed treatment with the same source chain and target authority
- **THEN** the prior item is exported as `status=superseded` with its original `review_decision` and evidence unchanged
- **AND** the replacement is exported as pending `candidate` until its own review
- **AND** after that review the replacement enters `verified` or `rejected` while the prior remains `superseded`

#### Scenario: Malformed supersession fails closed

- **WHEN** replacement links branch, cycle, point to an absent predecessor, disagree reciprocally, or change source/target identity
- **THEN** the runtime does not select or discard a winner
- **AND** affected IDs remain visible as candidate/blocker evidence

#### Scenario: Review predates candidate creation

- **WHEN** a treatment review has `reviewed_at < created_at`
- **THEN** review creation is rejected or a legacy malformed row is exported with `review_chronology_invalid`
- **AND** neither quality export nor prefiling can treat it as resolved

### Requirement: Prefiling binds two producer artifacts to one corpus state

`quality prefiling-refresh` MUST accept only the exact treatment-quality-set envelope and a closed refresh plan and MUST require the existing public cache root. It MUST open that cache read-only without creating or migrating files, regenerate both artifacts in one consistent SQLite read snapshot, and independently verify that caller and live artifacts bind the supplied current corpus digest and the same complete treatment IDs and population SHA, that their self-digests are valid, that cache integrity is clean, that gaps are a subset of declared requirements, and that pending/verified/rejected/superseded classifications are pairwise disjoint and their union equals the plan population.

#### Scenario: Matching complete producer pair is consumed

- **WHEN** quality-export and refresh-plan are produced from one unchanged current cache, all treatments are validly resolved, no stale seed remains, timestamps are current, and baseline equals current digest
- **THEN** prefiling MAY return `current_no_material_change` with `complete=true` and code `0`

#### Scenario: Disclosed gap remains bounded

- **WHEN** the only remaining limitation is an unchanged valid gap for a declared requirement
- **THEN** prefiling MAY return `bounded_current_with_disclosed_gaps` with `complete=true` and code `0`
- **AND** preserves the gap and does not interpret it as absence of practice

#### Scenario: Cache or population changes between producer calls

- **WHEN** the corpus digest, treatment IDs, or treatment population SHA differs between plan, treatment set, and current input
- **THEN** prefiling returns `refresh_incomplete` or material-change status with `complete=false` and code `3`

#### Scenario: Live cache cannot be safely verified

- **WHEN** the cache path or schema is missing/malformed, the SQLite 3 header is invalid, or `-wal`/`-shm`/`-journal` is present
- **THEN** the command returns input error code `2` without creating or mutating the cache
- **AND WHEN** the readable cache has content, index, symlink-containment, foreign-key, or caller/live binding drift
- **THEN** the assessment preserves diagnostics with `complete=false` and code `3`

#### Scenario: Static SQLite store changes during verification

- **WHEN** the database device/inode, size, `mtime_ns`, byte SHA-256, header, or sidecar state differs between the pre-read and post-transaction checks
- **THEN** the runtime records a static-store TOCTOU issue
- **AND** cannot return `complete=true`

### Requirement: Prefiling identity and chronology are explicit

Prefiling MUST require a lowercase SHA-256 `subject_evidence_sha256` and at least one unique canonical claim ID. Filing-significant timestamps MUST use the full RFC 3339 date-time shape with seconds and timezone for completion. Plan `as_of` MUST equal `checked_through`, `reviewed_at` MUST not precede `checked_through`, `checked_through` MUST not precede `filing_cutoff`, and `as_of`, `checked_through`, and `reviewed_at` MUST not be future claims.

#### Scenario: Claim population is explicit

- **WHEN** `--claim-id` is missing, empty, noncanonical, or duplicated
- **THEN** the CLI returns code `2` without a prefiling artifact

#### Scenario: Timestamp cannot support currentness

- **WHEN** a timestamp is reduced, lacks the required timezone for completion, violates chronology, or lies in the future
- **THEN** prefiling returns code `2` for an invalid input shape or code `3` for an assessable incomplete chronology as appropriate
- **AND** never returns `complete=true`

### Requirement: Schemas describe structure and runtime enforces cross-record parity

The practice-quality and case-relative-workbench schemas MUST close the structural input/output shapes and MUST disclose non-local digest, set-equality, chronology, and cross-record rules as runtime invariants where JSON Schema cannot express them. The authoritative runtime and portable handoff MUST revalidate a complete prefiling artifact's exact field set, artifact digest, coverage requirement digest and gap subset, corpus/population/set/live-cache bindings, complete treatment classification, timestamps, empty blockers, and exact claim set before accepting it as filing-significant quality evidence.

#### Scenario: Schema-valid producer artifacts agree with runtime

- **WHEN** source and clean-installed producers create a valid plan, treatment set, reliability report, or prefiling report
- **THEN** the artifact validates under its published schema definition
- **AND** source and installed runtime produce equivalent process outcomes and JSON apart from expected paths

#### Scenario: Mutated quality binding is rejected during handoff

- **WHEN** a prefiling artifact's requirement digest, gap scope, treatment set digest, population SHA, treatment classification, chronology, or claims are altered
- **THEN** handoff validation rejects the quality binding even if an outer envelope hash is recomputed

### Requirement: Existing v1 paths require explicit regeneration

The release MUST document that `practice-quality.v1.json`, `case-relative-workbench.v1.json`, and top-level `schema_version: "1.0"` paths are intentionally hardened in place for installed-path compatibility, not backward acceptance. Prior artifacts lacking the new required fields and bindings MUST remain historical/audit-readable only and MUST NOT satisfy current completion or handoff gates.

#### Scenario: User upgrades with older artifacts

- **WHEN** a user has an older coding, refresh, treatment, prefiling, or reviewed-handoff artifact
- **THEN** guidance instructs the user to regenerate it from authoritative source data in dependency order
- **AND** forbids manually inserting missing fields or hashes to simulate the new contract

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
