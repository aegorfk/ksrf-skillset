## 1. Change Contract

- [x] 1.1 Create an isolated worktree from the exact published `main`.
- [x] 1.2 Define semantic-first sampling, bounded fallback, mount-snapshot scope, measurable I/O targets, and non-goals.
- [x] 1.3 Validate the complete OpenSpec change in strict mode before implementation.

## 2. Baseline and Test-First Contract

- [x] 2.1 Record current complete-payload read and mount-discovery counts for valid, late-invalid, and early-invalid retained evidence.
- [x] 2.2 Add failing tests requiring one complete traversal per comparison sample for valid and late-invalid evidence.
- [x] 2.3 Add failing tests for descriptor-bound Linux mount IDs, live Linux fallback, and zero repeated empty-set discovery on non-Linux hosts.
- [x] 2.4 Preserve changing-evidence, stable-invalid, oversized-before-read, no-write, FD, and public-output regressions.

## 3. Observation Refactor

- [x] 3.1 Make semantic validation primary and reuse complete fingerprints for valid and late-invalid observations.
- [x] 3.2 Retain one bounded raw completion scan for early-invalid observations without unbounded retries.
- [x] 3.3 Use descriptor-bound Linux mount IDs with a fingerprint-bound boundary method per comparison sample, retaining the live Linux fallback when descriptor IDs are unavailable.
- [x] 3.4 Keep standalone helper behavior and normal installation semantics unchanged.

## 4. Verification

- [x] 4.1 Pass focused performance/adversarial status tests with resource warnings fatal.
- [x] 4.2 Pass the full root suite, all skill tests, source/runtime strict validation, offline self-containment, and clean-room installation.
- [x] 4.3 Regenerate `skills-manifest.json`, validate OpenSpec strictly, and pass `git diff --check` plus shell/AST checks.
- [x] 4.4 Obtain independent performance/state and security reviews with no unresolved P1/P2.

## 5. Publication

- [ ] 5.1 Commit and push the isolated feature branch.
- [ ] 5.2 Merge to `main`, push, and confirm the exact live remote SHA.
- [ ] 5.3 Install the exact published `main` globally and verify status, runtime/offline validation, and installed tree hash.
- [ ] 5.4 Archive this OpenSpec change only after publication evidence is complete.
