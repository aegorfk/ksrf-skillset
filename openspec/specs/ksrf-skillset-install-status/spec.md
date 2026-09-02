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

Status SHALL provide concise Russian human output by default and deterministic
JSON with bounded public fields when `--json` is selected. A clean result SHALL
distinguish structural installation state from runtime content identity and
online freshness. Without opening the network or executing validation, its
recommended action SHALL emit two ordered shell-quoted absolute commands from
the current repository for the exact target: first
`<repo>/install.sh --verify --target <exact target>` for local offline
integrity, then `<repo>/install.sh --verify-current --target <exact target>` for
optional online freshness. It SHALL NOT depend on older target-side policy or
imply that reinstalling is the only way to inspect the installation. If the
repository entry point is absent, non-executable, symlinked, or any command
value contains non-printable/control/surrogateescaped characters, status SHALL
emit an honest fallback rather than a dead, partial, or visually spoofable
command. Non-clean states SHALL retain their existing action without inspecting
the entry point. The guidance SHALL preserve that byte equality is not
installation provenance, legal-source freshness, or filing readiness.

#### Scenario: Human clean result

- **WHEN** a user requests status without `--json`
- **THEN** the output explains the observed structural state, canonical skill count, ordered executable offline and optional online commands for the exact target, and read-only unlocked boundary in plain Russian

#### Scenario: JSON clean result

- **WHEN** automation requests clean status with `--json`
- **THEN** the stable report shape and exit code remain unchanged while `message` says content and freshness were not checked and `recommended_action` names one existing repo-side installer, `--verify`, `--verify-current`, and the exact `--target` in that order

#### Scenario: Repo-side entry point is absent

- **WHEN** status is invoked from a detached tool copy without the canonical installer beside it
- **THEN** recommended action says the verification entry point is unavailable and directs the user to update the repository without emitting a nonexistent command

#### Scenario: Repo-side entry point is not executable

- **WHEN** the canonical installer exists but cannot be executed by the current process
- **THEN** status emits the same honest fallback and no dead shell command

#### Scenario: Target path contains surrogateescaped bytes

- **WHEN** a clean POSIX target contains filesystem bytes that cannot be represented as ordinary Unicode command arguments
- **THEN** recommended action says safe commands cannot be formed and emits no misleading command for a different path

#### Scenario: Target path contains display control characters

- **WHEN** a clean target spelling contains newline, carriage return, tab, escape, or another non-printable character
- **THEN** recommended action emits one fixed fallback without interpolating the path or a spoofable command line

#### Scenario: Status remains offline

- **WHEN** clean status renders the ordered verification recommendation
- **THEN** status itself invokes no network opener, validator, installer, subprocess, write, recovery, or lock operation

#### Scenario: JSON result

- **WHEN** automation requests status with `--json`
- **THEN** stdout contains one JSON object with schema version, status, severity, exit code, bounded stable reason code, target, target existence, managed-skill summary, optional transaction summary, message, recommended action, and an observation boundary declaring `explicit_mutations_performed=false`, `filesystem_access_time_updates_possible=true`, and `atomic_snapshot=false`

#### Scenario: Sensitive journal details

- **WHEN** a journal contains content identities and per-skill progress
- **THEN** status does not emit digests, journal bodies, old content, arbitrary unknown entry names, raw exceptions, or unrelated target entries

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

Status SHALL require only `--target`; normal installation SHALL continue to
require exactly one of `--repo` or `--source-skills-root` and preserve its
existing installation operations and exit behavior. Its successful and
publication-refusal public presentation SHALL follow the bounded-output
requirement in the installation-transaction capability.

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

### Requirement: Explicit current-release verification has stable outcomes

The public installer SHALL provide `--verify-current` as an explicitly online,
non-installing route that first applies the existing offline status preflight,
then validates the complete runtime target and compares its exact runtime
identity with the manifest at the immutable SHA resolved from canonical
`main`. It SHALL use the repository-side validator with runtime, strict,
update-check, and current-required modes. Every freshness HTTP attempt SHALL run
through the validator's fixed-route isolated helper under a parent-enforced
10-second monotonic execution deadline covering helper startup, DNS, TCP/TLS,
headers, and complete bounded response delivery. Response progress SHALL NOT
extend that deadline. The helper SHALL use isolated Python startup, a minimal
environment without inherited proxy or credential variables, no shell or stdin,
suppressed diagnostics, a route-specific output cap, process-group termination,
and bounded cleanup on timeout or protocol failure. Deadline expiry SHALL remain
the existing `network_error` and SHALL add no report, route, or timing field.
Ref resolution SHALL use REST first and SHALL attempt the validator's fixed,
non-interactive, bounded Git fallback exactly once after a REST ref
`network_error` when fixed-system Git is available; other REST ref evidence
failures and all immutable manifest failures SHALL NOT trigger that Git fallback.
Immutable manifest retrieval SHALL use the fixed raw URL first and SHALL attempt
`https://api.github.com/repos/aegorfk/ksrf-skillset/contents/skills-manifest.json?ref=<same-lowercase-40-hex-sha>`
exactly once only after a raw-route `network_error`, using
`Accept: application/vnd.github.raw+json`, `X-GitHub-Api-Version: 2026-03-10`,
`User-Agent: ksrf-runtime-validator/1`, no credential or compression header, and
the same already-resolved SHA; other raw evidence failures SHALL remain
fail-closed without that content fallback. After existing validation failures
take precedence, the process SHALL return `0` for `current`, `10` for
`different`, and `20` for `unknown`. Public human output SHALL be rendered from
the structured report in concise Russian, preserve counts, content identity,
remote version evidence, and bounded readable findings, and SHALL NOT expose
normal users to internal coverage labels or enum tokens such as `runtime`,
`evals`, `not_checked`, `validated`, `public-source`, `public-repository`, or
`source/release QA`. The machine report and direct maintainer renderer SHALL
remain unchanged. Human output SHALL preserve that equality is not installation
provenance, legal-source freshness, publication authority, or filing readiness.
Public wrapper errors SHALL use fixed actionable Russian wording and SHALL NOT
expose `repo-side`, `preflight`, `postflight`, trusted-policy implementation
terms, Python exception classes, raw transport diagnostics, or raw exception
text.

#### Scenario: Human current verification

- **WHEN** a user runs `install.sh --verify-current [--target PATH]`
- **THEN** the command performs no installation or recovery and prints a plain-Russian result for the exact target without maintainer coverage labels

#### Scenario: Matching published content

- **WHEN** runtime validation passes and freshness is `current`
- **THEN** human output says the installed content matches the current published version, shows its version SHA and local content digest, and does not claim provenance or legal freshness

#### Scenario: Known content difference

- **WHEN** runtime validation passes and any manifest identity field differs, including file count or byte count when the tree hash is equal
- **THEN** the report remains `freshness.status=different`, current-required mode returns `10` without calling the installer, and human output says the installed content differs without calling it corrupt or obsolete

#### Scenario: Trickling REST response remains bounded

- **WHEN** the REST ref helper receives continuous partial progress but exceeds its aggregate deadline
- **THEN** it is terminated as `network_error`, the public route can use only the existing one-shot Git fallback, and no partial response or helper diagnostic appears

#### Scenario: REST ref network failure uses fixed fallback

- **WHEN** explicit current verification receives bounded `network_error` from the REST ref lookup and the fixed Git fallback returns one valid exact-ref SHA
- **THEN** verification compares against the immutable manifest at that SHA with unchanged public output and exit meanings

#### Scenario: Trickling raw and Contents responses preserve fallback limits

- **WHEN** the raw helper exceeds its aggregate deadline and the same-SHA Contents helper either succeeds or also exceeds its own deadline
- **THEN** raw timeout invokes Contents exactly once, Contents timeout is terminal, no ref is repeated, and public current/different/unknown output plus exit meanings remain unchanged

#### Scenario: Raw manifest network failure uses official fallback

- **WHEN** explicit current verification has one valid remote SHA, the immutable raw-host request fails with bounded `network_error`, and the fixed Contents API raw-media request returns a valid manifest at that SHA
- **THEN** verification completes with unchanged current-or-different output and exit meanings

#### Scenario: Incomplete freshness evidence

- **WHEN** runtime validation passes but neither permitted ref-resolution route can establish a valid remote SHA, or the applicable permitted immutable-manifest route or routes cannot establish valid identity evidence
- **THEN** the report remains `freshness.status=unknown`, current-required mode returns `20`, and human output says comparison could not be completed without emitting a positive conclusion

#### Scenario: Existing validation failure takes precedence

- **WHEN** runtime validation fails or strict warnings exist
- **THEN** the existing validation code is returned before freshness-specific codes and human output says the installed content did not pass validation without a current/different success heading

#### Scenario: Public findings remain readable and bounded

- **WHEN** offline or current verification returns validator findings
- **THEN** the public installer prints at most 50 Russian severity, escaped bounded location, and escaped bounded message entries, replaces exception-derived diagnostics and internal runtime markers with fixed Russian explanations, omits internal finding codes, and states how many further findings were not printed while the structured report remains complete

#### Scenario: Exit-code automation

- **WHEN** automation runs `--verify-current` for a structurally clean target
- **THEN** the exit code distinguishes current, different, unknown, validation failure, and usage failure without parsing prose

#### Scenario: Explicit network and subprocess boundary

- **WHEN** neither `--verify-current` nor the internal `--check-updates` flag is selected
- **THEN** installation, offline verification, and status initiate neither freshness HTTP helper nor the Git subprocess fallback

#### Scenario: Unsafe or incomplete target

- **WHEN** the selected target is missing, structurally incomplete, a symlink, `/`, HOME, a file, or otherwise non-clean under the read-only status contract
- **THEN** current verification returns local prerequisite failure `1` before invoking the validator network lookup and gives a plain-Russian next action without raw exception details

#### Scenario: Trusted verification cannot complete

- **WHEN** the repository-side policy raises unexpectedly or returns malformed current-release evidence
- **THEN** the public wrapper returns `2`, prints no positive result, and asks the user in plain Russian to update the repository and retry without exposing implementation names, transport diagnostics, or exception text

#### Scenario: Target changes during the network window

- **WHEN** a candidate-current local tree changes after its first identity pass and before the post-network identity pass
- **THEN** the report fails with `RUNTIME_IDENTITY_CHANGED`, freshness is `unknown`, and no `current` success is emitted

#### Scenario: Target root is replaced during verification

- **WHEN** the lexical runtime root is replaced, rebound, or converted to a symlink after preflight
- **THEN** current-required validation fails with `RUNTIME_ROOT_CHANGED` and cannot return `0`

#### Scenario: Invalid option combinations

- **WHEN** `--verify-current` is combined with `--status` or `--json`, `--json` is used without `--status`, or validator `--require-current` lacks its required runtime update-check scope
- **THEN** the relevant CLI exits with usage code `2` before installation or freshness success is reported

### Requirement: Explicit offline runtime verification has stable outcomes

The public installer wrapper MUST expose `--verify [--target PATH]` as a
read-only, repo-side, strict runtime-content verification mode. It MUST perform
the existing structural status preflight before validation, MUST execute the
repository validator with the complete canonical runtime scope, and MUST NOT
request network freshness, install, recover, clean, acquire the writer lock, or
run source-only tests/evals. Success MUST mean only that the sampled local
runtime is complete, self-contained, and internally valid under the repo-side
validator; it MUST NOT claim provenance, current-release identity,
source/release QA, legal freshness, or filing readiness. Public human output
MUST call the successful outcome `ПРОВЕРКА БЕЗ СЕТИ ПРОЙДЕНА`, explain omitted
source-only tests in ordinary Russian, use the shared bounded readable findings
format, and use the same fixed Russian local/internal error guidance as
`--verify-current`; the machine and maintainer interfaces remain unchanged.

#### Scenario: Complete valid runtime

- **WHEN** `./install.sh --verify` observes a structurally clean target and the strict complete runtime validator passes
- **THEN** it exits `0`, prints the runtime identity and coverage boundary in plain Russian, and states that online freshness was not checked

#### Scenario: Offline boundary

- **WHEN** `--verify` runs
- **THEN** it passes neither `--check-updates` nor `--require-current`, performs no network request, and does not mutate the target or source checkout except for filesystem read-side effects such as `atime`

#### Scenario: One immutable policy snapshot

- **WHEN** installed bytes change temporarily while offline policy checks are running and are then restored
- **THEN** all content and offline-policy checks still read one private immutable snapshot, the snapshot identity is compared with a final held-root validation, and the temporary live-tree state cannot produce a false successful result

#### Scenario: Snapshot capture is bounded and no-follow

- **WHEN** a nested installed entry is replaced by a symlink, becomes a special or hard-linked file, crosses a device or mount boundary, exceeds the per-file limit, or makes the complete capture exceed its entry or byte budget
- **THEN** descriptor-relative snapshot capture stops with local failure `1` before following or copying that entry and cannot report verification success

#### Scenario: Unsafe or incomplete target

- **WHEN** the structural status preflight is non-clean
- **THEN** the wrapper exits `1` before invoking the content validator and reports in plain Russian that a safe complete installation is required

#### Scenario: Runtime validation fails

- **WHEN** the preflight is clean but strict runtime validation finds an error or warning
- **THEN** the wrapper exits `1`, cannot report offline verification success, and renders only bounded readable findings without internal finding codes

#### Scenario: Installed target data is unreadable

- **WHEN** a runtime policy file is malformed, not valid UTF-8 where text is required, or becomes unreadable
- **THEN** the wrapper reports a bounded validation finding and exits `1`, reserving code `2` for a coordinator or trusted-policy malfunction

#### Scenario: Unexpected validator failure

- **WHEN** the repo-side validator cannot be trusted or returns its unexpected-failure outcome
- **THEN** the wrapper exits `1` for a missing or unsafe local prerequisite and `2` for an unexpected validator outcome, without installing or repairing anything and without exposing implementation or exception details

#### Scenario: Verification modes are exclusive

- **WHEN** `--verify` is combined with `--status`, `--verify-current`, or `--json`
- **THEN** the wrapper exits with usage code `2` before any status, validation, network, or installation operation

#### Scenario: Existing read-only modes remain compatible

- **WHEN** callers use `--status [--json]` or `--verify-current` without `--verify`
- **THEN** their arguments, behavior, output boundaries, and exit-code contracts remain unchanged

#### Scenario: Normal installation changes only public presentation

- **WHEN** callers use normal installation without a verification mode
- **THEN** its arguments, installation operations, and exit-code contracts remain unchanged, while canonical-target success omits nested publication evidence and canonical-target publication refusal replaces both nested streams with the fixed Russian message specified by the installation-transaction capability
