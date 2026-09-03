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

### Requirement: Treatment writes use one reserved provenance transaction

Treatment proposal and review MUST acquire an owned `BEGIN IMMEDIATE` transaction
before the first database-backed provenance read. The same transaction MUST contain
all snapshot, indexed-text, official-source, source-chain, treatment, predecessor,
successor, current-history, mutation, exact-history-insert, and final-result reads
needed by that operation. It MUST commit explicitly only after all checks and writes
succeed, and MUST roll back both treatment state and history on any body or commit
failure. Pure row-independent argument and finite canonical-JSON validation MAY
precede the transaction. A caller-owned transaction MUST be rejected without being
committed or rolled back, and a successful result MUST NOT depend on a post-commit
database read.

#### Scenario: Source binding cannot change between review and decision

- **WHEN** a second SQLite connection attempts to change the indexed source-chain,
  treatment source, official observation, or other reviewed database provenance
  after review validation has begun
- **THEN** that mutation cannot interleave before the treatment decision commits
- **AND** the successful result and immutable history bind the same protected state

#### Scenario: Proposal predecessor cannot change between validation and insertion

- **WHEN** a replacement proposal validates a completed predecessor while another
  writer attempts to change that predecessor or create a competing successor
- **THEN** at most one protected state is committed
- **AND** the losing operation records neither a treatment row nor a history event

#### Scenario: Commit failure is atomic

- **WHEN** the treatment mutation and history insert run but the transaction cannot
  commit
- **THEN** both changes are rolled back
- **AND** the connection no longer owns the failed transaction

#### Scenario: Caller transaction ownership is preserved

- **WHEN** proposal or review is invoked while its connection already has a caller-
  owned transaction
- **THEN** the operation fails before changing treatment state
- **AND** it neither commits nor rolls back the caller's transaction

### Requirement: Treatment contention is typed and never retried internally

The reserved treatment transaction MUST temporarily use zero SQLite busy timeout,
perform only one begin/write/commit attempt, and restore the connection's prior busy
timeout after success or failure before that connection is reused. If restoration
fails, the corpus connection MUST be quarantined, low-level close MUST be attempted,
and a distinct diagnostic MUST identify the transaction outcome as committed, not
committed, or uncertain and disclose when close was not confirmed. The timeout-zero
attempt MUST itself be inside this cleanup boundary. A restoration, rollback, or
uncertain post-commit error MUST NOT be mislabeled as the ordinary nothing-recorded
contention case. Only SQLite `BUSY` and `LOCKED`, including their extended result
codes, MUST become a dedicated `PublicCorpusBusyError`; unrelated operational, I/O,
read-only, or integrity failures MUST NOT be mislabeled. This no-retry boundary
applies to the treatment transaction, not to earlier writable-corpus construction
or schema/search initialization.

#### Scenario: Another writer owns the reservation

- **WHEN** proposal or review reaches its transaction boundary while another
  connection holds the SQLite writer reservation
- **THEN** it makes one begin attempt and raises `PublicCorpusBusyError`
- **AND** it adds no treatment/history state and restores the prior busy timeout

#### Scenario: A reader prevents DELETE-mode commit

- **WHEN** the transaction reaches commit while another connection's read snapshot
  prevents an exclusive commit
- **THEN** it raises `PublicCorpusBusyError` without retry
- **AND** its treatment mutation and history insertion are rolled back together

#### Scenario: Explicit retry observes the committed winner

- **WHEN** a contending caller explicitly repeats the operation after the winning
  transaction has committed
- **THEN** ordinary exact-replay, immutable-review, or replacement-conflict rules
  apply to the now-current state
- **AND** the runtime does not fabricate or choose a second legal-review decision

#### Scenario: Timeout restoration fails after a known transaction outcome

- **WHEN** SQLite cannot restore the prior busy timeout after the treatment
  transaction has committed or rolled back
- **THEN** the runtime quarantines that connection, attempts low-level close, and
  does not return the corpus object for reuse
- **AND** the error distinguishes committed from not-committed state and requires
  reopening the cache before any deliberate follow-up

#### Scenario: Commit outcome becomes uncertain

- **WHEN** a commit attempt changes SQLite transaction state but reports an error
  before the runtime can confirm successful completion
- **THEN** the runtime does not report the ordinary nothing-recorded busy result
- **AND** it quarantines the corpus connection and requires manual comparison of
  the treatment row with its exact history before any deliberate retry

#### Scenario: Rollback cannot be confirmed

- **WHEN** rollback of an active owned treatment transaction reports failure
- **THEN** the runtime quarantines the corpus connection and attempts low-level close
- **AND** the diagnostic reports an uncertain outcome rather than allowing later
  corpus work to commit partial treatment state

#### Scenario: Zero-timeout setup reports failure after application

- **WHEN** the attempt to set zero busy timeout changes connection state and then
  reports an error before any treatment transaction begins
- **THEN** the cleanup boundary restores the caller's prior timeout or quarantines
  the connection if restoration cannot be confirmed

### Requirement: Treatment history is exact at every write boundary

History insertion MUST be a non-ignoring exact insert that affects one row. A new
treatment and its `candidate_created` event MUST be indivisible, as MUST a review
status update and its `verified` or `rejected` event. A candidate is reviewable only
when its complete current history is the sole canonical `candidate_created` event:
null reviewer, event time equal to immutable `created_at`, exact proposal payload,
and recomputed deterministic history ID. Missing, extra, malformed, colliding, or
mismatching history MUST fail before or roll back the mutation and MUST NOT be
silently repaired.

An exact deterministic proposal replay, including a replacement replay, MUST be
idempotent only when the existing row's immutable proposal columns and complete
status-appropriate history are exact. It MUST return the stored status from inside
the reserved transaction without another history event. A same-ID mismatch or a
different successor MUST fail as corruption or conflict.

#### Scenario: Forged decision-history collision does not promote a candidate

- **WHEN** a row already occupies the deterministic history ID required by a review
- **THEN** the exact insert fails and the candidate status remains unchanged
- **AND** the forged row is not treated as the decision just requested

#### Scenario: Candidate base history is missing or changed

- **WHEN** `candidate_created` is absent, duplicated, has changed payload, reviewer,
  timestamp, or ID, or another event is already present on a candidate
- **THEN** review fails before the treatment update
- **AND** the evidence history remains available for quality-export diagnosis

#### Scenario: Exact proposal is safely replayed

- **WHEN** a caller repeats the exact ordinary or replacement proposal after losing
  its prior successful response
- **THEN** the existing status is returned without inserting another row or event
- **AND** any mismatch in the stored immutable row or status-appropriate history
  turns the replay into a fail-closed error

#### Scenario: History insertion aborts proposal or review

- **WHEN** a trigger, constraint, collision, or row-count failure prevents the exact
  candidate or decision history insert
- **THEN** the paired treatment insert or status update is rolled back
- **AND** the operation does not report success

### Requirement: Native audit preparation emits a primary-answer-blinded reviewer archive

New output from `quality coding-audit-prepare` MUST carry
`bundle_contract_version="1.1"` in the parent manifest and MUST add
`independent-review-packet.zip` as its sixth exact content file. The manifest
schema MUST retain a separate legacy branch under which a preceding five-file
manifest with no `bundle_contract_version` remains valid; the new producer MUST
emit only the exact six-file `1.1` variant and MUST NOT reinterpret a legacy
manifest as `1.1`.

The ZIP MUST contain exactly six members: the five payload members
`CODING-BRIEF.json`, `CODING-CODEBOOK.md`, `REVIEW-INSTRUCTIONS.md`,
`review-materials.jsonl`, and `secondary-coding-template.jsonl`, plus
`review-packet-manifest.json`, which inventories exactly those five payload members.
It MUST use a sorted flat path order, stored entries, fixed timestamps and
regular-file modes, and no archive comment so identical accepted inputs produce
identical bytes.

Each review-material row MUST have the exact closed field set `schema_version`,
`candidate_id`, `chain_id`, `document_id`, `source_text_sha256`,
`packet_text_sha256`, and `text`. It MUST carry the same candidate and
chain/document identities as the frozen audit inputs, the normalized store
`source_text_sha256`, a `packet_text_sha256` over the exact UTF-8 text string
supplied in that row, and the non-empty full text. It MUST NOT carry `source_id` or
`source_ids`. Exact full text MAY retain TAB, LF, VT, FF, and CR layout controls but
MUST contain a visible non-whitespace character and MUST reject every other Unicode
control (`Cc`) plus every format (`Cf`) and surrogate (`Cs`) code point before any
publication. The pending templates MUST equal the producer's selected secondary
templates byte for byte.

The sorted unique inner-manifest `candidate_ids`, the review-material candidate
IDs, and the pending-template candidate IDs MUST each equal the frozen audit
plan's exact `required_candidate_ids`, with every candidate present exactly once
in each JSONL file. For every candidate, `candidate_id`, `chain_id`, and
`document_id` MUST agree across material and template, and both text digests MUST
agree with the content-addressed document and exact supplied text. A missing,
extra, duplicate, or cross-bound row MUST prevent any parent bundle publication.

The self-digesting inner manifest MUST bind the exact candidate population and the
size and SHA-256 of all five payload members. It MUST declare primary-answer
blinding, full-text inclusion, pending independent review, no created human
approval, no default publication safety, and no legal readiness. Both the inner and
versioned parent manifests MUST repeat `codebook_sha256` for the exact built-in
codebook bytes and `coding_brief_file_sha256` for the exact serialized neutral-brief
bytes, and each value MUST equal the corresponding inner file-inventory digest.

The required `--codebook-version` input MUST accept exactly the release-supported
allowlist, which is only `1.0` in this release, and MUST resolve the tracked neutral
`CODING-CODEBOOK.md`. Primary records MUST carry that same version, but their value
is only an equality check: neither codebook selection nor any ZIP bytes may be
derived from a primary record. A missing or unsupported selection, primary mismatch,
or missing, unsafe, empty, non-UTF-8, or concurrently replaced codebook MUST prevent
publication.

`CODING-BRIEF.json` MUST be the exact closed self-digesting projection of the frozen
plan's neutral reviewer context: plan identity and title, selected codebook version,
exactly one directional hypothesis with only its ID, fixed
`hypothesis_under_test` status, text and norm references,
applicable norm editions, population, inclusion/exclusion rules, materiality rule,
and contradiction rule. It MUST NOT project query/search lanes or text, screening
matches, sampling metadata, primary coding, `approved_by`, `adverse_review`, or
other reviewer/search metadata. Because `supports`/`adverse` require a fixed
proposition and the 20-field coding record has one unqualified `relation`, an open
`research_question`, zero questions, or multiple frozen questions MUST prevent
publication and require separate per-hypothesis frozen plans and audit packets.

Apart from the independently captured unchanged judicial `text` and its content
identities/digests, the required candidate union, the closed neutral plan projection,
the opaque frozen-plan commitment, and the independently selected built-in codebook,
no inner field, metadata value, row order, path, or archive byte may derive from a
primary coding record or digest, first-coder identity, sample-lane label, or
adjudication. Raw query lanes, query text, and screening matches MUST NOT be
serialized. `plan_sha256` and each content-bound candidate ID MAY cryptographically
commit to the full frozen plan, including query lanes; documentation MUST NOT call
that commitment semantic secrecy from a party that knows or guesses the plan. The
content of the judicial act itself and membership in the union sample are not hidden
and MUST NOT be described as outcome-blind evaluation.

The parent manifest MUST bind the exact ZIP byte length and SHA-256, and successful
producer stdout MUST expose that same digest as
`independent_review_packet_sha256`. The embedded guide MUST instruct the custodian
to retain and communicate the expected digest separately from the ZIP and the
reviewer to compare the received ZIP against it before extraction or coding. The
inner self-digest MUST NOT be represented as authentication of its own enclosing
ZIP.

#### Scenario: User hands one archive to the independent coder

- **WHEN** a valid native audit bundle is prepared from a verified workspace
- **THEN** its parent manifest binds one deterministic
  `independent-review-packet.zip`
- **AND** that archive gives the reviewer all selected full texts, identities,
  pending templates, and Russian instructions without the primary answers
- **AND** producing it leaves secondary review, adjudication, legal approval, and
  filing incomplete

#### Scenario: Legacy and new parent manifests stay distinguishable

- **WHEN** schema validation receives an intact preceding five-file manifest
  without `bundle_contract_version` or a new six-file manifest with
  `bundle_contract_version="1.1"`
- **THEN** each is accepted only by its own exact schema branch
- **AND** a five-file `1.1` manifest, a six-file unversioned manifest, or either
  manifest with a mixed file set is rejected

#### Scenario: Every required candidate has exactly one review pair

- **WHEN** the producer assembles review materials, pending templates, and the
  inner manifest for a multi-candidate union
- **THEN** all three sorted unique candidate populations equal the frozen required
  candidate set
- **AND** omission, duplication, an extra candidate, or swapped identity/text
  binding prevents publication

#### Scenario: Primary answers change without changing selected membership

- **WHEN** two otherwise identical valid workspaces differ only in primary
  substantive coding, first-coder identity, and per-lane selection while retaining
  the same candidate union, codebook version, and source inputs
- **THEN** their independent-review ZIP bytes are identical
- **AND** their parent custodian artifacts may still differ and remain separately
  bound to their exact primary inputs
- **AND** unchanged judicial text remains byte-exact even if it contains a string
  also used by one primary coding record

#### Scenario: Codebook authority is independent and allowlisted

- **WHEN** the custodian omits `--codebook-version`, selects anything other than
  `1.0`, a primary record names another version, or the installed `1.0` codebook is
  missing, unsafe, empty, non-UTF-8, or changes during preparation
- **THEN** preparation fails without publishing a parent bundle
- **AND** no primary field is treated as authority for codebook selection or bytes

#### Scenario: Directional reviewer context is sufficient without revealing search design

- **WHEN** a valid frozen plan contains exactly one `hypothesis_under_test`
- **THEN** `CODING-BRIEF.json` contains only the closed neutral projection needed to
  apply the codebook and its self-digest binds every projected field
- **AND** both manifests bind the exact brief and codebook file bytes
- **AND** no query lane/text, match, sampling lane, primary answer, `approved_by`, or
  `adverse_review` appears in the ZIP

#### Scenario: Open or multiple questions cannot supply a relation target

- **WHEN** the verified frozen plan contains an open `research_question`, zero
  questions, or more than one question
- **THEN** preparation fails without output instead of guessing which proposition
  `supports`, `adverse`, or the returned `relation` addresses
- **AND** the custodian must prepare separate single-hypothesis frozen plans and
  audit packets

#### Scenario: Captured and normalized text representations differ

- **WHEN** a selected captured text contains layout whitespace that normalizes for
  the content-addressed document identity
- **THEN** `source_text_sha256` remains the normalized store digest
- **AND** `packet_text_sha256` verifies the exact text string supplied to the reviewer
- **AND** TAB, LF, VT, FF, and CR remain byte-exact, while NUL, every other `Cc`, and
  every `Cf` or `Cs` character cause fail-closed refusal with no output

#### Scenario: Collapsed source copies differ only in exact layout

- **WHEN** two source rows share one chain/document identity and normalized store
  digest but have different exact UTF-8 text strings
- **THEN** preparation fails without output instead of selecting a variant by
  source ID or input order

#### Scenario: Packet is not automatically public-safe

- **WHEN** the archive contains selected full judicial texts
- **THEN** its manifest fixes `publication_safe=false`
- **AND** the instructions require deliberate secure transfer and separate
  publication/redaction judgment rather than treating public-source status as
  blanket permission to republish personal data

#### Scenario: Reviewer receives an externally pinned archive

- **WHEN** preparation succeeds and the custodian transfers the ZIP
- **THEN** stdout exposes the same SHA-256 that the parent manifest records for the
  ZIP
- **AND** the instructions require the reviewer to compare that separately supplied
  expected digest before using the archive
- **AND** neither the digest nor a successful comparison claims a signature,
  reviewer identity, completed review, legal approval, or filing authority

### Requirement: Embedded review guidance states the closed completion contract

`REVIEW-INSTRUCTIONS.md` MUST name all and only the 20 fields of the authoritative
completed secondary-coding record: `candidate_id`, `chain_id`, `document_id`,
`label`, `speaker`, `proposition`, `quote`, `quote_locator`, `norm_edition_id`,
`reasoning_to_outcome`, `reading_family`, `relation`, `remedy`, `coder`,
`codebook_version`, `material_facts`, `alternative_grounds`, `human_review`,
`quote_verified`, and `full_text_reviewed`. It MUST list the seven accepted `label`
values and five accepted `relation` values, require `speaker="court"` for
substantive labels, distinguish unchanged identity/procedure fields from
human-authored coding, and state the non-empty visible text and canonical
identifier requirements.

The guide MUST define `material_facts` as a non-empty list of visible strings and
`alternative_grounds` as a list that may be empty, whose objects contain required
`ground` and Boolean `independently_sufficient`, optional `quote` and
`quote_locator`, and no other fields. It MUST permit `human_review="approved"`,
`quote_verified=true`, and `full_text_reviewed=true` only after those human acts
occurred. It MUST require a separate strict UTF-8 JSONL return file with exactly one
closed record per required candidate, unique keys, finite JSON values, and no edits
to the original packet/template.

#### Scenario: Second coder can return a contract-complete file

- **WHEN** the reviewer follows the embedded guide without access to the parent
  custodian directory
- **THEN** the guide identifies every required field, enum, nested shape, identity
  preservation rule, and strict JSONL constraint needed for a completed secondary
  record
- **AND** it says that return of the file does not itself prove independence,
  text verification, agreement, legal approval, or filing authority
