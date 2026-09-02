## Context

`tools/install_skillset.py` already owns the canonical transaction grammar: a persistent target lock file, at most one `.ksrf-install-transaction-*` root, at most one `.ksrf-install-gc-*` root, schema-bound journals, per-skill progress, and terminal cleanup vectors. Today the only code path that interprets those artifacts is the mutating installer, which acquires locks and immediately attempts recovery. Users therefore cannot safely distinguish a healthy target from retained evidence before running another installation.

The status command must reuse the same validation grammar without reusing any recovery side effects. It is intended for a local user or automation and must remain useful when the source checkout is unavailable.

## Goals / Non-Goals

**Goals:**

- Inspect one target without issuing create, write, rename, delete, sync, recovery, cleanup, or filesystem-lock operations, while disclosing possible filesystem-managed `atime` updates caused by reads.
- Classify clean, not installed, incomplete, recovery-required, and unsafe states with stable JSON and exit codes.
- Validate a retained transaction or GC root deeply enough that a structurally valid recovery candidate is not confused with corrupt or foreign evidence.
- Give concise Russian guidance while preserving the exact evidence path for manual escalation.
- Detect target replacement or a changing observation and fail closed instead of reporting a false clean result.

**Non-Goals:**

- Recover, roll back, clean, install, update, or delete anything.
- Certify that an installer process is or is not currently running; the persistent lock file is not an activity marker and status deliberately acquires no lock.
- Verify release freshness, publication authority, source hashes, or legal/filing readiness; existing source/runtime validators remain separate.
- Promise a globally atomic snapshot to lock-free readers.
- Detect a brief ABA substitution that is fully restored between the opening and final identity samples; the command still detects any replacement that changes the held inode or classification fingerprint at either boundary.

## Decisions

### 1. Status is a source-independent CLI mode

`tools/install_skillset.py --status --target PATH [--json]` and `install.sh --status [--target PATH] [--json]` SHALL not require `--repo` or `--source-skills-root`. Normal installation keeps the existing source requirement. `--json` is status-only, and `--preserve-target-development` remains install-only.

This avoids loading or trusting a source tree merely to explain target-local evidence. A separate executable was considered, but rejected because it would duplicate private transaction constants and validation rules.

### 2. Stable classifications and process codes

The report uses schema `1.0` and one of five status values:

| Status | Exit | Meaning |
|---|---:|---|
| `clean` | 0 | Safe target, all canonical skill directories present, no installer-owned recovery roots |
| `not_installed` | 10 | Target is absent or contains none of the canonical skills |
| `incomplete` | 20 | Some canonical skills are missing without a transaction root |
| `recovery_required` | 20 | One structurally valid transaction or terminal GC root is retained, or the observation changed |
| `unsafe` | 30 | Path, lock, journal, container, identity, or root multiplicity is ambiguous or corrupt |

Non-zero operational codes are deliberately distinct from argparse usage code 2. Human output is Russian; JSON keys and enum values are stable ASCII API identifiers.

### 3. Read-only validation reuses pure validators

Inspection SHALL disable Python bytecode writes before importing local helpers, open the existing target with `O_RDONLY | O_NONBLOCK | O_DIRECTORY | O_NOFOLLOW`, hold that descriptor through the observation, and read relevant entries with descriptor-relative `stat/open` calls that never follow symlinks. Regular-file opens also use `O_NONBLOCK`, then verify the anchored object is still a regular single-link file before reading, so a FIFO substitution cannot hang the command. Journal, layout, progress-vector, and terminal-state validators receive an immutable observation snapshot rather than reopening paths. Validation of a pre-journal transaction requires current-user ownership and no group/world write permission on the root and optional single-link journal temporary file. Building, prepared/rolling-back, terminal transaction, and terminal GC phases each use their existing phase-specific invariants.

The existing transaction `semantic_digest` remains content/mode based so it can be compared with journal identities. The descriptor scanner indexes relative paths, sorts the complete index globally exactly like the canonical installer (including `.`), safely reopens each component, and streams original file bytes into the hash. A separate internal `observation_fingerprint` includes device, inode, type, mode, owner, group, link count, size, timestamps, and content digest for every fact that determines classification. Byte-identical inode replacement therefore changes the observation even when its semantic digest is unchanged.

No status path calls target creation, lock acquisition, journal write, recovery, cleanup, rename, unlink, or fsync. The existing `.ksrf-install.lock` is only inspected with `lstat`; it is never created or locked.

### 4. Status describes an unlocked observation honestly

The JSON report always includes `observation.consistency = "unlocked_read_only"`, `observation.explicit_mutations_performed = false`, `observation.filesystem_access_time_updates_possible = true`, and `observation.atomic_snapshot = false`. The command issues no mutation syscall, but directory enumeration and file reads may let the host filesystem update `atime`; this is disclosed instead of claiming byte-for-byte metadata immobility. The target identity, lock entry, 15 canonical top-level skill entries, transaction/GC root set, and every journal/container/live-skill entry read for evidence validation contribute to the sampled classification fingerprint. Target replacement is `unsafe`; any other changed classification determinant is `recovery_required` with an instruction to retry after any running installer finishes. If a deep observation is invalid, status repeats the complete evidence and live-skill observation: only two invalid observations with equal fingerprints are classified `unsafe`; a successful, incomparable, or different second observation is `recovery_required`.

Each complete evidence observation has fixed budgets of 20,000 entries, depth 64, 32 MiB per regular file, and 128 MiB total regular-file bytes. Journal and journal-temporary files have a stricter 1 MiB cap. The scanner indexes metadata and enforces these limits before opening payload bytes, then bounds each read to the anchored size so a growing file cannot extend the operation indefinitely. Two matching over-budget observations are a fail-closed `unsafe` result; if the rejected metadata or outcome changes between samples, the result is `recovery_required`. Neither outcome deletes evidence or starts partial recovery.

The command never labels a retained transaction as definitely active or abandoned. Guidance says to wait if an installation is still running, otherwise rerun the normal installer to invoke its validated recovery path.

### 5. The report exposes bounded facts, not journal payloads

JSON includes schema version, status, severity, exit code, a stable bounded `reason_code`, lexical target path, target existence, managed-skill counts and missing names, optional transaction kind/phase/evidence paths, message, recommended action, and observation boundary. Before either JSON or human rendering, unpaired filesystem surrogate code points in public paths are converted to printable ASCII escapes, preserving valid UTF-8 output even for raw-byte POSIX arguments. The report does not emit per-skill digests, old content, journal bodies, arbitrary unknown entry names, or unrelated target entries. Human output maps internal phase enums and failure reasons to Russian phrases rather than exposing implementation tokens or raw exceptions.

## Risks / Trade-offs

- **Concurrent mutation can invalidate a read-only observation** → sample target/root identity before and after, classify changes without claiming corruption, and state the unlocked boundary in every report.
- **Read syscalls can update `atime` on writable mounts** → issue no mutation syscall and disclose this host-filesystem side effect in both output modes instead of claiming persistent metadata immobility.
- **Hostile sparse or expanding files can consume unbounded I/O** → enforce entry/depth/per-file/aggregate budgets before payload reads and stop if a file grows beyond its anchored size.
- **Deep identity checks can be slower on large installed skills** → restrict traversal to the 15 managed destinations and installer-owned containers; correctness is preferred over a shallow false green.
- **Existing private validators could accidentally gain side effects later** → add tests that patch all mutating primitives and assert target snapshots remain byte/mode/mtime identical.
- **Exit codes above the conventional 0/1 range require documentation** → keep them stable in the spec, README, JSON, and tests.
- **A safe persistent lock file can exist when no installer runs** → never infer activity from presence alone and acquire no flock.

## Migration Plan

1. Add failing status API/CLI/read-only tests.
2. Extract the pure pre-journal validation helper and implement inspection/report rendering.
3. Wire direct CLI and `install.sh` status modes without changing normal installation behavior.
4. Run adversarial, full root, source/runtime/offline, clean-room, and OpenSpec validation.
5. Publish, install the exact remote `main`, and archive the change only after evidence is complete.

Rollback is removal of the status-only entry points and report helpers; the existing installer transaction format and installed payload remain unchanged.

## Open Questions

None. The command deliberately reports an unlocked observation instead of probing or acquiring installer locks.
