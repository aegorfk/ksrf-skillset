## 1. Contract and RED

- [x] 1.1 Freeze live base `0d4ac416f6471eccafd255eb20261b0f2c05e68d` in a dedicated worktree/branch.
- [x] 1.2 Inventory exact section boundaries, size/hash, TOC and indicator labels, all consumers, ten ownership routes, and the actual `ksrf_autocollect.py` outputs.
- [x] 1.3 Record proposal, design, delta spec, risks, non-goals, and corrected exact projection before implementation.
- [x] 1.4 Add failing tests for exact cleanup, preserved guide content/routes, payload presence, no overmatch, and the shipped collector contract. RED: the original projection produced 2 expected failures; the corrected 5-test contract produced 11 expected failures before the collector table and guide route existed.

## 2. Implementation

- [x] 2.1 Document the eight shipped or partial autocollect outputs and two explicit non-capabilities in `ksrf-tool-layer.md`.
- [x] 2.2 Remove the exact automation TOC row and mixed roadmap section only after the output contract is preserved.
- [x] 2.3 Rename exactly two automatic indicators without changing their criteria, replace exactly two dead route descriptions with shipped checks, and link the live guide to the collector contract.
- [x] 2.4 Update public documentation and regenerate the manifest from the frozen live base.
- [x] 2.5 Record exact final file and payload change: guide -5,450 bytes, tool contract +5,696 bytes, runtime net +246 bytes for the preserved exact output contract.

## 3. Verification and publication

- [x] 3.1 Run focused RED/GREEN, 602 tests across five suites, source strict 15/15 with 0/0, clean-room runtime strict 15/15 with 0/0, strict OpenSpec 14/14, exact payload verification, and diff checks.
- [x] 3.2 Obtain independent semantic, test, and release review with no unresolved P1/P2; both discovered P2 findings were fixed and re-reviewed.
- [ ] 3.3 Publish atomically to `main`, confirm remote SHA, install and verify the exact global payload.
- [ ] 3.4 Archive the completed OpenSpec change and publish the final evidence commit.
