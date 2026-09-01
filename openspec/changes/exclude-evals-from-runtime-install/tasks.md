## 1. Baseline and RED

- [x] 1.1 Freeze live base `925d8fb4848e1373e64b78a318750f45bcf107f1` and isolate the change in its own worktree.
- [x] 1.2 Record proposal, design, delta spec, risks, and migration before implementation.
- [x] 1.3 Measure exact eval file/byte savings on the live base: 30 files / 94 270 bytes.
- [x] 1.4 Add failing validator profile tests: source still fails without evals, clean runtime can pass, source-only artifacts block runtime, report/manifest scope is explicit, unknown profile fails closed.
- [x] 1.5 Add failing install/manifest/reverse-sync tests for excluding and preserving evals.

## 2. Implementation

- [x] 2.1 Add explicit `source|runtime` profiles while keeping source as the default.
- [x] 2.2 Skip only eval-specific checks in runtime profile and label JSON/text assurance honestly.
- [x] 2.3 Add exact `evals` path component to canonical and portable development-only boundaries.
- [x] 2.4 Preserve tests and evals byte-for-byte during reverse sync.
- [x] 2.5 Update generated manifest exclusions and regenerate from the exact live base.
- [x] 2.6 Replace installed instructions that would require absent evals and document the source/runtime split.
- [x] 2.7 Make source-release eligibility depend on canonical public-source safety coverage, including source-only eval assets.

## 3. Verification and publication

- [x] 3.1 Run focused RED/GREEN, complete source tests, source strict validator, runtime clean-room strict validator, and strict OpenSpec.
- [x] 3.2 Confirm clean-room/global exact file, byte, package, and tree hashes; assert tests=0 and evals=0.
- [x] 3.3 Obtain independent review with no unresolved P1/P2.
- [ ] 3.4 Publish atomically to `main`, confirm remote SHA, install exact global payload, and verify source development assets remain.
- [ ] 3.5 Archive the completed OpenSpec change and publish the final evidence commit.
