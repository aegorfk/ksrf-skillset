## 1. Contract and RED

- [x] 1.1 Freeze live base `b76026d1f16cc0d8c634a8ede8004ad5864545ff` and isolate the topic in its own worktree/branch.
- [x] 1.2 Measure the exact five-file source-only candidate set: 164 081 bytes; verify zero runtime-consumer backlinks and identify active near-neighbours that must remain installed.
- [x] 1.3 Record proposal, design, modified spec, risks, non-goals, and migration before implementation.
- [x] 1.4 Add failing canonical contract/install tests for exact exclusion, cross-skill/similar-name non-overmatch, clean target replacement, and reverse-sync byte preservation.
- [x] 1.5 Add failing portable validator tests for manifest parity, source security/public-source coverage, and runtime rejection of stale exact artifacts.

## 2. Implementation

- [x] 2.1 Add a versioned `skill name + exact relative path` source-only predicate to the canonical file contract.
- [x] 2.2 Use the same predicate for payload enumeration, reverse-sync preservation, and manifest exclusion metadata.
- [x] 2.3 Mirror the exact contract in the standalone validator without weakening source checks or ordinary JSON/script eligibility.
- [x] 2.4 Update user/publication docs and regenerate `skills-manifest.json` from the frozen live base.

## 3. Verification and publication

- [x] 3.1 Run focused RED/GREEN, all source suites, source strict validator, clean-room runtime strict validator, strict OpenSpec, shell syntax, and diff checks.
- [x] 3.2 Confirm exact clean-room/global file, byte, package, and tree hashes; assert all five paths plus tests/evals are absent while source bytes remain.
- [x] 3.3 Obtain independent review with no unresolved P1/P2.
- [x] 3.4 Publish atomically to `main`, confirm remote SHA, install the exact global payload, and verify source-only artifacts remain in the repository.
- [x] 3.5 Archive the completed OpenSpec change and publish the final evidence commit.
