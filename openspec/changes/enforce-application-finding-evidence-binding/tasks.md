## 1. Regression Contract

- [x] 1.1 Add a RED test proving `application_record_ids` are currently dropped from an `application_finding`.
- [x] 1.2 Add a RED test proving caller statuses plus fictional evidence currently satisfy release support.
- [x] 1.3 Add negative fixtures for malformed/coerced IDs, cross-claim/norm records, unrelated spans, missing locators, caller-omitted later records, unclear or superseded complete chains, stale record/passport/application/scope approvals, wording or inference mismatch, request/response mutation, role downgrade, and incomplete indexes.
- [x] 1.4 Add a positive multi-line fixture and manifest-time TOCTOU revalidation tests.

## 2. Runtime Binding Gate

- [x] 2.1 Preserve strict claim, passport, record, evidence, and inference fields and compute deterministic application-binding requests.
- [x] 2.2 Add the host authority protocol and locally reconstruct the independently resolved complete chain inventory, selected positive records, exact positive proof set, passport, application approvals, reviewed wording, and scope validation.
- [x] 2.3 Add the independent host-registry complete application-finding index, including the authoritative empty set.
- [x] 2.4 Thread the authority through composer, render/status, release build/verify/approval, and final readiness with a fail-closed default.
- [x] 2.5 Keep legacy unbound findings readable as drafts but blocked at release, with exact repair blockers.

## 3. Skill and Schema Contract

- [x] 3.1 Advance structured complaint to `1.4` and filing package to `1.5` with application bindings, receipts, index, and conditional ready-state requirements.
- [x] 3.2 Update complaint-cycle, complaint-QA, and release methodology with the exact application-finding stop rule.
- [x] 3.3 Add behavioral evals for fictional, cross-claim, stale-chain, overbroad-wording, and positive exact bindings.

## 4. Candidate Verification

- [x] 4.1 Run focused RED/GREEN and full complaint-cycle tests.
- [x] 4.2 Run cassation-skill and root tests, strict schemas, skillset, quick validation, and strict OpenSpec validation.
- [x] 4.3 Obtain independent contract/code review with no unresolved P1/P2 findings.
- [x] 4.4 Generate and verify the exact candidate manifest and hashes.

## 5. Candidate Publication

- [x] 5.1 Commit the isolated change and push only `codex/ksrf-application-finding-evidence-binding-20260901`.
- [x] 5.2 Confirm the remote feature SHA and confirm live `main` plus global skills remain unchanged.

## 6. Human Promotion Gate

- [ ] 6.1 Obtain separate exact-hash human approval before any merge to `main`.
- [ ] 6.2 Obtain separate exact-hash human approval before any global-skill installation.
