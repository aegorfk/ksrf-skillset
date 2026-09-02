## ADDED Requirements

### Requirement: Admissibility matrices are versioned, complete and evidence-bound

The installed runtime MUST accept an `AdmissibilityMatrix` only when all twelve canonical gates appear exactly once and every row records a status, rationale, applicability reason, evidence references, official-rule check time, curability, record availability, next action and gate-specific disposition. Status MUST be one of `pass`, `fail`, `unknown` or `not_applicable`. Every status MUST carry evidence; an unavailable record MUST cite the exhausted-search observation. `unknown` MUST NOT be treated as `pass`; `not_applicable` MUST include a reviewable reason and current official-rule support. Route, proceeding status and permissible remedy MUST be derived from their evidence-bound gate dispositions rather than unbound summary fields. A claimed current official snapshot MUST be recomputed against current local source authority rather than trusted from payload flags.

#### Scenario: Complete current matrix is validated

- **WHEN** a matrix contains every canonical gate once, valid row invariants and official-rule evidence that resolves as current verified authority
- **THEN** `admissibility validate` returns a valid normalized matrix and persists its exact input and result in the matter workflow ledger

#### Scenario: Gate is missing or duplicated

- **WHEN** a matrix omits a canonical gate, repeats one, or adds an unknown gate
- **THEN** validation fails with the exact gate defect and no route recommendation is emitted

#### Scenario: Not-applicable is unsupported

- **WHEN** a row says `not_applicable` without a non-empty applicability reason and current official-rule evidence
- **THEN** validation fails instead of allowing the row to disappear from the hard-gate set

#### Scenario: Official check is missing or stale

- **WHEN** the official snapshot or a gate lacks a valid check time, declares stale authority, or cites evidence that no longer resolves as current verified official authority
- **THEN** `GO_TO_KSRF` is impossible and derivation records an official-authority blocker

### Requirement: Route derivation is deterministic and fail closed

The installed runtime MUST derive exactly one documented route by explicit precedence and MUST report every decisive gate and blocker. It MUST NOT emit a scalar readiness score. `GO_TO_KSRF` MUST require all applicable gates to pass, a completed proceeding for the individual-complaint route, a complete issue assessment with at least one viable option bound by its native `issue-candidate-content:sha256:<64 lowercase hex>` fingerprint and evidence, and an evidence-bound viable permissible-remedy gate. The workflow MUST reopen the latest same-matter issue-candidate event, recompute each bound fingerprint and verify the candidate `claim_id`; a caller-supplied digest alone MUST NOT establish the binding. `unknown` MUST produce `FIX_FIRST` or `ABSTAIN_PENDING_RECORD`, never `GO_TO_KSRF` or `NO_GO_KSRF`. Source or record unavailability and failure to find a viable issue option MUST NOT be converted into an absence finding. Every recommendation MUST bind a computed canonical matrix revision and the exact option fingerprints used.

#### Scenario: All legal inputs support GO

- **WHEN** the official snapshot is currently verified, every applicable gate passes, issue research is complete with a viable option and the remedy is viable
- **THEN** derivation emits `GO_TO_KSRF` with decisive evidence, no scalar score and human decision still pending

#### Scenario: Controlled remediable gap exists

- **WHEN** a gate has a curable fail or controlled unknown and no higher-priority abstention or incurable failure applies
- **THEN** derivation emits `FIX_FIRST` with the concrete next actions and reconsideration conditions

#### Scenario: Active proceeding supports a court request

- **WHEN** the case is active, current-route evidence explicitly marks a court request as preferred, and no official-authority, incurable, unavailable-record or controlled-curable blocker applies
- **THEN** derivation emits `COURT_REQUEST_ROUTE` without claiming that a court must make the request

#### Scenario: Incurable barrier is proved

- **WHEN** a gate has a proved incurable fail and current official authority is available
- **THEN** derivation emits `NO_GO_KSRF` with the decisive gate evidence

#### Scenario: Critical record is unavailable

- **WHEN** an unknown depends on a record unavailable after an exhausted search, or official authority is missing, stale or currently unverifiable
- **THEN** derivation emits `ABSTAIN_PENDING_RECORD`, not `NO_GO_KSRF`

#### Scenario: Issue or remedy research is incomplete

- **WHEN** hard gates otherwise pass but issue research is incomplete or has no currently viable fingerprinted option
- **THEN** derivation cannot emit GO and returns the documented controlled next step

### Requirement: Runtime route preserves human legal and filing control

The installed CLI MUST expose `ksrf admissibility validate|derive|status` in Russian, MUST perform no network or model call, and MUST persist through the existing content-addressed matter workflow ledger. Every derived `KSRFRouteRecommendation` MUST set `human_decision=pending`, `legal_assessment_automated=false`, `filing_authority=false` and `filing_performed=false`.

#### Scenario: Recommendation is derived locally

- **WHEN** a user runs `ksrf admissibility derive --workspace ... --payload ...`
- **THEN** the command reads only local inputs, records exact hashes and returns a human-review planning artifact without external transmission or filing

#### Scenario: Status is requested

- **WHEN** a user runs `ksrf admissibility status` after a validation or derivation
- **THEN** the command reloads the latest persisted matrix, re-resolves current official authority, re-derives the recommendation and appends a new status event without modifying the prior record

#### Scenario: Current authority is revoked after GO

- **WHEN** a prior recommendation was `GO_TO_KSRF` but a later status check cannot revalidate one of its official evidence IDs
- **THEN** status reports `ABSTAIN_PENDING_RECORD`, preserves the older event and exits as blocked

#### Scenario: Existing workspace is used

- **WHEN** the route runs in a workspace created before this capability existed
- **THEN** it works through the existing workflow event ledger and does not require rewriting `matter.json`

#### Scenario: Clean runtime is installed

- **WHEN** the source repository is installed through the runtime manifest
- **THEN** both schemas, the domain module, the CLI route and user guidance remain available without source-only `evals` or tests
