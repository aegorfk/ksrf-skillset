## 1. Contract

- [x] 1.1 Start from the exact published `main` in an isolated worktree.
- [x] 1.2 Define explicit-network, exit-code, compatibility, and legal-assurance boundaries.
- [x] 1.3 Strictly validate the complete OpenSpec change before tests or implementation.

## 2. Test First

- [x] 2.1 Add RED validator tests for `--require-current` current/different/unknown and invalid combinations.
- [x] 2.2 Add RED shell tests for exact delegation, target forwarding, JSON rejection, conflicts, and no install/publication side effects.
- [x] 2.3 Add RED status-guidance tests for the short exact command and fail-honest fallbacks.

## 3. Implementation

- [x] 3.1 Implement additive validator exit semantics without changing default behavior or report schemas.
- [x] 3.2 Implement `install.sh --verify-current` and update status guidance.
- [x] 3.3 Update Russian README/help and regenerate the release manifest.

## 4. Verification and Publication

- [x] 4.1 Pass focused/full QA, strict validators, OpenSpec, AST/shell/public guards, and clean-room checks.
- [x] 4.2 Obtain independent review with no unresolved P1/P2.
- [ ] 4.3 Commit/push the feature branch, merge/publish exact `main`, install globally, and verify live SHA.
- [ ] 4.4 Archive the OpenSpec change and publish the final manifest-bound release commit.
