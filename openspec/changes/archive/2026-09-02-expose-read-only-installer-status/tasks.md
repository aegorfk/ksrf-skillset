## 1. Change Contract

- [x] 1.1 Create the isolated branch/worktree and OpenSpec proposal.
- [x] 1.2 Define the read-only status schema, classifications, exit codes, concurrency boundary, and non-goals.
- [x] 1.3 Validate the complete OpenSpec change in strict mode before implementation.

## 2. Test-First Status Contract

- [x] 2.1 Add failing API tests for clean, not-installed, incomplete, valid recovery, unsafe, and changing observations.
- [x] 2.2 Add failing tests proving status creates no target, lock, journal, temporary path, flock, fsync, rename, unlink, or cleanup side effect.
- [x] 2.3 Add failing direct-CLI and `install.sh` tests for human output, JSON, exit-code parity, source independence, and invalid option combinations.
- [x] 2.4 Add adversarial fixtures for symlinked paths, unsafe lock metadata, multiple/conflicting roots, malformed journals, and target replacement.

## 3. Read-Only Inspector

- [x] 3.1 Extract pure validation for safe pre-journal transaction evidence and retain it in the existing cleanup path.
- [x] 3.2 Implement target, lock, managed-skill, transaction, and GC inspection using only read operations.
- [x] 3.3 Implement stable status reports, target/root change detection, and bounded error mapping without leaking journal digests.

## 4. CLI and User Experience

- [x] 4.1 Add `--status --target PATH [--json]` while preserving normal source-required installation behavior.
- [x] 4.2 Add `install.sh --status [--target PATH] [--json]` without publication verification, mutation, success export, or install output.
- [x] 4.3 Add concise Russian human rendering and document usage, exit codes, limits, and recovery guidance in README.

## 5. Verification

- [x] 5.1 Pass focused status and existing transactional installer tests with warnings/resource leaks treated as failures.
- [x] 5.2 Pass the full root suite, all skill tests, strict source/runtime validators, offline self-containment, and clean-room installation.
- [x] 5.3 Verify zero filesystem diffs for status fixtures and no `tests`/`evals` in runtime installation.
- [x] 5.4 Regenerate `skills-manifest.json`, run `git diff --check`, and validate OpenSpec strictly.
- [x] 5.5 Add and pass audit regressions for bytecode writes, FIFO substitution, JSON type/depth failures, unsafe pre-journal/GC metadata, globally ordered semantic identity, deep invalid re-observation, valid UTF-8 output for surrogateescaped paths, disclosed `atime` behavior, bounded evidence I/O, over-budget evidence changing between samples, and Russian shell/direct-CLI help and usage errors.
- [x] 5.6 Obtain independent security/state and user-facing CLI reviews with no unresolved P1/P2.

## 6. Publication

- [x] 6.1 Commit the isolated change and push the feature branch.
- [x] 6.2 Merge through the approved publication workflow, push `main`, and confirm the exact live remote SHA.
- [x] 6.3 Install the exact published `main` globally and verify runtime/offline status plus the installed tree hash.
- [x] 6.4 Archive this OpenSpec change only after publication and global-install evidence are complete.
