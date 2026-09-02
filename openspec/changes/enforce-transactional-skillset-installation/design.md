## Context

`copy_skillset()` currently validates source and target boundaries, computes the source payload, copies every managed skill into a private directory below the target, and verifies every staged tree. Publication then loops over `SKILL_NAMES`: it recursively deletes an existing destination and renames the staged directory into place. The `finally` block always deletes staging. There is no target lock, old-generation backup, transaction journal, rollback, stale-transaction recovery, or aggregate verification of the published target.

That structure protects the target from most preflight and staging failures, but it does not protect the commit phase. An injected failure on the third `Path.replace()` deterministically leaves two skills from the new source, one absent, and twelve from the old source. Concurrent A/B installs can interleave their per-skill replacements and both report success with a hybrid final tree.

The target is a flat skills directory that may also contain unrelated Codex skills and files. Replacing the whole target is therefore out of scope. Standard portable filesystem operations also cannot atomically swap fifteen non-empty sibling directories as a group. This design provides strict single-writer, rollback-at-return, durable next-run recovery, and exact final verification without claiming lock-free reader atomicity.

## Goals

- Prevent two cooperating installers from mutating the same target concurrently.
- Ensure any handled exception or `KeyboardInterrupt` restores the exact pre-install state of every managed KSRF destination.
- Leave enough durable, verified information to recover conservatively after uncatchable process death.
- Fail closed without further target mutation when recovery evidence is corrupt or ambiguous.
- Verify that a successful return exposes one complete incoming KSRF generation, never a mixed or missing managed tree.
- Preserve unrelated target siblings and the existing explicit development-file preservation mode.
- Keep the implementation local, deterministic, offline, and shared by all installer callers.

## Non-Goals

- Promise that a process reading skill paths without the installer lock observes a group-atomic snapshot during commit.
- Replace the complete Codex skills root, convert it to a symlink, introduce a generation-pointer layout, or change how Codex discovers skills.
- Modify any installed KSRF skill, runtime schema, legal workflow, CLI route, approval gate, or filing boundary.
- Add network retrieval, model calls, remote locks, a daemon, or background cleanup.
- Automatically repair unknown historical damage that lacks a valid journal and complete backups.

## Decisions

### 1. One lock serializes every writer to the actual target

The Python installer SHALL canonicalize the actual target and acquire exclusive non-blocking advisory locks on both its held parent-directory descriptor and its regular target lock file before it snapshots, preserves, recovers, stages against, or replaces any managed destination. The parent lock prevents a renamed-and-recreated target from admitting a second cooperating writer, while held parent, target-directory, and lock-file descriptors let every destructive boundary revalidate the same device/inode identities. Every managed old-to-backup, staged-to-live, live-to-quarantine, and backup-to-live rename SHALL resolve both relative paths through the held target-directory descriptor, so a retarget between pathname checks cannot redirect that mutation into a replacement directory. The lock identity SHALL converge for path aliases to the same actual target. The lock file inode, owner, link count, and non-group-writable mode SHALL be checked after acquisition. The lock file may persist between runs; unlinking a held lock is forbidden because it would allow a second inode to bypass the file lock.

If another writer holds the lock, the second invocation SHALL exit non-zero with a stable actionable error before reading preservable development files or mutating any managed skill or transaction directory. `install.sh`, canonical installation, custom installation, and reverse synchronization SHALL all inherit this same lock by calling the Python installer rather than implementing separate locking.

### 2. Staging remains complete and same-filesystem

All incoming runtime files and any explicitly preserved development files SHALL be copied and verified before the first destination rename. Staging, transaction backups, and destinations SHALL reside on the same filesystem so directory renames retain their atomic per-path semantics. Every owned-tree traversal SHALL reject symlinks, special files, hard links, nested mount points, and device boundaries before descent; cleanup SHALL delete only the previously validated bottom-up inode set rather than recursively following a newly exposed subtree. The installer SHALL compute a canonical expected aggregate over all managed skill names, relative payload paths, content digests, and explicit preserved-development digests.

No pre-existing destination is recursively deleted during forward commit. Each present managed destination is rehashed immediately before its rename, renamed into the transaction's backup area, and rehashed there before publication continues; an absent destination is recorded and rechecked explicitly. A late target mutation therefore blocks with its bytes retained in live or backup evidence rather than being silently discarded. Only then is the verified staged directory renamed into its managed path. Unmanaged siblings are never moved, copied, hashed as owned payload, deleted, or restored.

### 3. The journal is durable before destructive renames

Before the first managed destination moves, the installer SHALL create one uniquely identified transaction directory and an atomic journal containing at least:

- schema version, transaction ID, normalized target identity and phase;
- exact ordered managed-skill set;
- expected incoming aggregate digest;
- for each skill, whether the old destination existed and the expected backup identity;
- durable progress sufficient to distinguish old-to-backup and staged-to-live transitions; and
- commit and cleanup state.

Journal updates SHALL use write-to-temp plus atomic replace and fsync the journal file and relevant directory before the corresponding destructive transition is allowed. A failure to fsync a renamed committed marker SHALL report failure and retain the transaction rather than reinterpret page-cache bytes as a durable success. A temp-only transaction left before the initial journal publication may be removed only when its exact safe pre-mutation shape is proved. When a valid older journal coexists with a regular temp file after process death before replace, recovery SHALL first validate the older journal and physical state, then discard the uncommitted temp before retrying any journal transition. Backup and staged paths SHALL be strict regular directories below the validated transaction root, without symlink or mount traversal. Multiple unfinished transaction directories, mismatched target IDs, unknown schema or phase, unsafe paths, absent required backups, an unreachable global forward/rollback progress vector, or internally inconsistent physical state make recovery ambiguous and SHALL fail closed.

### 4. Handled failures restore the exact previous state

The transaction boundary SHALL catch ordinary exceptions and `KeyboardInterrupt`, roll back in reverse managed-skill order, and then re-raise or return non-zero. Before an incoming live directory is displaced during rollback, its exact identity and the required old backup SHALL be proved. The incoming directory SHALL then move atomically into transaction-owned quarantine rather than being recursively deleted from the live target. For a destination that existed before installation, rollback SHALL rename the exact backup into its original path; for a destination that was absent, rollback SHALL restore absence. It SHALL then verify the complete pre-install state recorded by the journal.

If rollback verification succeeds, temporary transaction data may be cleaned safely. If any rollback step or verification fails, the installer SHALL retain the journal, backups, and diagnostics, return non-zero, and refuse to report the target as restored. It SHALL never delete the only remaining old or staged bytes in a `finally` block.

### 5. Process death is recovered before a new transaction

An uncatchable termination may stop between per-directory renames. On the next invocation, after acquiring the target lock and before creating new staging, the installer SHALL inspect installer-owned transaction state:

- an unfinished valid transaction without a durable commit marker is conservatively rolled back to the exact recorded pre-install state;
- a transaction with a durable commit marker is cleaned only after the current target revalidates to the recorded incoming aggregate;
- a supposedly committed target that fails aggregate verification is not guessed or overwritten and remains blocked for explicit recovery; and
- corrupt, incomplete, duplicated, symlinked, foreign-target, or otherwise ambiguous state is reported and preserved without further managed-target mutation.

Recovery SHALL be idempotent: interruption during recovery leaves a journal state from which the same conservative outcome can be retried. A `building` transaction has not renamed any managed destination; after the recorded old generation is reverified and backup/quarantine are proved empty, its partial staging is removed beneath the still-durable building journal, with that journal deleted last. It SHALL NOT be relabeled as terminal garbage merely to reuse committed cleanup. A new installation may begin only after recovery has reached and verified one terminal old or committed generation or has safely discarded such a pre-mutation building transaction.

### 6. Success is declared only after aggregate verification

After all staged directories are live, the installer SHALL recompute the aggregate managed payload and preserved-development digests from the target. Any missing skill, stale file, unexpected runtime file, digest mismatch, mixed generation, or preservation mismatch triggers rollback before success is printed. Only an exact aggregate may receive a durable committed journal phase. After a verified commit or rollback, the complete transaction directory SHALL first move atomically to a transaction-owned garbage name and fsync the target. Before initial or resumed garbage deletion, the installer SHALL reload the journal, prove its terminal phase and target identity, revalidate the corresponding live aggregate, and validate every remaining owned artifact; unproved garbage is evidence and is never deleted by name alone. Each top-level container moves through a durable, globally reachable `pending -> deleting -> deleted` cleanup vector. Exact recorded digests are required before `deleting`; once that intent is durable, a partial remaining subtree may be deleted only after the same name/type/link/mount/device safety checks. The terminal journal is deleted last, and an empty validated garbage root is the only journal-free cleanup residue that may be removed. A process death during safe bottom-up garbage deletion therefore cannot turn a valid terminal generation into an ambiguous active transaction, and the next locked invocation may finish only revalidated stale-garbage cleanup.

`install.sh` SHALL print `KSRF_SKILLS_ROOT` only after the Python installer has committed successfully. Lock contention, rollback, recovery failure, or corruption SHALL propagate as non-zero and SHALL not print a success or export line.

### 7. The reader consistency boundary remains explicit

The lock makes writers serial and guarantees exact terminal states at successful or successfully rolled-back return. It does not make fifteen directory renames a single filesystem operation. A reader that does not participate in the installer lock can observe a short mixed or missing window during commit or crash recovery. Tests, documentation, and final reporting SHALL call this out explicitly and SHALL NOT label the flat-layout installer fully atomic for lock-free readers.

A future generation directory plus one atomic pointer switch could close this reader-observation gap, but it would change target layout and skill discovery and is not part of this minimal hardening.

## Risks and Mitigations

- **Rollback destroys the only old copy:** old destinations are renamed, never deleted, and backups are removed only after a durable verified commit.
- **Process death during journal update:** atomic journal replacement plus fsync ensures recovery sees either the prior valid state or the next valid state.
- **Concurrent path aliases bypass locking:** the lock is anchored in the actual target and its file safety is revalidated under the acquired descriptor.
- **Target path is renamed and recreated while locked:** the held parent-directory lock blocks a second cooperating writer, canonical operations and inode guards reject the replacement path, and recovery is not attempted against a different inode.
- **Target changes inside a rename check window:** managed renames use held-target `dir_fd` resolution, so the operation remains attached to the original inode and the post-check blocks further work.
- **Nested mount is mistaken for owned bytes:** all hashing and cleanup stop before mount/device boundaries, and deletion uses only a prevalidated inode list.
- **Stale garbage name is forged:** terminal journal, target generation, progress, and artifact identities are revalidated before deletion.
- **Stale or malicious transaction artifacts:** strict owned-name, path, type, target-ID, schema, set, and digest checks fail closed without guessing.
- **Rollback itself is interrupted:** progress is journaled and recovery operations are idempotent.
- **Staging fails before prepare:** partial staging remains governed by its building journal and is retryably removed without creating non-terminal garbage.
- **Post-install hybrid is reported as success:** aggregate verification occurs against the live target before the commit marker and success output.
- **Unrelated skills are damaged:** ownership is restricted to `SKILL_NAMES` and installer metadata; fixtures prove unmanaged siblings remain byte-identical.
- **Transactional overclaim:** the specification states the lock-free reader limitation and defers true group-atomic visibility to a separate layout change.

## Verification

- Inject an `OSError` before and after selected destination renames and prove exact all-skill rollback, including previously absent destinations.
- Inject `KeyboardInterrupt` at the same boundaries and prove identical rollback behavior.
- Terminate a child process with `os._exit()` after backup and after live placement, then prove the next invocation recovers the exact old generation before starting any new transaction.
- Hold the target lock in one process and prove a second installer exits non-zero before target mutation; run serialized A then B installs and prove the final tree is wholly B.
- Rename and recreate the target after real lock acquisition; prove the second writer is refused and neither writer installs into the replacement path.
- Mutate a destination after its old snapshot, inject a nested device boundary, fail the initial journal publish, and fail committed-marker fsync; prove fail-closed retention and retry behavior.
- Forge stale-garbage state and an unreachable rollback progress vector; prove neither live nor evidence bytes are mutated.
- Interrupt deletion inside a terminal backup container; prove the durable cleanup intent admits safe idempotent resumption without weakening validation of untouched containers.
- Fail a staged file copy and interrupt cleanup of that partial staging; prove both ordinary and interrupted building cleanup leave the old generation exact and retries unblocked.
- Terminate GC cleanup after fsync of a journal temp but before its replace; prove the older durable state remains authoritative and retry discards the stale temp before advancing.
- Corrupt or remove journal/backup fields, add a second unfinished transaction, and introduce unsafe symlinks; prove recovery refuses without further managed-tree changes.
- Complete an A-to-B install and prove exact aggregate B, no stale runtime files, no unfinished transaction artifacts, preserved development files when requested, and byte-identical unmanaged siblings.
- Run `install.sh --target` against a path containing spaces and an apostrophe; prove export is printed only on committed success and suppressed on lock/recovery failure.
- Run installer tests, full root and skill suites, source/runtime/offline validators, exact clean-room installation, manifest regeneration/verification, strict OpenSpec validation, and independent review with no unresolved P1/P2.
