## 1. Regression Contract

- [x] 1.1 Add RED tests proving an explicit unknown or misspelled role currently bypasses release support.
- [x] 1.2 Add RED tests for canonical-role-to-narrative downgrade, deletion, insertion, global-order mutation, section movement, text substitution, stale receipt, malformed host response, and absent authority.
- [x] 1.3 Add positive tests for explicit/missing-role narrative, every canonical filing role, and an exact complete role index.

## 2. Runtime Integrity Gate

- [x] 2.1 Define the canonical role registry and emit sentence-specific release blockers for explicit unknown roles without mutating draft content.
- [x] 2.2 Add the host sentence-role index protocol, continuous global ordinals, strict request/response validation, deterministic ordered projection/index hashes, and immutable receipt.
- [x] 2.3 Thread the authority through pack build, manifest verification, approval, and workflow paths with a fail-closed ready-state default.
- [x] 2.4 Revalidate persisted receipts against current host authority and include the receipt in the release basis.

## 3. Schema and Skill Contract

- [x] 3.1 Advance filing-package schema to `1.4`, allow unknown roles only for blocked diagnostics with an exact correlated machine blocker, and require a valid ordered complete role index for ready statuses.
- [x] 3.2 Update complaint-cycle filing documentation and SKILL guidance with the canonical registry, compatibility boundary, and host-index stop rule.
- [x] 3.3 Add behavioral evals for typo/alias bypass, narrative downgrade, absent authority, and the positive exact-index path.

## 4. Candidate Verification

- [x] 4.1 Run focused and full complaint-cycle tests.
- [x] 4.2 Run root tests, strict skillset validation, and strict OpenSpec validation.
- [x] 4.3 Obtain independent contract/code review with no unresolved P1/P2 findings.
- [x] 4.4 Generate and verify the exact candidate manifest and hashes.

## 5. Candidate Publication

- [ ] 5.1 Commit the isolated change and push only `codex/ksrf-narrative-role-gate-20260901`.
- [ ] 5.2 Confirm the remote feature SHA and confirm `main` plus global skills remain unchanged.

## 6. Human Promotion Gate

- [ ] 6.1 Obtain separate exact-hash human approval before any merge to `main`.
- [ ] 6.2 Obtain separate exact-hash human approval before any global-skill installation.
