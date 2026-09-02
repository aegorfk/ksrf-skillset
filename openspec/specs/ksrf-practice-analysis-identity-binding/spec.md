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
