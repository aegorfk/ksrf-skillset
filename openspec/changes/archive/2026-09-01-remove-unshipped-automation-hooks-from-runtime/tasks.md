## 1. Contract and RED

- [x] 1.1 Freeze live base `82b7174adec78da51886112c8a941e47b9dc4b3a` in a dedicated worktree/branch.
- [x] 1.2 Inventory graph counts, evidence-map labels, generator ownership, and all repository consumers.
- [x] 1.3 Record proposal, design, delta spec, risks, preservation invariants, and non-goals before implementation.
- [x] 1.4 Add failing tests for generator source, generated artifacts, exact filtered graph preservation, evidence-map methodology preservation, malformed graphs, and a missing curated guide (27 initial plus 8 fail-closed RED outcomes).

## 2. Implementation

- [x] 2.1 Stop projecting maintainer `automation_hooks` into the graph and user-facing Markdown while preserving source-only metadata.
- [x] 2.2 Losslessly project the frozen JSON artifacts and curated Markdown evidence map without automation claims.
- [x] 2.3 Make the source-only metadata writer unable to overwrite the curated runtime evidence guide and fail before writes when that guide is absent.
- [x] 2.4 Update runtime/public documentation and regenerate the manifest from the frozen live base.
- [x] 2.5 Record exact final file, byte, node, edge, and tree reductions.

## 3. Verification and publication

- [x] 3.1 Run focused RED/GREEN, full source suites, source strict, clean-room runtime strict, strict OpenSpec, syntax, and diff checks.
- [x] 3.2 Obtain independent semantic and release review with no unresolved P1/P2.
- [x] 3.3 Publish atomically to `main`, confirm remote SHA, install the exact global payload, and verify package/file/byte/tree hashes.
- [x] 3.4 Archive the completed OpenSpec change and publish the final evidence commit.
