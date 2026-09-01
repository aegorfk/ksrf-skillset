## ADDED Requirements

### Requirement: Requested-remedy sentences preserve exact binding identity

The structured complaint SHALL preserve a non-empty claim ID, issue-option ID, norm-version-passport ID, and canonical unique application-record IDs for every `requested_remedy` sentence. It SHALL emit a deterministic SHA-256 over the complaint identity, sentence content, evidence IDs, and those binding references.

#### Scenario: Bound remedy survives normalization

- **WHEN** a draft contains a well-formed requested-remedy binding
- **THEN** the runtime preserves every binding field and its deterministic fingerprint in `SentenceEvidenceMap`

#### Scenario: Duplicate or malformed identifiers

- **WHEN** a new binding contains empty, non-string, or duplicate identifiers
- **THEN** normalization fails with a named binding-contract error instead of coercing or deduplicating the values

#### Scenario: Requested-remedy role downgrade

- **WHEN** a sentence is placed in the `requested_remedy` section but the caller labels it `narrative`
- **THEN** normalization still treats it as `requested_remedy` and the binding gate remains mandatory

#### Scenario: Requested-remedy role is moved outside its section

- **WHEN** a caller labels a bound sentence `requested_remedy` inside `facts` or any other section while leaving the real requested-remedy section empty
- **THEN** normalization rejects the section/role mismatch and the misplaced line cannot satisfy the remedy gate or index

#### Scenario: Malformed or duplicate sentence identity

- **WHEN** a caller supplies a noncanonical or repeated sentence ID
- **THEN** normalization rejects it before authority lookup or receipt projection

### Requirement: Release support uses current host authority

The release-support gate MUST resolve exact upstream artifacts through a host-attested binding authority and MUST NOT treat complaint-supplied IDs, statuses, fingerprints, or `passed` flags as authority.

#### Scenario: Authority is absent

- **WHEN** a requested-remedy sentence otherwise looks verified but no host binding authority is supplied
- **THEN** release support fails closed for that sentence

#### Scenario: Embedded pass flag is supplied

- **WHEN** a complaint payload embeds a `passed` or `filing_ready` flag without a current authority resolution
- **THEN** the flag is ignored and release support remains blocked

### Requirement: Resolved artifacts form one claim-scoped graph

The release-support gate SHALL recompute content fingerprints and SHALL require the resolved selected issue, norm-version passport, application records, and sentence evidence to belong to the same claim, norm, and edition. Every referenced gate receipt SHALL be content-bound and carry its trusted approval reference.

#### Scenario: Cross-claim evidence carryover

- **WHEN** a `CLAIM-B` requested-remedy sentence cites an evidence item or application record resolved only for `CLAIM-A`
- **THEN** release support fails with the affected sentence ID and a cross-claim blocker

#### Scenario: Stale upstream receipt

- **WHEN** an issue, passport, or application record no longer matches the content fingerprint in its authority receipt
- **THEN** release support fails closed as stale

#### Scenario: Arbitrary approval-request fingerprint

- **WHEN** an artifact receipt carries a non-empty but noncanonical approval request or an incomplete issue approval-key set
- **THEN** local validation rejects it instead of treating string presence as trusted approval evidence

#### Scenario: Unknown evidence or unusable locator

- **WHEN** a requested-remedy evidence ID is absent from same-claim resolved evidence or lacks a usable locator
- **THEN** release support fails closed for that evidence ID

#### Scenario: Same norm but old source-evidence edition

- **WHEN** same-claim source evidence names the selected norm but a different or missing norm-version ID
- **THEN** release support fails with an edition mismatch

#### Scenario: Source content or locator changes under a reused revision

- **WHEN** current source evidence keeps its verification revision ID but changes its content SHA-256, locator, verifier, or checked time
- **THEN** manifest revalidation rejects the old full source-evidence receipt as stale

#### Scenario: Host graph values require coercion

- **WHEN** the authority returns a non-string or noncanonical nested issue, passport, application, evidence, or locator value
- **THEN** release support rejects the raw resolution before an upstream deserializer can coerce it

#### Scenario: Host artifact schema version is unknown

- **WHEN** a resolved issue, norm-version passport, or application record uses any schema version other than its required `1.0.0`
- **THEN** release support rejects the artifact even if a receipt was recomputed for that unknown shape

#### Scenario: Receipt timestamp is not a canonical date-time

- **WHEN** source evidence or the authoritative remedy index carries a non-RFC3339 `checked_at` string
- **THEN** runtime rejects it explicitly before emitting a receipt

#### Scenario: Authority mutates the lookup request

- **WHEN** an authority adapter mutates an evidence or application identifier in the lookup object it receives
- **THEN** release support reports request mutation and validates no receipt under the original binding SHA

### Requirement: Principal and reserve lines validate independently

The runtime SHALL validate every requested-remedy sentence independently and SHALL NOT infer membership from a singular top-level issue-option alias.

#### Scenario: Two correctly bound remedy lines

- **WHEN** principal line A binds only to claim A artifacts and reserve line B binds only to claim B artifacts
- **THEN** both lines pass the remedy binding gate in the same complaint

#### Scenario: One of two lines crosses claims

- **WHEN** principal line A is valid but reserve line B references an application record from claim A
- **THEN** the complaint remains blocked and identifies reserve line B

### Requirement: Manifest recheck uses the authoritative complete remedy index

The release-support and manifest gates MUST resolve the complete current requested-remedy line set from a host draft registry independent of the complaint or manifest projection. The canonical index SHALL bind matter, draft, strict unique sentence IDs, requested-remedy section and role, exact line binding SHA-256 values, authority revision, and checked time.

#### Scenario: One of two remedy lines is deleted everywhere in the manifest

- **WHEN** a caller removes line B and its receipt, leaves valid line A, and recomputes the release basis
- **THEN** the current manifest set differs from the host-authoritative A/B index and revalidation fails

#### Scenario: Remedy line role is downgraded

- **WHEN** a line remains in the requested-remedy section but its manifest role is changed to narrative
- **THEN** runtime and schema report a role mismatch and the line cannot disappear from index reconciliation

#### Scenario: Extra or changed remedy line is injected

- **WHEN** a manifest adds a remedy sentence or changes its binding SHA without a matching current registry entry
- **THEN** index reconciliation fails closed

#### Scenario: Index authority is absent or stale

- **WHEN** no index resolver is configured, or the stored index receipt differs from the current authoritative revision or set
- **THEN** release support or manifest verification rejects the package

#### Scenario: Duplicate or malformed host index

- **WHEN** the host index contains a malformed, noncanonical, or repeated sentence entry
- **THEN** local validation rejects the index instead of canonicalizing it silently

### Requirement: Legacy unbound payloads are draft-only

The runtime SHALL continue to normalize legacy unbound complaint payloads for working-draft use, but MUST NOT mark an unbound requested-remedy sentence release-supported.

#### Scenario: Legacy verified-looking remedy

- **WHEN** a legacy requested-remedy sentence has non-empty evidence IDs and `support_status=verified` but no exact binding
- **THEN** draft construction and schema-valid serialization succeed with `relief_binding_status=unbound`, while `require_release_support` fails closed

### Requirement: Render and release share the same binding gate

Render preparation and release-pack construction SHALL invoke the same remedy binding validation and SHALL accept the host authority only through an explicit dependency boundary.

#### Scenario: Direct release with valid authority

- **WHEN** a fully bound complaint and current host authority are supplied to the release entrypoint
- **THEN** the remedy binding itself does not add a release blocker and its fingerprint is present in the release basis

#### Scenario: Workflow release without authority

- **WHEN** a workflow attempts to release a bound remedy without configured host authority
- **THEN** the workflow remains blocked rather than trusting payload fields

#### Scenario: Manifest projection is removed or malformed

- **WHEN** a caller removes any remedy entry, marks a bound line unbound, downgrades its role, supplies malformed or repeated sentence/evidence/application IDs, removes the authoritative index, or recomputes manifest hashes after such a change
- **THEN** manifest 1.1 validation blocks before host authority can promote the package
