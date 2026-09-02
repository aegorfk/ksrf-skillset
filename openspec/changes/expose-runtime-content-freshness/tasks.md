## 1. Contract and Baseline

- [x] 1.1 Create an isolated worktree from the exact published `main`.
- [x] 1.2 Define local identity, explicit network opt-in, result states, pinning, bounds, and assurance non-goals.
- [x] 1.3 Validate the complete OpenSpec change strictly before implementation.

## 2. Test-first Runtime Contract

- [x] 2.1 Add failing parity tests for the installed runtime identity and root release manifest tree hash.
- [x] 2.2 Add failing tests proving default validation never opens the network.
- [x] 2.3 Add failing current/different/unknown tests with one resolved SHA and immutable manifest fetch.
- [x] 2.4 Add hostile-response, bounded-output, CLI compatibility, and unchanged-exit tests.

## 3. Implementation

- [x] 3.1 Compute and cross-check the local runtime tree identity without exposing file rows in runtime output.
- [x] 3.2 Implement bounded fixed-host GitHub ref and pinned-manifest reads.
- [x] 3.3 Add runtime-only `--check-updates`, stable JSON states, and concise Russian human guidance.
- [x] 3.4 Preserve offline default, source validation, runtime manifest prohibition, and all legal/publication boundaries.

## 4. Verification

- [x] 4.1 Pass focused validator and adversarial network tests with warnings fatal.
- [ ] 4.2 Pass the full root suite, all skill tests, source/runtime strict validation, offline self-containment, and clean-room installation.
- [x] 4.3 Regenerate `skills-manifest.json`, validate OpenSpec strictly, and pass diff, shell, AST, and public-source checks.
- [x] 4.4 Obtain independent security/state and user-contract reviews with no unresolved P1/P2.

## 5. Publication

- [ ] 5.1 Commit and push the isolated feature branch.
- [ ] 5.2 Merge to `main`, push, and confirm the exact live remote SHA.
- [ ] 5.3 Install the exact published `main` globally and verify runtime identity, default offline behavior, online freshness, and no `tests/` or `evals/`.
- [ ] 5.4 Archive this OpenSpec change only after publication evidence is complete.
