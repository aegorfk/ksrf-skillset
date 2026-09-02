# ksrf-skillset-install-transaction Specification

## Purpose
TBD - created by archiving change enforce-transactional-skillset-installation. Update Purpose after archive.
## Requirements
### Requirement: Skillset installation is single-writer and rollback-safe

The KSRF skillset installer MUST canonicalize the actual target and acquire one exclusive target-scoped writer lock, anchored by held parent, target-directory, and lock-file descriptors, before reading preservable target state or mutating any managed skill. Every managed rename MUST resolve relative to the held target-directory descriptor. It MUST stage and verify the complete incoming generation before commit, preserve each previous managed destination by same-filesystem rename rather than destructive deletion, and verify the aggregate live generation before success. Any ordinary exception or `KeyboardInterrupt` MUST restore and verify the exact pre-install state of every managed skill, including recorded absence, while leaving unmanaged target siblings byte-identical. Lock contention or target-inode replacement MUST exit non-zero before mutation of the replacement path.

#### Scenario: Failure occurs after some skills were replaced

- **WHEN** an exception or `KeyboardInterrupt` occurs after one or more managed destinations have moved or received staged content
- **THEN** the installer rolls back every managed destination to the exact pre-install generation, reports failure, retains recovery evidence if rollback is incomplete, and does not print success

#### Scenario: Two writers target the same directory

- **WHEN** one installer holds the target transaction lock and another installer starts through any path alias to the same target
- **THEN** the second installer exits non-zero before reading preservable development files or mutating managed skills, and the first writer alone may proceed

#### Scenario: The locked target is renamed and recreated

- **WHEN** the target path is replaced after the first installer acquires its real lock and a second installer starts against the recreated path
- **THEN** the held parent lock refuses the second writer, inode guards stop the first writer from touching the replacement target, and automatic recovery is not attempted against the different inode

#### Scenario: A destination changes after its old snapshot

- **WHEN** a managed destination's identity changes before or during its move into the backup slot
- **THEN** the installer reports failure, retains the changed bytes in live or transaction evidence, and does not publish or delete them as if they matched the recorded old identity

#### Scenario: An owned tree crosses a mount or device boundary

- **WHEN** source, live, staged, backup, quarantine, or garbage traversal encounters a nested mount point or different device
- **THEN** traversal stops before descent, installation or cleanup exits non-zero, and bytes beyond that boundary are not deleted

#### Scenario: Installation succeeds

- **WHEN** staging, publication and aggregate live-target verification all complete
- **THEN** every managed skill belongs to the same exact incoming generation, stale managed runtime files are absent, explicit development preservation is honored, unmanaged siblings are unchanged, and success is printed only after a durable commit marker

#### Scenario: A managed destination was initially absent

- **WHEN** a handled failure occurs after the installer created a skill that did not exist before the transaction
- **THEN** rollback removes that incoming destination and restores its recorded absent state without changing unrelated target entries

### Requirement: Interrupted transactions recover durably and fail closed

Before the first managed-directory rename, the installer MUST persist and fsync a versioned transaction journal that binds the exact target, ordered managed set, old identities and presence, fixed planned backup slots, incoming aggregate, globally reachable per-skill progress, commit state, and globally reachable per-container cleanup progress. Each present old directory becomes the exact backup by same-filesystem rename immediately before that destination is replaced. On the next invocation after process death, the installer MUST acquire the same lock and idempotently restore an uncommitted valid transaction to its exact old generation before beginning new work. It MAY clean a durably committed transaction or transaction-derived garbage only after reloading its terminal journal and revalidating the live target against the recorded aggregate. A partially deleted container is resumable only after a durable `deleting` intent; untouched `pending` containers still require exact recorded identities, and the terminal journal is deleted last. Corrupt, incomplete, duplicated, symlinked, foreign-target, missing-backup, forged-garbage, unreachable-progress or otherwise ambiguous recovery state MUST block without further managed-target mutation or deletion of recovery evidence.

#### Scenario: Process dies before durable commit

- **WHEN** a process terminates after a destination is backed up or replaced but before a durable commit marker exists
- **THEN** the next installer invocation rolls the valid journal back to the exact old generation, verifies recovery, and only then may start a new transaction

#### Scenario: Staging fails before the transaction is prepared

- **WHEN** copying or verifying incoming files fails while the durable journal remains in `building` and no managed destination has moved
- **THEN** the installer revalidates the exact old live generation, proves backup and quarantine empty, removes partial staging under the retained building journal with that journal last, and leaves no non-terminal garbage; interruption of this cleanup remains retryable from the same building journal

#### Scenario: Process dies after durable commit

- **WHEN** a process terminates after the commit marker but before backup cleanup
- **THEN** the next invocation verifies the complete incoming aggregate and then safely finishes cleanup without reverting a valid committed installation

#### Scenario: Recovery is interrupted

- **WHEN** process death occurs while an unfinished transaction is being recovered
- **THEN** the journal remains sufficient for the next invocation to repeat recovery toward the same conservative terminal state

#### Scenario: Journal or backup state is ambiguous

- **WHEN** the installer finds an unknown journal schema or phase, inconsistent target ID, multiple unfinished transactions, unsafe path or symlink, missing required backup, or aggregate mismatch that cannot be proved safe
- **THEN** it exits non-zero, identifies the retained recovery location, and performs no further mutation of managed skills or recovery evidence

#### Scenario: Committed marker directory fsync fails

- **WHEN** the committed journal rename occurs but durability of its containing directory cannot be confirmed
- **THEN** the current invocation reports failure, retains journal and backup evidence, and does not reinterpret the visible marker as successful cleanup

#### Scenario: Transaction-derived garbage is stale or forged

- **WHEN** a later invocation encounters an installer garbage name after interrupted cleanup or unproved namespace creation
- **THEN** it reloads and validates a terminal journal, the corresponding live generation, and remaining owned artifacts before deletion; otherwise it fails closed and retains all evidence

#### Scenario: Process dies during terminal garbage deletion

- **WHEN** a process removes only part of a container after its durable cleanup intent and terminates before marking that container deleted
- **THEN** the next invocation revalidates the terminal live generation and cleanup vector, safely finishes the partial container, and continues cleanup without demanding its already removed bytes or weakening exact checks for untouched containers

#### Scenario: Process dies before a cleanup journal replacement

- **WHEN** the next journal payload is fsynced to its temporary file but the process terminates before atomic replacement of the older valid journal
- **THEN** recovery treats the older journal as authoritative, revalidates its terminal state and physical artifacts, discards the uncommitted regular temp file, and retries the cleanup transition without permanent blockage

### Requirement: Installation reports its reader consistency boundary honestly

The installer and its public guidance MUST distinguish serialized writer safety and exact terminal-state recovery from group-atomic visibility. Under the current flat fifteen-directory layout, it MUST NOT claim that readers which do not acquire the installer lock observe one atomic snapshot during commit or crash recovery. `install.sh` MUST use the shared transaction implementation, propagate lock and recovery failures, and print a shell-safe `KSRF_SKILLS_ROOT` export only after committed success.

#### Scenario: Lock-free reader observes installation

- **WHEN** a process reads managed skill paths without participating in the installer lock while commit or recovery is in progress
- **THEN** no guarantee of a group-atomic fifteen-directory snapshot is claimed, even though the installer guarantees serialized writers and an exact verified terminal state

#### Scenario: Shell wrapper encounters lock or recovery failure

- **WHEN** `install.sh` receives a non-zero result from lock acquisition, rollback or recovery
- **THEN** it exits non-zero and prints neither an installation-success message nor a `KSRF_SKILLS_ROOT` export

#### Scenario: Custom clean-room target contains unrelated entries

- **WHEN** installation runs against a target containing non-KSRF directories or files
- **THEN** only the declared KSRF skill destinations and validated installer-owned transaction metadata are touched, and every unmanaged sibling remains byte-identical
