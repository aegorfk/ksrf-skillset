# ksrf-skillset-install-status Specification

## Purpose
TBD - created by archiving change expose-read-only-installer-status. Update Purpose after archive.
## Requirements
### Requirement: Status inspection issues no mutation operation
The installer SHALL provide a status mode that inspects an installation target without issuing any create, write, lock, rename, delete, sync, recovery, or cleanup operation. The report SHALL disclose that ordinary read operations may cause the filesystem to update access-time metadata.

#### Scenario: Missing target
- **WHEN** status is requested for a target path that does not exist
- **THEN** it reports `not_installed`, returns exit code 10, and leaves the target and all parents absent or byte-identical

#### Scenario: Persistent lock file is absent
- **WHEN** a safe target has no `.ksrf-install.lock`
- **THEN** status does not create it and continues the read-only classification

#### Scenario: Recovery evidence exists
- **WHEN** a transaction or GC root is present
- **THEN** status validates and reports the evidence without invoking rollback, cleanup, journal writes, fsync, unlink, rename, or flock

#### Scenario: Filesystem updates access time on read
- **WHEN** the host filesystem changes directory or file `atime` as a consequence of list/read operations
- **THEN** status still performs no explicit mutation and both human and JSON output disclose that access-time updates are possible

#### Scenario: Evidence exceeds inspection budget
- **WHEN** evidence exceeds the fixed depth, entry-count, individual-file, or total-byte budget
- **THEN** status stops before reading an oversized file and, after two matching failed observations, reports bounded `unsafe`/30 output while retaining all evidence

#### Scenario: Over-budget evidence changes between samples
- **WHEN** an entry exceeds a scan budget in the first observation but its rejected metadata or validation outcome changes before the second observation
- **THEN** status reports `recovery_required`/20 with `observation_changed` rather than presenting the first failure as stable `unsafe` evidence

#### Scenario: Direct CLI imports local helpers
- **WHEN** status is invoked from a clean source copy without Python bytecode environment overrides
- **THEN** it disables bytecode generation before local imports and creates no `__pycache__` or `.pyc` artifact

#### Scenario: File type changes before open
- **WHEN** a previously regular status input is substituted with a FIFO or another special file before `open`
- **THEN** the read-only open cannot block waiting for a peer and the post-open metadata check fails closed

### Requirement: Status classifications and exit codes are stable
Status SHALL emit schema `1.0` with `clean`/0, `not_installed`/10, `incomplete`/20, `recovery_required`/20, or `unsafe`/30, and the process exit code SHALL equal the report's `exit_code`.

`clean` confirms only that installer-owned recovery roots are absent and all 15 canonical top-level entries are observed as safe directories. It does not validate skill contents, release freshness, source equality, runtime correctness, publication authority, or filing readiness.

#### Scenario: Complete stable installation
- **WHEN** all canonical KSRF skill directories are safe and no transaction or GC root exists
- **THEN** status is `clean` with exit code 0

#### Scenario: Partial stable installation
- **WHEN** at least one but fewer than all canonical skill directories exist and no recovery root exists
- **THEN** status is `incomplete` with exit code 20 and identifies only the missing canonical skill names

#### Scenario: Structurally valid retained evidence
- **WHEN** exactly one valid pre-journal, building, prepared, rolling-back, committed, rolled-back, or terminal GC state is observed
- **THEN** status is `recovery_required` with exit code 20 and reports its kind, phase, and evidence path

#### Scenario: Ambiguous or unsafe evidence
- **WHEN** paths are symlinked, lock metadata is unsafe, roots are multiple or conflicting, or journal/layout/identity invariants fail
- **THEN** status is `unsafe` with exit code 30, retains all evidence, and reports no success

#### Scenario: Type-confused or deeply nested journal
- **WHEN** a journal uses a non-string phase, progress, or cleanup state, exceeds the JSON parser depth, or contains an integer rejected by the parser limit
- **THEN** status returns bounded `unsafe`/30 output without a traceback or raw parser detail

#### Scenario: Unsafe unpublished or garbage metadata
- **WHEN** pre-journal evidence is not owned by the current user, is group/world writable, has an unsafe temporary file, or a GC journal has a non-terminal phase
- **THEN** status reports `unsafe`/30 rather than presenting the evidence as structurally recoverable

### Requirement: Status output serves people and automation

Status SHALL provide concise Russian human output by default and deterministic JSON with bounded public fields when `--json` is selected. A clean result SHALL distinguish structural installation state from runtime content identity and online freshness. Without opening the network or executing validation, its recommended action SHALL emit a shell-quoted command that uses the current repository's validator, passes the observed target with `--skills-root`, and includes `--profile runtime --strict --check-updates`; it SHALL NOT depend on an older target-side validator or imply that reinstalling is the only way to observe freshness. If the repository validator is absent or the exact path cannot be represented as a safe shell command, status SHALL emit an honest fallback rather than a dead command. Non-clean states SHALL retain their existing action without inspecting the validator path. The guidance SHALL preserve that byte equality is not installation provenance, legal-source freshness, or filing readiness.

#### Scenario: Human clean result

- **WHEN** a user requests status without `--json`
- **THEN** the output explains the observed structural state, canonical skill count, executable repo-side runtime update-check command for the exact target, and read-only unlocked boundary in plain Russian

#### Scenario: JSON clean result

- **WHEN** automation requests clean status with `--json`
- **THEN** the stable report shape and exit code remain unchanged while `message` says content and freshness were not checked and `recommended_action` names an existing repo-side validator, the exact `--skills-root`, and `--profile runtime --strict --check-updates`

#### Scenario: Repo-side validator is absent

- **WHEN** status is invoked from a detached tool copy without the canonical validator beside it
- **THEN** recommended action says the validator is unavailable and directs the user to update the repository without emitting a nonexistent command

#### Scenario: Target path contains surrogateescaped bytes

- **WHEN** a clean POSIX target contains filesystem bytes that cannot be represented as ordinary Unicode command arguments
- **THEN** recommended action says a safe command cannot be formed and emits no misleading command for a different path

#### Scenario: Status remains offline

- **WHEN** clean status renders the runtime freshness recommendation
- **THEN** status itself invokes no network opener, validator, installer, subprocess, write, recovery, or lock operation

#### Scenario: JSON result

- **WHEN** automation requests status with `--json`
- **THEN** stdout contains one JSON object with schema version, status, severity, exit code, bounded stable reason code, target, target existence, managed-skill summary, optional transaction summary, message, recommended action, and an observation boundary declaring `explicit_mutations_performed=false`, `filesystem_access_time_updates_possible=true`, and `atomic_snapshot=false`

#### Scenario: Sensitive journal details

- **WHEN** a journal contains content identities and per-skill progress
- **THEN** status does not emit digests, journal bodies, old content, arbitrary unknown entry names, raw exceptions, or unrelated target entries

#### Scenario: Target contains surrogateescaped bytes

- **WHEN** a POSIX target argument contains bytes represented internally as unpaired surrogate code points
- **THEN** JSON and human stdout remain valid UTF-8 and render those bytes as bounded printable escapes

#### Scenario: Human recovery phase

- **WHEN** human output describes a pre-journal, building, prepared, rollback, committed, or cleanup phase
- **THEN** it uses a concise Russian phrase rather than the internal phase enum

### Requirement: Status reports concurrency limits honestly
Status SHALL treat its result as an unlocked bounded observation and SHALL not claim whether an installer process is active or whether a later installation will succeed. Retained evidence SHALL be classified from two independent comparison samples; an optimization SHALL NOT reuse a payload or mount snapshot across those samples.

#### Scenario: Stable retained transaction
- **WHEN** a valid transaction is observed without a changed root fingerprint
- **THEN** guidance says to wait if an installation is still running and otherwise rerun normal installation for validated recovery
- **AND** each of the two comparison samples traverses every evidence and live-skill payload file at most once

#### Scenario: State changes during observation
- **WHEN** the target remains anchored but any lock, canonical-skill, installer-root, journal, container, live-skill, or sampled mount-table fact determining classification changes during inspection
- **THEN** status is `recovery_required`, advises retrying after the installer finishes, and does not label the evidence corrupt

#### Scenario: Stable invalid evidence after a complete semantic sample
- **WHEN** all evidence and live-skill bytes have been sampled but a transaction state invariant fails
- **THEN** status reuses that complete sample fingerprint and does not perform an additional raw payload traversal for the same comparison sample

#### Scenario: Invalid evidence before a complete semantic sample
- **WHEN** parsing, layout, type, or budget validation fails before a complete comparable identity exists
- **THEN** status performs at most one bounded raw completion traversal for that comparison sample before applying the existing stable-invalid versus changing-evidence rule

#### Scenario: Mount discovery during retained-evidence inspection
- **WHEN** a stable retained transaction contains any number of safe nested directories
- **THEN** Linux child descriptors are compared with the target descriptor's `mnt_id`; if the target descriptor's ID is unavailable, the current live per-directory fallback remains in force, while an unavailable child ID after a target ID was established is rejected fail-closed
- **AND** hosts without Linux mountinfo do not repeatedly load an empty Linux set, while the two boundary samples remain independent and their method and target identity contribute to the comparable fingerprint

#### Scenario: Same-device bind mount is substituted
- **WHEN** a child directory has the expected device but its descriptor-bound Linux mount ID differs from the target sample mount ID
- **THEN** status rejects the child as a mount boundary without traversing it

#### Scenario: Target replacement during observation
- **WHEN** the target device or inode differs between the start and end samples
- **THEN** status is `unsafe` and no clean or recovery-safe conclusion is reported

### Requirement: Status mode is source-independent and install-compatible
Status SHALL require only `--target`; normal installation SHALL continue to require exactly one of `--repo` or `--source-skills-root` and preserve its existing success and failure behavior.

#### Scenario: Direct status invocation
- **WHEN** `tools/install_skillset.py --status --target PATH --json` is invoked without a source option
- **THEN** status runs and returns its classified process code

#### Scenario: Public shell entry point
- **WHEN** `install.sh --status [--target PATH] [--json]` is invoked
- **THEN** it runs status without publication verification, installation, or export output

#### Scenario: Invalid option combination
- **WHEN** `--json` is used without `--status`, or status is combined with source or development-preservation options
- **THEN** the CLI rejects the request as usage error before reading or changing the target

#### Scenario: Shell target value is another option
- **WHEN** `install.sh --target` is followed by `--status`, `--json`, or another option token instead of a path
- **THEN** the shell exits with usage code 2 before publication verification, target creation, or installation

### Requirement: Status anchors all relevant reads
Status SHALL hold the existing target and installer-evidence directories by read-only descriptors, perform relevant child access descriptor-relatively without following symlinks, and compare observation identities before returning a classification.

#### Scenario: Target is replaced after opening
- **WHEN** the lexical target is renamed and a byte-identical replacement appears after status opened the original directory
- **THEN** status reports `unsafe`, does not traverse the replacement, and changes neither directory

#### Scenario: Canonical skill inode changes
- **WHEN** a canonical top-level skill is replaced by byte-identical content between classification samples
- **THEN** status reports `recovery_required` rather than `clean`

#### Scenario: Evidence root is replaced
- **WHEN** a transaction or GC root path is substituted after its read-only descriptor is opened
- **THEN** status continues reading only the held evidence inode and returns no clean result

#### Scenario: Transaction-compatible semantic identity
- **WHEN** an evidence payload contains a directory descendant, a similarly prefixed sibling, or a relative name that sorts before `.`
- **THEN** status hashes all relative paths in the same global order and with the same file-byte stream as the canonical installer identity

#### Scenario: Stable malformed journal
- **WHEN** a descriptor-anchored journal remains byte-identical and violates its schema or state invariants
- **THEN** status reports `unsafe`; if its observation fingerprint changes instead, status reports `recovery_required`

#### Scenario: Invalid journal is repaired during inspection
- **WHEN** the first deep snapshot fails validation but a complete second observation succeeds or has a different evidence/live-skill fingerprint
- **THEN** status reports `recovery_required` with `observation_changed`; only two matching invalid deep snapshots may produce `unsafe`
