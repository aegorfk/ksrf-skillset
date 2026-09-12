## Why

Post-release adversarial review showed that the independent-ground branch could
label implicit norm use as preserved even when the two supporting
`ImplicitPremiseProof` records were contradicted or the full record was still
unapproved. The final filing gate remained closed, but the intermediate legal
classification overstated the evidence and did not satisfy the published
complete-approved-record contract.

## What Changes

- Require non-contradicted issue and operative-logic premise records, quoted
  full-act evidence, court-authored operative logic and a diagnostic
  named-review marker before the
  independent-ground branch emits `implicit_norm_use_preserved`; state that
  only the separate trusted ledger can prove approval of the fingerprinted
  complete record.
- Keep a claimed but unverified implicit-use record at `application_unclear`
  with an explicit verification reason; do not turn either uncertainty or an
  independent causal ground into proof of non-application.
- Prevent a contradicted implicit premise from producing
  `implicitly_applied_proven` in the ordinary determinative branch.
- Reject duplicate premise names before order can hide a contradiction, and
  require court/disposition evidence rather than a party-only assertion for
  affirmative non-application.
- Reject an affirmative complete-independent-ground assertion when the
  canonical outcome-causation axis does not carry the matching status.
- Reject a record whose valid court-authored independent-ground span conflicts
  with the canonical outcome-causation axis, and encode the duplicate-premise
  and causal-axis invariants in the standalone JSON Schema as well as runtime.
- Require nonblank quoted text for incorporation and later independent-ground
  chain proof, so a locator without evidentiary content cannot prove survival
  or supersession between instances.
- State expressly that the diagnostic named-review marker controls the
  intermediate classifier only; exact-content trusted approval remains a
  separate admissibility and release condition.
- Require an RFC 3339 review timestamp before the diagnostic marker counts as
  complete; an opaque nonempty string must not unlock a positive intermediate
  classification.
- Add direct runtime tests for approved, pending, contradicted and genuinely
  absent implicit-use records, while retaining the separate trusted approval
  and causal-harm gates.
- Keep every changed machine-readable OpenSpec SHALL body on one physical line
  and add a JSON-level continuation-clause check, because strict validation
  alone did not detect truncated wrapped requirement text.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-academic-method-ingestion`: tighten the proof state required to preserve
  implicit norm use and define the fail-closed result for unverified candidates.

## Impact

The change is limited to the application-evidence record and classifier, its
schema, chain proof and focused tests, the implicit-application reference, OpenSpec and the
generated release manifest. It does not add a filing bypass, change the
independent-ground causation result, or add any source/runtime dependency.
