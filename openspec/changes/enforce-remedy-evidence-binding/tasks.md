## 1. Regression Contract

- [x] 1.1 Add a focused RED test for `CLAIM-B` remedy evidence carried over from `CLAIM-A`.
- [x] 1.2 Add positive principal/reserve fixtures and negative role-downgrade, cross-edition, malformed, duplicate, unknown, stale-request, stale-source, dropped-line, mutating-authority, and legacy-unbound fixtures.
- [x] 1.3 Assert bound and explicit draft-only serialization conform to structured-complaint schema 1.1.

## 2. Runtime Binding Gate

- [x] 2.1 Preserve typed remedy binding fields, plural issue IDs, and deterministic binding fingerprints.
- [x] 2.2 Add the host-attested relief-binding authority protocol, local exact-artifact graph validation, and canonical full approval-request matching.
- [x] 2.3 Thread the authority dependency through render/release entrypoints while keeping the default fail-closed.
- [x] 2.4 Keep legacy unbound payloads readable as drafts but blocked at release.
- [x] 2.5 Require an independent host-authoritative complete remedy-line index and full source-evidence receipts; reject raw adapter coercion and request mutation.

## 3. Skill Contract

- [x] 3.1 Update structured-complaint and filing-package JSON Schemas to version 1.1 with explicit bound/unbound, relief-receipt schema 1.1.0, a typed authoritative index receipt, and strict relief projections.
- [x] 3.2 Update `ksrf-complaint-facts-demands` methodology and workflow reference with the binding and stop rule.
- [x] 3.3 Add cross-claim, role-downgrade, stale-request, and positive multi-line behavioral evals.

## 4. Candidate Verification

- [x] 4.1 Run focused RED/GREEN tests and the full complaint-cycle test suite after final review fixes.
- [x] 4.2 Run root tests, strict skillset validation, and strict OpenSpec validation from a clean tree.
- [x] 4.3 Obtain independent contract and code review with no unresolved P1/P2 findings.
- [x] 4.4 Generate and verify the exact candidate publication manifest and hashes.

## 5. Candidate Publication

- [ ] 5.1 Commit the isolated change atomically and push only `codex/ksrf-facts-demands-evidence-binding-20260901`.
- [ ] 5.2 Confirm the remote feature SHA and confirm `main` plus global skills remain unchanged.

## 6. Human Promotion Gate

- [ ] 6.1 Obtain separate exact-hash human approval before any merge to `main`.
- [ ] 6.2 Obtain separate exact-hash human approval before any global-skill installation.
