## ADDED Requirements

### Requirement: Practice sentences preserve exact binding identity

The system SHALL preserve distinct constitutional `claim_id`, native `practice_claim_id`, `issue_option_id`, strict unique `evidence_ids` interpreted as native finding identifiers, and `maximum_supported_inference` for every `practice_claim` sentence and SHALL derive `practice_binding_sha256` from exact matter, draft, sentence, section, text, constitutional claim, practice claim, issue, finding-set, and inference-ceiling bytes. The current practice-analysis ledger claim ID and `PracticeClaimGate.claim_id` SHALL both equal `practice_claim_id` and SHALL NOT be inferred from constitutional `claim_id`.

#### Scenario: Bound practice sentence survives normalization

- **WHEN** a draft contains a complete practice binding
- **THEN** the normalized sentence map preserves every binding field and the locally derived fingerprint

#### Scenario: Legacy unbound practice sentence remains a draft

- **WHEN** a legacy practice sentence lacks a constitutional claim, practice claim, issue, finding set, or inference ceiling
- **THEN** it remains readable with `practice_binding_status=unbound` but cannot satisfy release support

#### Scenario: Malformed identifiers are supplied

- **WHEN** a practice sentence contains a scalar string, null, non-string, blank, or duplicate finding identifier
- **THEN** normalization rejects the binding instead of coercing it

#### Scenario: Constitutional and practice claim identities are conflated

- **WHEN** the host cannot prove the distinct constitutional claim projection and the exact native practice claim identity, or the ledger and PracticeClaimGate IDs disagree
- **THEN** release support fails rather than guessing an identity mapping

### Requirement: Release support uses current host practice authority

The system SHALL require an injected host authority for every present `practice_claim` and SHALL NOT treat complaint-supplied IDs, statuses, fingerprints, booleans, result copies, or embedded pass flags as authority.

#### Scenario: Fictional or foreign finding

- **WHEN** a verified-looking practice sentence references an unknown finding or a finding for another claim or result
- **THEN** release support fails with a sentence-specific blocker

#### Scenario: Authority is absent or mutates the request

- **WHEN** no practice authority exists or its adapter changes the supplied canonical request
- **THEN** release support fails closed and no receipt is emitted

#### Scenario: Authority response changes while being read

- **WHEN** a stateful or mutable authority mapping returns different approval, finding, or index values across reads
- **THEN** the runtime uses one detached snapshot for validation and receipt construction and never emits unvalidated later values

### Requirement: Native practice state is exact, reviewed, and current

For every requested practice binding, the host authority SHALL resolve an exact host-owned matter/draft-to-case/workspace revision and input-manifest binding, reopen that current practice-analysis state without accepting a caller path, and SHALL provide closed exact projections of the active practice claim, ready binding, content-bound native research request, imported v2 result, requested findings, wording review, result/attachment/trust-anchor material, filing validation, and pre-filing refresh. The runtime SHALL require exact agreement among the native request handoff, `request_sha256`, claim-set digest and canonical request/result claim bindings and among all workspace, case, practice-claim, constitutional-claim, issue, source, result, finding, wording, inference, event, refresh, and digest fields.

The current report SHALL have `stage=filing`; every projected `state=ready` claim SHALL carry semantically valid native material identifiers, timestamps, empty blockers/actions, and a content-bound wording-review ledger event; the exact target practice claim SHALL be `state=ready`, `draft_blocked=false`, present in list-valued `allowed_claim_ids`, and free of claim-specific blockers; global integrity errors SHALL be empty; and the required current pre-filing refresh SHALL have `valid=true` and bind the complete ready-claim set. Refresh recording SHALL follow all bound native material events, filing generation and validation SHALL follow refresh, authority checking SHALL follow filing validation, and the refresh `as_of` day SHALL match its recording and authority-check day. A native `valid=false`, `stage_verdict=partial` report caused solely by different isolated claims MAY support this exact ready claim only when report/state ID projections agree and its errors exactly reconstruct the other blocked claims; a `valid=true` partial projection SHALL fail as inconsistent.

Native request creation SHALL precede its attachment and result. Refresh recording SHALL follow the latest bound material event of every claim in the complete ready set, not only the exact target claim.

#### Scenario: Result or trust material is stale

- **WHEN** the claim revision, result, attachment, source file, sibling workspace, trust anchor, or any bound material event changed
- **THEN** release support fails even if a historical result once passed

#### Scenario: Pre-filing refresh is absent or stale

- **WHEN** filing-stage validation lacks a current refresh bound to the exact ready-claim set and later material events
- **THEN** the practice sentence cannot enter a ready manifest

#### Scenario: Authentic target claim is blocked

- **WHEN** the current host report is non-filing, contains any global integrity error, lacks a valid complete-ready-set refresh, or marks the exact target claim non-ready, blocked, or absent from the allowed set
- **THEN** release support fails instead of treating exact projection as a passing decision

#### Scenario: An unrelated isolated claim is blocked

- **WHEN** the current filing report is globally partial only because a different claim is blocked while the exact target claim and complete-ready-set refresh satisfy every target rule
- **THEN** this target practice binding is not rejected solely by the unrelated claim

#### Scenario: Caller selects another practice workspace

- **WHEN** a caller path or a different matter/draft-to-case workspace binding is offered with otherwise valid artifacts
- **THEN** release support fails as a wrong-workspace replay

#### Scenario: Target resolution set is incomplete or excessive

- **WHEN** the host omits, duplicates, or adds a finding whose `claim_ids` contains the target practice claim, or returns a requested finding outside the exact claim/result
- **THEN** exact-set validation fails

#### Scenario: Multi-claim result contains an unrelated finding

- **WHEN** the current v2 result also contains a structurally valid finding belonging solely to another bound practice claim
- **THEN** that unrelated finding neither supports nor blocks the exact target binding

#### Scenario: Native finding wording differs from the reviewed sentence

- **WHEN** a finding or its candidate carries a stronger or different claim wording even though its identifier and ceiling look valid
- **THEN** exact wording validation fails and the finding cannot support release

### Requirement: Wording and inference remain within the reviewed limit

The system SHALL require exact equality between release sentence bytes and the current reviewed wording and SHALL require the requested maximum inference to equal the independently stored result, wording-review, and host-scope ceilings.

#### Scenario: Sentence wording changed after review

- **WHEN** punctuation, text, claim identity, or finding set differs from the current wording review
- **THEN** release support fails pending a new review

#### Scenario: Sentence exceeds the permitted inference

- **WHEN** the requested ceiling differs from the current result or review ceiling
- **THEN** release support fails even if the findings themselves are valid

### Requirement: Issue selection uses an exact trusted approval

The system SHALL bind the practice sentence to the current selected issue and exact PracticeClaimGate projection and SHALL locally reconstruct both host-owned approval requests and fingerprints: `practice:<practice_claim_id>` and the separate issue `selection`. The current human selection SHALL be `principal` or `reserve`, and both approvals SHALL resolve as current and trusted with distinct trusted approval receipt IDs.

#### Scenario: Raw approval fields are supplied

- **WHEN** a practice gate contains `human_decision=approved` but no exact trusted approval resolves for the current issue, claim, statement, findings, and freshness scope
- **THEN** release support fails

#### Scenario: Practice claim is not present in the selected issue

- **WHEN** the sentence refers to a claim absent from the current issue option or its substantive practice gate
- **THEN** release support fails even when a compatible corpus result exists

#### Scenario: Practice approval exists but issue selection is absent

- **WHEN** the exact practice claim is approved but the issue is rejected, unselected, or lacks a current trusted `selection` approval
- **THEN** release support fails

#### Scenario: One approval receipt is reused for both decisions

- **WHEN** `practice:<practice_claim_id>` and `selection` point to the same trusted approval identity
- **THEN** release support fails because the two human decisions are not independent

### Requirement: The host attests the complete practice-line set

The system SHALL obtain from a pre-existing host draft registry one current authoritative index containing every practice sentence ID, section, role, constitutional claim ID, practice claim ID, issue option ID, and binding SHA for the exact matter and draft. Every per-line receipt and that index SHALL bind one identical authority revision, and all per-line receipts SHALL bind one workspace revision and input-manifest fingerprint. Every ready manifest SHALL carry this receipt even when the authoritative set is empty.

#### Scenario: Practice line is deleted or downgraded

- **WHEN** a persisted manifest drops a practice line or relabels it as narrative while dropping its receipt
- **THEN** the complete-index recheck detects the mismatch

#### Scenario: New or substituted practice line appears

- **WHEN** a line is inserted or its exact binding SHA changes after the host index was issued
- **THEN** the exact index set or hash check fails

#### Scenario: Claim and index come from different authority revisions

- **WHEN** individually valid claim receipts and an individually valid complete index were resolved from different host snapshots
- **THEN** release support and manifest verification fail with an authority-snapshot mismatch

### Requirement: Persisted release manifests revalidate practice authority

The filing-package manifest SHALL store complete per-line practice receipts and a nullable practice-index receipt, include them in the release basis, require `blockers=[]` for every ready status, and re-resolve current authority during manifest verification, approval, and final readiness.

#### Scenario: Ready manifest retains a blocker

- **WHEN** a manifest declares expert-review or human-signing readiness while `blockers` is non-empty
- **THEN** both schema and runtime verification reject the contradictory ready projection

#### Scenario: Ready manifest has no practice sentence

- **WHEN** a ready draft contains no `practice_claim`
- **THEN** per-line receipts are empty but a current host-authoritative index with `bindings=[]` is still required

#### Scenario: Blocked diagnostic has no practice authority

- **WHEN** a blocked diagnostic manifest has not obtained practice authority
- **THEN** empty receipts and a null index remain schema-valid but cannot support a ready status

#### Scenario: Authority changes after pack build

- **WHEN** any current claim, result, finding, source, attachment, trust-anchor, approval, wording, or refresh binding changes after the manifest was created
- **THEN** manifest verification fails and prior human approval cannot cure it

### Requirement: Human promotion boundaries remain intact

Passing the practice gate SHALL establish only a candidate's technical evidence binding. It SHALL NOT authorize legal approval, merge, global installation, signature, payment, transmission, or filing.

#### Scenario: Candidate passes all automated checks

- **WHEN** the branch passes tests, schemas, reviews, and manifest verification
- **THEN** it remains candidate-only until separate exact-hash human promotion decisions occur
