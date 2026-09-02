## 1. Contract and RED

- [x] 1.1 Freeze live base `b424e9c094e382fb230e9ce61e789883cfa19b73` in a dedicated worktree and branch.
- [x] 1.2 Inventory the target hash, six dimensions, eighteen score-cell meanings, four actions, TOC, payload membership, and consumers.
- [x] 1.3 Record proposal, design, delta spec, preservation controls, risks, and non-goals before implementation.
- [x] 1.4 Add failing tests for scalar removal, independent statuses, preserved meanings/actions/content, payload, backlink, and TOC.

## 2. Implementation

- [x] 2.1 Replace the 0–2 table with six independent qualitative checks while preserving all eighteen meanings.
- [x] 2.2 Replace score ranges with non-compensating action rules and a blocking insufficient-data rule.
- [x] 2.3 Update public documentation, record exact projections, and regenerate the manifest from the frozen live base.

## 3. Verification and publication

- [x] 3.1 Run focused RED/GREEN, all relevant suites, source strict, clean-room runtime strict, strict OpenSpec, exact payload verification, and diff checks.
- [x] 3.2 Obtain independent semantic, test, and release review with no unresolved P1/P2.
- [x] 3.3 Publish atomically to `main`, confirm remote SHA, install and verify the exact global payload.
- [x] 3.4 Archive the completed OpenSpec change and publish the final evidence commit.
