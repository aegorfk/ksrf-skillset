## 1. Contract

- [x] 1.1 Create an isolated worktree from the exact published `main`.
- [x] 1.2 Define the status/freshness boundary, exact user guidance, and non-goals.
- [x] 1.3 Validate the complete OpenSpec change strictly before implementation.

## 2. Test First

- [x] 2.1 Add a failing clean JSON test requiring the exact runtime update-check route.
- [x] 2.2 Add a failing Russian human-output test that distinguishes structure, content, and freshness.
- [x] 2.3 Prove status remains offline and does not invoke validation or installation.

## 3. Implementation

- [x] 3.1 Update clean-state message and recommended action without changing schema or exits.
- [x] 3.2 Align README wording with the new status recommendation and assurance limits.

## 4. Verification and Publication

- [x] 4.1 Pass focused and full QA, strict validators, OpenSpec, manifest, AST/shell, and clean-room checks.
- [x] 4.2 Obtain independent review with no unresolved P1/P2.
- [ ] 4.3 Commit and push the feature branch, merge and publish exact `main`, install it globally, and verify live SHA.
- [ ] 4.4 Archive the OpenSpec change and publish the final manifest-bound release commit.
