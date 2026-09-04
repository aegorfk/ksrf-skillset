# ksrf-practice-analysis-identity-binding Specification

## Purpose
TBD - created by archiving change resolve-practice-analysis-claim-aliases. Update Purpose after archive.
## Requirements
### Requirement: Exported claim identities are internally consistent

The practice-analysis runtime MUST project local claim IDs through the existing
deterministic public-ID function for identity-bearing external fields. It MUST
derive each `claim_questions[].question_id` from the exact public `claim_id` and
question emitted in that same object, and the resulting request MUST satisfy
the real sibling handoff validator. Before writing an alias record or request,
it MUST reject any selected local key whose projected public ID has more than
one owner across all active local keys. This projection is a syntactic identity
boundary, not a PII detector or anonymity guarantee; pass-through IDs and free
text retain their existing behavior.

#### Scenario: Projected request enters the real sibling runtime

- **WHEN** an active local claim requires the existing public-ID projection
  and request creation emits its binding and claim question
- **THEN** the binding and question use the same public ID, `question_id`
  matches that emitted content, and the real sibling handoff validator accepts
  the request without learning the local identity from an identity field

#### Scenario: Two local claims project to one public ID

- **WHEN** a selected exact active-ledger key projects to the same public ID as
  any other active key, including an unselected pass-through local key
- **THEN** request creation fails before writing `claim-aliases.json`, a
  canonical request, or an optional export and does not select an alias owner

#### Scenario: Active collision appears after result import

- **WHEN** a result was imported while its public claim ID had one active local
  owner and another active local key later projects to that same public ID
- **THEN** v2 validation and wording review treat the alias as ambiguous,
  append no wording review, and neither local claim can become `ready`; the
  earlier request, result, and import records remain audit-readable

#### Scenario: Local ID passes through the projection

- **WHEN** an active local ID already satisfies the existing public-ID
  predicate and has no collision
- **THEN** request creation preserves that ID and all existing request,
  attachment, result, and review behavior

#### Scenario: Legacy inconsistent request coexists with corrected request

- **WHEN** an immutable legacy request hashes `question_id` from a local ID,
  the corrected current request hashes it from emitted content, both bind the
  same current claim revision, and the corrected request is attached
- **THEN** state derivation selects only the internally consistent request for
  executable state, regardless of filename-hash order, while preserving the
  legacy request bytes for audit

### Requirement: Wording review crosses the claim identity boundary exactly once

The practice-analysis runtime MUST select wording-review targets by an active
local claim ID, project that ID through the same deterministic public-ID
function used by request creation, and require the imported v2 result to bind
that public ID to the exact current claim hash. It MUST use the public ID only
for external request, result, and finding comparisons and MUST retain the local
ID in private matter-workspace state. It MUST select only by an exact active
local key and MUST NOT reverse-resolve a non-active exported alias, consult an
alias record as authority, mutate external artifacts, or relax any
result-import, evidence, revision, human-review, trust, drafting, or filing
gate.

#### Scenario: Private claim receives a valid wording review

- **WHEN** an active claim ID requires the existing projection, its attached and
  imported drafting-eligible v2 result contains the canonical public alias and
  current claim hash, and a human reviewer submits an applicable finding
- **THEN** wording review resolves the external binding to that active local
  claim, records the review under the local ID, and allows only the existing
  downstream state derivation to determine readiness

#### Scenario: Non-active exported alias is supplied as a local selector

- **WHEN** a caller passes an exported alias that is not itself an exact active
  local key to wording review instead of the active local claim ID
- **THEN** the command rejects it as an unknown active claim before it can
  address local workspace state

#### Scenario: Result binding belongs to another claim

- **WHEN** the imported result lacks the selected claim's exact public-ID and
  current-hash binding, or a selected finding is not applicable to that public
  ID
- **THEN** wording review fails closed and appends no review event

#### Scenario: Alias record is stale or poisoned

- **WHEN** `claim-aliases.json` maps the projected ID to another local claim or
  otherwise disagrees with the deterministic projection
- **THEN** wording review ignores that record for authorization, resolves only
  from the selected active key and deterministic projection, and fails closed
  if the exact result or finding binding is absent

#### Scenario: External artifact is inspected

- **WHEN** request and result artifacts are read before and after wording review
- **THEN** their bytes and identity-bearing fields remain unchanged

#### Scenario: Public CLI contract is compared with the base release

- **WHEN** the identity-boundary runtime changes are inspected
- **THEN** all 18 practice-analysis help routes, 42 public argument actions,
  parser state, command tokens, and unrelated errors/non-help behavior remain
  unchanged

### Requirement: Result import independently anchors native coding reliability

Complaint-cycle `result import` MUST require
`--expected-finalization-receipt-sha256` for a v2 claim-bearing result. The importer
MUST independently compare it with the special quality binding's
`expected_receipt_sha256` and the recomputed finalization receipt self-digest after
validating the exact six-binding native relationship. It MUST record the explicit
value in the append-only `result_import` event, include it in the event digest, and
reject an idempotent re-import whose supplied value differs from the existing event.

`run attach` MUST remain unchanged because attachment precedes creation of the
finalization receipt. Legacy or unanchored results MAY remain audit-readable under
their existing status, but they MUST NOT be eligible for drafting or claim use.

#### Scenario: Independent import anchor matches the handoff

- **WHEN** a v2 result, attached trusted source, and independently supplied digest
  all bind the same native finalization receipt
- **THEN** import records that digest in the immutable event and may preserve the
  existing drafting-eligibility path

#### Scenario: Transported and local expectations differ

- **WHEN** the explicit import argument differs from the handoff binding or receipt
  self-digest
- **THEN** import fails before writing the result or event even if outer handoff
  hashes are valid

#### Scenario: Re-import supplies another expectation

- **WHEN** the same result identifier already has an immutable import event and a
  later invocation supplies a different expected digest
- **THEN** the importer rejects it rather than returning the earlier event as an
  idempotent success

### Requirement: Derived claim state rechecks the immutable native anchor

State derivation MUST reopen the selected result and import event and revalidate
the exact equality among event `expected_finalization_receipt_sha256`, special
binding `expected_receipt_sha256`, and receipt self-digest. It MUST also repeat the
six-binding and profile-origin relationship needed for claim use. The expected
digest MUST remain in exact-material ready bindings and prefiling refresh identity
so a later result/event substitution revokes readiness.

#### Scenario: Imported result changes after the event

- **WHEN** the stored result or any native binding changes after import while event
  bytes remain unchanged
- **THEN** state becomes blocked or stale and no wording, refresh, drafting, or
  filing transition remains ready

#### Scenario: Historical event lacks the expected digest

- **WHEN** state derives from an older result-import event without the new field
- **THEN** the event remains audit-readable but cannot contribute a current ready
  binding

### Requirement: Complaint-sentence binding independently enforces native lineage

The filing `practice_binding` consumer MUST independently verify the exact six
quality bindings, the finalization receipt self-digest and external expectation,
the receipt-to-reliability file/plan/candidate links, the uncertainty profile's
three origin links, and equality with the current claim state's immutable import
expectation. It MUST fail before emitting a complaint-sentence evidence receipt if
any relation is absent or mismatched, regardless of outer hashes or
`drafting_ready=true`.

#### Scenario: Ready state is cross-bound to another receipt

- **WHEN** a result and state are individually rehashed but carry different native
  finalization expectations
- **THEN** sentence evidence binding rejects the practice claim and emits no
  evidence receipt

#### Scenario: Standalone reliability replaces the finalizer output

- **WHEN** a complete compatibility reliability object is substituted without its
  exact native receipt relationship
- **THEN** both complaint-cycle consumers block claim use with value-free reasons
