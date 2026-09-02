## 1. Native Revocation Regressions

- [x] 1.1 Add a non-mocked source-identity E2E test that reaches GO through real current source authority, revokes the exact native approval, and observes status downgrade to ABSTAIN.
- [x] 1.2 Add a non-mocked issue-selection E2E test that reaches GO through a real persisted candidate and gate approvals, revokes the exact selection approval, and observes status downgrade to ABSTAIN.
- [x] 1.3 In both tests, assert the affected evidence/option identifier, the native revoked-approval semantics, blocked state, exit code `3`, and absence of network/model calls.
- [x] 1.4 Prove byte-for-byte preservation of the prior result object and prior event-ledger prefix, with exactly one appended status event.

## 2. Narrow Runtime Correction If RED Exposes One

- [x] 2.1 If required, repair only the existing source-authority or issue-binding current revalidation path; do not add a new route, CLI, schema, verifier profile, dependency, or storage format.
- [x] 2.2 Confirm status reloads the persisted matrix and never treats the cached GO recommendation or historical approval as current authority.
- [x] 2.3 Keep `human_decision=pending`, `legal_assessment_automated=false`, `filing_authority=false`, and `filing_performed=false` after both downgrades.

## 3. Verification

- [x] 3.1 Run focused RED/GREEN tests and the complete admissibility test module.
- [x] 3.2 Run the full complaint-cycle and root suites, strict schemas, skillset validation, runtime/offline installation checks, and strict OpenSpec validation.
- [x] 3.3 Inspect the diff for forbidden mocks, network/model activity, and public runtime/CLI/schema/installer drift.
- [x] 3.4 Obtain independent contract/code review with no unresolved P1/P2 findings.

## 4. Publication

- [x] 4.1 Regenerate and verify the exact manifest if tracked test-file inventory changes require it.
- [ ] 4.2 Commit the isolated change, merge through the approved publication workflow, push `main`, and confirm the exact remote SHA.
- [ ] 4.3 Install the exact published runtime globally and re-run strict runtime/offline validation.
- [ ] 4.4 Archive this OpenSpec change only after implementation and publication evidence are complete.
