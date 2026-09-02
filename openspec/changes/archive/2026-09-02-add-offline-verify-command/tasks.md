## 1. Contract

- [x] 1.1 Define the additive `--verify` user contract, assurance boundary, and stable exit codes.
- [x] 1.2 Assign the behavior to the existing installation-status capability without duplicating the validator or content-identity algorithm.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. Test-Driven Implementation

- [x] 2.1 Add failing wrapper tests for valid, invalid, unsafe, and mutually exclusive `--verify` invocations.
- [x] 2.2 Add no-network, no-install, exact-target, and repo-side-validator assertions.
- [x] 2.3 Add failing coordinator/validator tests for preflight-to-postflight root and content replacement.
- [x] 2.4 Implement the expected-root validator guard and stable offline final identity pass.
- [x] 2.5 Implement the repo-side coordinator and delegate both public verification modes without changing their public outcomes.
- [x] 2.6 Preserve every existing install, status, JSON, and online-verification mode.

## 3. User Guidance

- [x] 3.1 Add the short offline command and its boundary to README installation guidance.
- [x] 3.2 Update the complaint-cycle operator guidance to prefer the public repo-side wrapper when available.
- [x] 3.3 Regenerate the exact runtime manifest after runtime documentation changes.

## 4. Verification and Publication

- [x] 4.1 Pass focused and full tests, strict source/runtime validators, shell syntax, OpenSpec, and diff checks.
- [x] 4.2 Prove clean-room offline success, validation failure, absence of network access, and no installed tests/evals.
- [x] 4.3 Obtain independent review with no unresolved P1/P2.
- [x] 4.4 Commit/push the feature branch, merge/publish exact `main`, install globally, and verify the live release.
- [x] 4.5 Archive the OpenSpec change and publish the final manifest-bound commit.
