## Context

The matter workspace owns local claim identifiers. `request create` projects
each identifier through `_public_claim_id()`, and the v2 importer already maps
those public aliases back to active local claims. However, request creation
hashes `claim_questions[].question_id` over the local ID while emitting the
public ID; the sibling runtime hashes the emitted content and rejects the
request. `wording review` separately compares the local ID directly with
`payload.claim_bindings[].claim_id`. Both defects are invisible for a
pass-through identifier.

## Goals / Non-Goals

**Goals:**

- Make request attach and wording review work for identifiers that require the
  existing public-ID projection.
- Reuse the canonical public-ID projection rather than introducing a second
  alias format or alias registry.
- Keep identity-bearing external fields and their content-derived identifiers
  on one representation.
- Fail before writes when a selected projection collides with any active local
  claim's projection.
- Preserve legacy request bytes while preventing an internally inconsistent
  request from superseding a corrected request by filename-hash order.
- Preserve all existing content, provenance, revision, import, human-review,
  and filing gates.

**Non-Goals:**

- Do not reverse-resolve a non-active exported alias as a substitute for an
  exact active-ledger key.
- Do not add PII detection, guarantee anonymity, or sanitize free text.
- Do not redesign claim identifiers, schemas, handoff envelopes, or findings.
- Do not repair unrelated practice-analysis behavior.

## Decisions

### Project the local ID at the external binding boundary

After resolving the active claim by its local ID, wording review computes
`_public_claim_id(claim_id)` and uses that value only to find the exact result
binding and applicable findings. This mirrors request creation, v2 import, and
the existing `_request_binding()` helper.

### Hash the representation that is emitted

`claim_questions[].question_id` is content-addressed from the public
`claim_id` and question stored in that same object. This is the contract the
real sibling importer validates and does not change question text or semantics.

### Reject projection collisions before persistence

Request creation derives the public IDs of all active claims before writing
`claim-aliases.json` or a request. If any selected public ID has more than one
active local owner, it fails with a bounded error even when only one owner was
selected. It does not guess which local claim owns the alias.

The same unique-owner resolver is used by v2 result validation and wording
review. Thus an artifact imported before a later active collision remains
auditable but cannot authorize a review or make either colliding claim ready.

### Legacy requests remain audit history, not selection authority

State derivation keeps every archived request readable, but only a request
whose `claim_questions[].question_id` matches its emitted public claim ID and
question can become the current executable request. A legacy inconsistent
request remains byte-preserved; it cannot displace a corrected request merely
because its content hash sorts later.

### Keep command input local and fail closed

The command continues to require an exact active-ledger `claim_id`. It never
reverse-resolves a non-active exported alias. If a pass-through value is itself
an active key it remains valid. Missing bindings, changed claim hashes, unknown
findings, and findings for another claim remain errors.

### Preserve local audit identity

The wording-review ledger continues to store the local claim ID because it is
inside the private matter workspace and downstream state derivation keys on
that identity. The result and request bytes are never rewritten.

## Risks / Trade-offs

- [A second projection drifts] → Use the existing `_public_claim_id()` function
  at every external comparison.
- [The fix accidentally reverse-resolves aliases] → Test that an exported
  alias which is not an active key is rejected before result lookup.
- [Two local IDs project to one public ID] → Detect the collision before any
  request or alias write and fail instead of choosing an owner.
- [Legacy artifact predates the collision guard] → Recheck unique active
  ownership during result validation and wording review; append no review.
- [Legacy invalid request sorts after the corrected request] → Exclude the
  self-inconsistent request from executable selection without deleting it.
- [Evidence crosses between claims] → Retain exact claim hash and finding
  applicability checks and add a negative regression.
- [A passing test overstates authority] → Report only restoration of the local
  review route; drafting, legal, publication, and filing authority remain
  separate gates.

## Migration Plan

1. Add failing real-sibling and wording-review tests using a projected ID.
2. Hash exported question identity from exported content, reject projected-ID
   collisions across active state, keep legacy inconsistent requests out of
   executable selection, and use the projection for result/finding comparisons.
3. Run focused and full source/runtime validation and independent review.
4. Archive the validated change, publish one atomic commit, and install the
   exact published runtime.
