## ADDED Requirements

### Requirement: Legal-holding sentences preserve exact binding identity

The system SHALL preserve `claim_id`, strict unique `evidence_ids`, and `maximum_supported_inference` for every `legal_holding` sentence and SHALL derive `holding_binding_sha256` from exact matter, draft, sentence, text, claim, evidence-set, and inference-ceiling bytes.

#### Scenario: Bound holding survives normalization

- **WHEN** a draft contains a complete legal-holding binding
- **THEN** the normalized sentence map preserves every binding field and the locally derived fingerprint

#### Scenario: Legacy unbound holding remains a draft

- **WHEN** a legacy holding lacks a claim, evidence set, or inference ceiling
- **THEN** it remains readable with `holding_binding_status=unbound` but cannot satisfy release support

#### Scenario: Malformed identifiers are supplied

- **WHEN** a holding contains null, non-string, blank, or duplicate evidence identifiers
- **THEN** normalization rejects the binding instead of coercing the values

### Requirement: Release support uses current host source authority

The system SHALL require an injected host authority for every present `legal_holding` and SHALL NOT treat complaint-supplied IDs, statuses, fingerprints, booleans, or embedded pass flags as evidence authority.

#### Scenario: Fictional evidence identifier

- **WHEN** a verified-looking legal holding references an ID absent from the host resolution
- **THEN** release support fails with a sentence-specific unknown-evidence blocker

#### Scenario: Foreign-claim evidence

- **WHEN** a resolved source record belongs to a different claim
- **THEN** release support fails even if its text and locator otherwise look relevant

#### Scenario: Authority is absent or mutates the request

- **WHEN** no holding authority exists or its adapter changes the supplied canonical request
- **THEN** release support fails closed and no receipt is emitted

### Requirement: Native SourceEvidence and claim scope are exact and current

For each requested evidence ID, the system SHALL require exactly one full native schema-1.0.0 SourceEvidence record and its recomputed current-filing-authority result, plus one separate host-owned claim-scope record. The native record SHALL retain its canonical evidence ID, source ID, verification ID, raw SHA, official locator, filing state, validation state, and exact booleans. The current-authority result SHALL have exact `filing_ready=true` and no blockers. The claim-scope record SHALL carry the same claim, evidence ID, native source ID, exact `authority_role=ksrf_legal_holding`, official locator, pinpoint, raw SHA, verification revision, latest current evidence ID, `freshness_state=current`, scope revision/check time, and independently stored inference ceiling.

#### Scenario: Stale, superseded, or unofficial source

- **WHEN** a record is stale or superseded, lacks a valid revision or SHA, fails current-filing-authority recomputation, or is not the latest official evidence for its source/origin
- **THEN** release support fails with the exact source-record blocker

#### Scenario: Locator or pinpoint mismatch

- **WHEN** native SourceEvidence, the claim-scope record, and the host-attested receipt disagree about the official locator or pinpoint
- **THEN** release support fails and the source cannot be used through a bare identifier

#### Scenario: Official evidence has the wrong legal role

- **WHEN** a current official VSRF, lower-court, application, or comparative record is offered as a `legal_holding`
- **THEN** the claim-scope role check rejects it even though native SourceEvidence is otherwise filing-ready

#### Scenario: Duplicate or extra resolution

- **WHEN** the host returns a requested source twice, omits one, or adds an unrequested source
- **THEN** the exact-set validation fails

### Requirement: The maximum inference is independently attested

The system SHALL require every host-owned claim-scope record and the host scope receipt to attest the exact independently stored `maximum_supported_inference` carried by the sentence binding, and SHALL locally reconstruct the complete scope approval request and its fingerprint.

#### Scenario: Sentence exceeds the attested ceiling

- **WHEN** the sentence binding carries an inference ceiling different from the current source or scope receipt
- **THEN** release support fails with an inference mismatch

#### Scenario: Embedded pass flag lacks exact approval scope

- **WHEN** a scope receipt says `passed` but its approval request, evidence fingerprints, or trusted approval ID is missing or altered
- **THEN** the receipt is rejected

### Requirement: The host attests the complete holding-line set

The system SHALL obtain from a pre-existing host draft registry one current authoritative index containing every legal-holding sentence ID, section, role, and binding SHA for the exact matter and draft. Every ready manifest SHALL carry this receipt even when the authoritative set is empty.

#### Scenario: Holding line is deleted with its receipt

- **WHEN** a persisted manifest drops a holding line and its per-line receipt
- **THEN** the complete-index recheck detects the missing line

#### Scenario: Holding role is downgraded

- **WHEN** a persisted holding is relabeled as narrative while keeping its text or evidence
- **THEN** the complete-index recheck rejects the role substitution

#### Scenario: New or substituted holding appears

- **WHEN** a line is inserted or its binding SHA changes after the host index was issued
- **THEN** the exact index-set or index-hash check fails

### Requirement: Persisted release manifests revalidate holding authority

The filing-package manifest SHALL store complete per-line holding receipts and a nullable holding-index receipt, include them in the release basis, and re-resolve current authority during manifest verification and approval.

#### Scenario: Ready manifest has no legal holding

- **WHEN** a ready draft contains no `legal_holding` sentence
- **THEN** per-line receipts are empty but a current host-authoritative index with `bindings=[]` is still required

#### Scenario: Blocked diagnostic has no legal holding

- **WHEN** a blocked diagnostic manifest has not obtained holding authority
- **THEN** empty receipts and a null index remain schema-valid but cannot support a ready status

#### Scenario: A legal holding is present

- **WHEN** any sentence has role `legal_holding`
- **THEN** every such sentence must be bound, every exact receipt must be present, and the complete index must be non-null before a ready status is valid

#### Scenario: Source changes after pack build

- **WHEN** the host source revision, raw SHA, locator, or inference ceiling changes after the manifest was created
- **THEN** manifest verification fails and prior human approval cannot cure the stale evidence

### Requirement: Human promotion boundaries remain intact

Passing the holding gate SHALL establish only a candidate's technical evidence binding. It SHALL NOT authorize legal approval, merge, global installation, signature, payment, transmission, or filing.

#### Scenario: Candidate passes all automated checks

- **WHEN** the branch passes tests, schemas, reviews, and manifest verification
- **THEN** it remains candidate-only until separate exact-hash human promotion decisions occur
