## 1. Contract and RED

- [x] 1.1 Freeze live base `54a3b7cb7b08844aa4d46c1dfd5052aa30333681` in a dedicated worktree/branch.
- [x] 1.2 Prove both nested files are byte-identical to root tools, total 69 462 bytes, and have no runtime consumers.
- [x] 1.3 Record proposal, design, delta spec, risks, non-goals, and migration before implementation.
- [x] 1.4 Add failing tests for ownership classes, release coverage, exact stale-path behavior, reverse-sync preservation, and root enrich default.

## 2. Implementation

- [x] 2.1 Introduce disjoint mirrored/root-only/retired ownership in the canonical file contract and preserve root-only release hashes.
- [x] 2.2 Mirror the exact retired runtime identities in the portable validator without overmatching.
- [x] 2.3 Fix the root enrich default, delete only the two nested duplicates, and update active OpenSpec/publication references.
- [x] 2.4 Regenerate `skills-manifest.json` from the frozen live base and record exact net runtime reduction.
- [x] 2.5 Close review findings with a root-only release content scanner and canonical/portable fail-closed duplicate-presence gates.

## 3. Verification and publication

- [x] 3.1 Run focused RED/GREEN, full source suites, both tool `--help` smokes, source strict, clean-room runtime strict, strict OpenSpec, shell syntax, and diff checks.
- [x] 3.2 Confirm exact clean-room/global package, file, byte, and tree hashes; confirm root-only source hashes and nested absence.
- [x] 3.3 Obtain independent review with no unresolved P1/P2.
- [ ] 3.4 Publish atomically to `main`, confirm remote SHA, and install the exact global payload.
- [ ] 3.5 Archive the completed OpenSpec change and publish the final evidence commit.
