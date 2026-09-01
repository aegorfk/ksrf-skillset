## 1. Contract and RED

- [x] 1.1 Freeze live base `f3647d0496c9ca524e68d041b3efa147e0372c64` in a dedicated worktree/branch.
- [x] 1.2 Prove the journal is source-only, size 69 194 bytes, and enumerate every runtime backlink.
- [x] 1.3 Record proposal, design, delta spec, full methodology matrix, risks and non-goals before implementation.
- [x] 1.4 Add failing tests for exact exclusion, source retention/security, reverse-sync preservation, no overmatch, clean-room backlink absence and methodology coverage.

## 2. Implementation

- [x] 2.1 Add the exact journal identity to canonical and portable source-only contracts without changing basename/glob behavior.
- [x] 2.2 Replace every runtime backlink with retained operational references and remove the offline verifier exception from installed content.
- [x] 2.3 Keep root/mirrored builder and generated JSON deterministic and free of the excluded basename.
- [x] 2.4 Update publication/user documentation and regenerate `skills-manifest.json` from the frozen live base.
- [x] 2.5 Record exact final runtime file/byte/tree reduction and source journal hash preservation.

## 3. Verification and publication

- [x] 3.1 Run focused RED/GREEN, full source suites, source strict, clean-room runtime strict, strict OpenSpec, shell syntax and diff checks.
- [x] 3.2 Confirm exact clean-room/global package, file, byte and tree hashes; confirm the journal remains tracked in source and absent from runtime.
- [x] 3.3 Obtain independent semantic-coverage and security/release review with no unresolved P1/P2.
- [ ] 3.4 Publish atomically to `main`, confirm remote SHA and install the exact global payload.
- [ ] 3.5 Archive the completed OpenSpec change and publish the final evidence commit.
