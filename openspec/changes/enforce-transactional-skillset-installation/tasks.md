## 1. Regression Contract

- [x] 1.1 Add deterministic fault-injection tests proving the current third-replace failure leaves a mixed/missing target before the fix.
- [x] 1.2 Add concurrent A/B writer coverage proving lock contention fails before mutation and serialized success ends in one complete generation.
- [x] 1.3 Add exact pre-install snapshots covering present and absent managed destinations, preserved development files, and unmanaged siblings.

## 2. Single-Writer Transaction

- [x] 2.1 Add a safe target-anchored advisory lock held across recovery, snapshot, staging, commit, post-verification, and cleanup.
- [x] 2.2 Stage and verify the complete same-filesystem incoming generation before any managed destination rename.
- [x] 2.3 Replace destructive deletion with journaled old-to-backup and staged-to-live renames for every managed skill.
- [x] 2.4 Compute and verify aggregate old and incoming generation identities while excluding unmanaged siblings from installer ownership.

## 3. Rollback and Durable Recovery

- [x] 3.1 Persist an atomic fsynced transaction journal with target identity, complete managed set, old presence/backup state, incoming aggregate, per-skill progress, commit, and cleanup phases.
- [x] 3.2 Roll back ordinary exceptions and `KeyboardInterrupt` in reverse order and verify the exact pre-install state before cleanup.
- [x] 3.3 Recover valid unfinished transactions idempotently on the next invocation after process death; clean committed transactions only after live aggregate verification.
- [x] 3.4 Fail closed and preserve evidence for corrupt, ambiguous, duplicated, unsafe, foreign-target, missing-backup, or unverifiable transaction state.
- [x] 3.5 Ensure rollback/recovery failures retain the only old or staged bytes and never report success.

## 4. Caller and Boundary Contract

- [x] 4.1 Keep `install.sh` and reverse synchronization on the shared Python transaction path; propagate non-zero lock/recovery failures and print export only after commit.
- [x] 4.2 Preserve exact existing behavior for runtime exclusions, stale-file removal, custom targets, canonical publication preflight, and explicit development-file preservation.
- [x] 4.3 State in implementation documentation and diagnostics that flat-layout lock-free readers do not receive a group-atomic snapshot during commit.

## 5. Verification

- [x] 5.1 Pass focused OSError, post-placement mismatch, `KeyboardInterrupt`, absent-destination, and exact rollback tests.
- [x] 5.2 Pass child-process death/recovery, corrupt-journal, missing-backup, multiple-transaction, symlink-safety, and idempotent-recovery tests.
- [x] 5.3 Pass concurrent lock, full A-to-B success, unmanaged-sibling, preserved-development, stale-file removal, and final aggregate verification tests.
- [x] 5.4 Pass `install.sh --target` clean-room tests with spaces and an apostrophe, including suppressed success/export output on failure.
- [x] 5.5 Run the complete installer, root, and skill suites plus strict source/runtime/offline validators and strict OpenSpec validation.
- [x] 5.6 Obtain independent review with no unresolved P1/P2 and inspect the diff for unsupported atomicity claims.
- [x] 5.7 Pass adversarial target-retarget, late-destination-mutation, mount/device-boundary, and temp-only pre-journal recovery tests.
- [x] 5.8 Pass adversarial forged/stale-garbage, committed-marker fsync, and globally unreachable rollback-progress tests.
- [x] 5.9 Pass held-`dir_fd` retarget-race and interrupted terminal-container cleanup-resumption tests.
- [x] 5.10 Pass ordinary and interrupted pre-prepare building-cleanup retry tests without non-terminal garbage.
- [x] 5.11 Pass process-death recovery with a stale GC journal temp before atomic replacement.

## 6. Publication and Installation QA

- [x] 6.1 Regenerate `skills-manifest.json` and verify exact release-file and release-tree hashes.
- [ ] 6.2 Commit the isolated change, merge through the approved publication workflow, push `main`, and confirm the exact live remote SHA.
- [ ] 6.3 Install the exact published `main` globally through the transactional path and verify source/runtime/offline profiles plus the installed tree hash.
- [ ] 6.4 Archive this OpenSpec change only after published and globally installed evidence is complete.
