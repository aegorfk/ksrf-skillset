## ADDED Requirements

### Requirement: Application-finding sentences preserve exact binding identity

The system SHALL preserve `claim_id`, `norm_passport_id`, strict unique `application_record_ids`, strict unique `evidence_ids`, and `maximum_supported_inference` for every `application_finding` sentence and SHALL derive `application_binding_sha256` from exact matter, draft, sentence, section, text, claim, passport, record-set, evidence-set, and inference-ceiling bytes.

#### Scenario: Bound finding survives normalization

- **WHEN** a draft contains a complete application-finding binding
- **THEN** the normalized sentence map preserves every binding field and the locally derived fingerprint

#### Scenario: Legacy finding remains repairable

- **WHEN** a legacy application finding lacks one or more binding fields
- **THEN** its available identifiers remain readable with `application_binding_status=unbound`, but it cannot satisfy release support

#### Scenario: Malformed identifiers are supplied

- **WHEN** an application finding contains null, non-string, blank, or duplicate record/evidence identifiers
- **THEN** normalization rejects the binding instead of coercing the values

### Requirement: Release support uses current host application authority

The system SHALL require an injected host authority for every present `application_finding` and SHALL NOT treat complaint-supplied IDs, statuses, fingerprints, booleans, general human approval, or the sentence-role receipt as evidence authority.

#### Scenario: Fictional evidence identifier

- **WHEN** a verified-looking finding references an ID absent from current host records
- **THEN** release support fails with an exact sentence-specific unknown-evidence blocker

#### Scenario: Foreign-claim or foreign-norm record

- **WHEN** a resolved application record or evidence span belongs to a different claim, norm, or edition
- **THEN** release support fails even if its text looks relevant

#### Scenario: Authority is absent or mutates the request

- **WHEN** no authority exists or its adapter changes the canonical request
- **THEN** release support fails closed and no receipt is emitted

### Requirement: Native application records and chain are exact and current

For each request, the system SHALL resolve a host-attested complete ordered `chain_records` inventory independently from the caller-selected `application_record_ids`, reject duplicate or non-canonical stage ordering, recompute every record fingerprint and classification, recompute the complete chain, validate the current norm-version passport, and require one current application-gate receipt for each selected positive record. Selected records SHALL be a subset of positive supporting records, have `outcome_causation=determinative|contributory`, and pass current norm-version and preservation prerequisites. An incorporation-only final record MAY be present in the complete chain without being misclassified as a selected positive record, while every selected approval SHALL bind the same complete chain fingerprint.

The requested evidence set SHALL exactly equal the complete positive proof set: non-contradicted full-act court `express_norm_use|operative_rule` spans and required court/disposition `outcome_link` proof for direct application; only non-contradicted evidence satisfying each named implicit premise's exact role/speaker rule, including court/disposition `outcome_link|counterfactual_analysis` for the counterfactual premise and human-confirmed reviewer `alternative_ground_analysis`; and any non-contradicted full-act court/disposition incorporation evidence required by the surviving chain. Every proof span SHALL match its owning record's act/stage, claim, and norm. Every incorporated record reference SHALL resolve uniquely to an earlier record in the complete chain. Broad classification output SHALL NOT make contradicted, party-only, background, quotation-only, foreign-scope, or unrelated spans eligible.

#### Scenario: Application is unclear or does not survive

- **WHEN** the reconstructed chain is unclear or superseded, or a requested record is not part of the supported surviving chain
- **THEN** the finding is blocked regardless of caller status or outcome

#### Scenario: Bare affirmance is offered as proof

- **WHEN** a later act merely affirms without express incorporation or independent proven application
- **THEN** it cannot establish the application finding

#### Scenario: Caller omits a later adverse act

- **WHEN** selected records omit a later act that the host complete-chain inventory identifies as superseding or making application unclear
- **THEN** the complete chain controls and the finding is blocked

#### Scenario: Incorporation-only final record

- **WHEN** a final act expressly incorporates an earlier positive application record but is not itself classified as positive
- **THEN** the complete chain may support the selected earlier record without requiring a contradictory positive-record receipt for the final act

#### Scenario: Record, locator, or approval becomes stale

- **WHEN** a record fingerprint, evidence locator, passport revision, preservation prerequisite, chain fingerprint, or trusted application approval changes
- **THEN** the prior receipt is stale and release verification fails

#### Scenario: Resolution set is incomplete or ambiguous

- **WHEN** the host omits, duplicates, or adds a requested record/evidence item
- **THEN** exact-set validation fails

#### Scenario: Incorporation proof is contradicted or foreign

- **WHEN** a surviving-chain result relies on an incorporation span marked `contradicted` or belonging to another norm, act, stage, or claim
- **THEN** the application finding remains blocked and no receipt is emitted

#### Scenario: Incorporation reference is unresolved

- **WHEN** a chain record names an incorporated record that is absent, duplicated, current, or later rather than uniquely earlier in the complete inventory
- **THEN** complete-chain validation fails closed

#### Scenario: Implicit premise contains broad background

- **WHEN** a nominally complete implicit proof adds a background span that does not satisfy the named premise's exact role and speaker rule
- **THEN** that span is not positive proof and the exact evidence set is rejected

### Requirement: Finding wording and inference are independently reviewed

The system SHALL require a current host-owned scope record and trusted approval binding exact UTF-8 reviewed-statement bytes and SHA-256, matter/draft/sentence/section identity, the same claim/passport fingerprint and revision, selected record/evidence sets, complete-chain fingerprint plus its independent revision/check time, and an independently stored `maximum_supported_inference`. The chain revision/check time SHALL NOT be conflated with the top-level application-index authority revision.

#### Scenario: Sentence wording differs from reviewed wording

- **WHEN** the release sentence is inserted, paraphrased, or broadened after review
- **THEN** the application-finding binding fails and requests a new exact review

#### Scenario: Inference ceiling is only echoed by the caller

- **WHEN** no independently stored host ceiling and approval match the supplied ceiling
- **THEN** the finding remains unbound

### Requirement: The host attests the complete application-finding set

The system SHALL obtain from a pre-existing host draft registry one current authoritative index containing every application-finding sentence ID, section, role, claim ID, norm-passport ID, and application-binding SHA. Every ready manifest SHALL carry this index, including an authoritative empty set.

#### Scenario: Finding line or receipt is deleted

- **WHEN** a persisted manifest drops a finding line and its per-line receipt
- **THEN** the complete-index recheck detects the missing line

#### Scenario: Finding role is downgraded

- **WHEN** a persisted finding is relabeled as narrative while keeping its text or evidence
- **THEN** the complete-index recheck rejects the role substitution

#### Scenario: New or substituted finding appears

- **WHEN** a line is inserted or its binding SHA changes after the index was issued
- **THEN** the exact index-set or hash check fails

### Requirement: Persisted release manifests revalidate application authority

The filing-package manifest SHALL store complete per-line application-finding receipts and a nullable complete-index receipt, include them in the release basis, and re-resolve current authority during render/status, pack build, manifest verification, expert approval, and final readiness.

#### Scenario: Ready manifest has no application finding

- **WHEN** a ready draft contains no `application_finding` sentence
- **THEN** per-line receipts are empty but a current host-authoritative `bindings=[]` index is still required

#### Scenario: Blocked diagnostic lacks authority

- **WHEN** a blocked diagnostic manifest has not obtained application authority
- **THEN** empty receipts and a null index remain schema-valid but cannot support a ready status

#### Scenario: Application finding is present

- **WHEN** any sentence has role `application_finding`
- **THEN** every such sentence must be bound, every exact receipt must be present, and the complete index must be current before a ready status is valid

#### Scenario: Host state changes after build

- **WHEN** records, chain, approvals, reviewed wording, or authority revision change after manifest creation
- **THEN** current verification fails and prior human approval cannot cure the stale evidence

### Requirement: Human promotion boundaries remain intact

Passing the application-finding gate SHALL establish only a candidate's technical evidence binding. It SHALL NOT authorize legal approval, merge, global installation, signature, payment, transmission, or filing.

#### Scenario: Candidate passes automated checks

- **WHEN** the branch passes tests, schemas, reviews, and manifest verification
- **THEN** it remains candidate-only until separate exact-hash human promotion decisions occur
