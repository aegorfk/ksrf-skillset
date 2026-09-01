## 1. Contract and RED

- [x] 1.1 Freeze live base `4a45540a6fdb21745f58220a197c02c790f8b35d` in a dedicated worktree/branch.
- [x] 1.2 Inventory the backlog, its exact size/hash, all runtime backlinks and all 23 ownership destinations.
- [x] 1.3 Record proposal, design, delta spec, risks and non-goals before implementation.
- [x] 1.4 Add failing tests for exact exclusion, stale removal, reverse-sync preservation, no overmatch, source security and replacement routes.

## 2. Implementation

- [x] 2.1 Add the exact backlog identity to canonical and portable source-only contracts.
- [x] 2.2 Replace both runtime backlinks with shipped operational routes and leave no user-facing basename trace.
- [x] 2.3 Keep the tracked source backlog byte-identical and covered by source/repository validation.
- [x] 2.4 Update user/publication documentation and regenerate the manifest from the frozen live base.
- [x] 2.5 Record exact final file/byte/tree reduction.

## 3. Verification and publication

- [x] 3.1 Run focused RED/GREEN, full source suites, source strict, clean-room runtime strict, strict OpenSpec, shell syntax and diff checks.
- [x] 3.2 Confirm exact clean-room package, file, byte and tree hashes; confirm backlog tracked in source and absent from clean runtime.
- [x] 3.3 Obtain independent semantic-ownership and security/release review with no unresolved P1/P2.
- [ ] 3.4 Publish atomically to `main`, confirm remote SHA, install the exact global payload and verify its package/file/byte/tree hashes.
- [ ] 3.5 Archive the completed OpenSpec change and publish the final evidence commit.
