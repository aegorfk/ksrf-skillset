## Why

Practice-analysis requests and results project a local `claim_id` to a
deterministic public alias when the existing public-ID predicate requires it.
Two consumers currently cross that boundary incorrectly: request creation
derives `question_id` from the local ID although it emits the public ID, and
wording review looks for the local ID in the public result. The real sibling
runtime therefore rejects the request, or a later valid result cannot be
reviewed, leaving the claim blocked.

## What Changes

- Derive each exported `question_id` from the exact public `claim_id` emitted
  beside it so the real sibling runtime accepts the self-consistent request.
- Resolve an active local claim to the same public alias before checking result
  bindings and finding applicability.
- Reject a selected local claim whose projection collides with any active
  claim before writing a request or alias record.
- Apply the same unique-owner rule when validating or reviewing legacy
  artifacts, so a pre-guard collision cannot reach `ready`.
- Keep a corrected request selectable when a legacy self-inconsistent request
  for the same claim remains in immutable audit history.
- Keep identity-bearing external fields on the public representation, while
  the local review command and local ledger retain the exact active local ID.
- Preserve exact revision, result-import, finding-applicability, human-review,
  trust, drafting, and filing gates.
- Add an end-to-end regression through the real sibling validator with an
  identifier that requires projection, plus fail-closed identity regressions.

## Capabilities

### Added Capabilities

- `ksrf-practice-analysis-identity-binding`: keep projected practice-analysis
  artifacts self-consistent and bind them back to the exact active local claim
  without weakening evidence gates.

## Impact

- Runtime: two identity-boundary corrections and an early collision guard in
  `ksrf-complaint-cycle/scripts/ksrf_practice_analysis.py`.
- Source-only: focused practice-analysis tests and this OpenSpec change.
- Existing evidence-binding contracts and archived requests remain independent;
  this change grants no release, legal, publication, or filing authority.
- No new PII detector or anonymity guarantee is introduced. Safe/pass-through
  IDs and free-text fields keep their existing behavior.
