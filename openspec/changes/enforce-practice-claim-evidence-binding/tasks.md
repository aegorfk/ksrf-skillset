## 1. Regression Contract

- [x] 1.1 Add RED tests proving fictional and coerced finding IDs currently pass the generic `practice_claim` gate.
- [x] 1.2 Add negative fixtures for cross-claim/result findings, stale claim/result/source/attachment/trust anchor/refresh, blocked/partial filing reports, wrong-workspace replay, wording or inference mismatch, missing practice or selection approval, request mutation, role downgrade, and incomplete complete-index responses.
- [x] 1.3 Add a positive multi-line fixture and manifest-time TOCTOU revalidation tests.

## 2. Runtime Binding Gate

- [x] 2.1 Preserve strict claim, issue, finding, and maximum-inference fields and compute deterministic practice-binding requests.
- [x] 2.2 Add the host authority protocol, native current-state projection validation, exact issue approval, and immutable receipts.
- [x] 2.3 Add the independent host-registry complete practice index, including the authoritative empty set, and reject deletion, insertion, substitution, and role downgrade.
- [x] 2.4 Thread the authority through composer, release, approval, and workflow paths with a fail-closed default.
- [x] 2.5 Keep legacy unbound practice sentences readable as drafts but blocked at release.

## 3. Skill and Schema Contract

- [x] 3.1 Advance structured-complaint and filing-package schemas to 1.3 with practice bindings, receipts, index, and conditional ready-state requirements.
- [x] 3.2 Update `ksrf-cassation-judicial-meaning`, complaint QA, and filing references with the exact binding and corpus-inference stop rule.
- [x] 3.3 Add behavioral evals for fictional, cross-claim, stale, overbroad, missing-approval, index-mutation, and positive exact bindings.

## 4. Candidate Verification

- [x] 4.1 Run focused and full complaint-cycle and cassation-skill tests.
- [x] 4.2 Run root tests, strict skillset validation, and strict OpenSpec validation.
- [x] 4.3 Obtain independent contract/code review with no unresolved P1/P2 findings.
- [x] 4.4 Generate and verify the exact candidate manifest and hashes.

## 5. Candidate Publication

- [x] 5.1 Commit the isolated change and push only `codex/ksrf-judicial-meaning-evidence-binding-20260901`.
- [x] 5.2 Confirm the remote feature SHA and confirm `main` plus global skills remain unchanged.

## 6. Human Promotion Gate

- [ ] 6.1 Obtain separate exact-hash human approval before any merge to `main`.
- [ ] 6.2 Obtain separate exact-hash human approval before any global-skill installation.
