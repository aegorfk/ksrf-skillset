## Context

For retained installer evidence, `inspect_installation_status()` takes two comparable observations before reporting a stable recovery or unsafe state. Today each `_status_observe_evidence()` first performs `_status_raw_observation_fingerprint()` over the entire evidence and live payload, then performs `_status_observe_evidence_once()` over the same data for semantic validation. A valid transaction therefore incurs four complete payload traversals. The raw-first order exists so a semantic failure still has a comparable complete fingerprint; that safety property must remain.

Every status directory open also calls `_status_fd_is_mount()`, which reloads `/proc/self/mountinfo` through `_linux_mount_points()`. A transaction can contain thousands of directories, so mount discovery itself becomes repeated global work. Merely caching that path list for an entire scan would weaken same-device bind-mount race protection, so the optimization must use the opened descriptor's Linux mount identity when the kernel exposes it.

### Measured baseline

On the repository's synthetic interrupted-install fixture (15 skills, two small files per skill), one public status request currently produces:

| State | `os.read` calls | payload bytes returned | mount discovery calls | raw samples | semantic samples |
|---|---:|---:|---:|---:|---:|
| valid `prepared` | 488 | 29,872 | 786 | 2 | 2 |
| stable late-invalid live identity | 488 | 29,924 | 786 | 2 | 2 |
| stable early-invalid journal | 248 | 4,124 | 540 | 2 | 2 |

The exact byte totals depend on fixture paths and journal length; the stable structural baseline is two unconditional raw samples plus two semantic samples, with mount discovery proportional to directory count. Post-change gates therefore assert traversal/mount-call structure rather than those environment-specific byte constants.

## Goals

- Preserve two independent comparison samples and every existing classification, output, budget, path-anchor, no-follow, mount-boundary, and no-mutation guarantee.
- Reduce valid retained-evidence payload reads from four complete traversals to two: one per comparison sample.
- Avoid an extra full raw traversal for validation failures that occur only after a complete semantic sample is already available.
- Compare Linux `mnt_id` values from bounded `/proc/self/fdinfo/<fd>` reads and include the boundary method/target identity in the comparable fingerprint. If Linux mountinfo exists but fd mount IDs are unavailable, retain live per-directory fallback checks; if mountinfo does not exist, use `os.path.ismount()` without repeatedly rebuilding an always-empty Linux set.
- Keep early-invalid evidence bounded: a semantic prefix may be followed by one raw completion traversal, never an unbounded retry loop.

## Non-goals

- Do not make `clean` inspect skill contents or release freshness.
- Do not change schema `1.0`, status names, exit codes, messages, recovery authority, or installation behavior.
- Do not acquire the installer lock or turn the unlocked observation into an atomic snapshot.
- Do not remove the second comparison sample, scan budgets, or deep transaction grammar.

## Decisions

### 1. Semantic-first observation

Each comparison sample first executes semantic evidence validation. If it succeeds, its evidence and live-skill fingerprints are already complete and become the sample identity. If a state invariant fails after those complete fingerprints exist, the failure is wrapped with that same identity and no raw rescan occurs.

If parsing, layout validation, or a budget/type failure occurs before a complete identity exists, the sample performs exactly one bounded raw completion scan. The raw scan either yields a comparable identity or yields the existing bounded failure trace. Two matching invalid samples remain `unsafe`; a valid, different, or changing second sample remains `recovery_required` with `observation_changed`.

### 2. Descriptor-bound mount identity with fail-closed fallback

At the start of each comparison sample, status reads the target descriptor's numeric `mnt_id` from `/proc/self/fdinfo/<fd>` with a fixed byte cap and strict single-field parsing. Every child descriptor is checked against that target mount ID as well as the existing device and `os.path.ismount()` checks. This detects same-device bind mounts without reparsing the global mount table for every directory.

If the target descriptor's Linux fdinfo is unsupported, oversized, malformed, or unreadable, every child retains the current live `_linux_mount_points()` fallback rather than caching a race-prone path set. Once a sample has a target `mnt_id`, an unavailable child `mnt_id` is rejected fail-closed as a mount boundary; this avoids an unrecorded mid-sample switch in the boundary method. On macOS/BSD, where `/proc/self/mountinfo` is absent and the Linux set is necessarily empty, descriptor checks keep `os.path.ismount()` and skip repeated empty-set discovery. The boundary method and target mount ID (when available) are combined with valid and invalid sample fingerprints. The second sample captures its own independent boundary identity; a changed identity becomes `observation_changed`. Outside a sample context, `_status_fd_is_mount()` retains its current standalone behavior.

### 3. Instrumented performance contract

Tests build a valid interrupted transaction with nontrivial payload files, patch `os.read` and mount discovery, and assert both semantic parity and strict upper bounds. The primary contract is structural rather than wall-clock based: two complete payload reads, exactly two target mount-boundary acquisitions, and zero global mount-table loads when target descriptor mount IDs are available or Linux mountinfo is absent. The intentionally live per-directory Linux fallback remains outside that zero-load bound only when the target descriptor's mount ID is unavailable. Wall-clock measurements may be recorded for diagnostics but are not pass/fail gates.

### 4. Safety review

Regression coverage must retain stable oversized/malformed `unsafe`, changing invalid `recovery_required`, target replacement, FIFO/nonblocking opens, bounded bytes, FD closure, and zero explicit mutation. An independent review must confirm that no optimization reuses a semantic result across the two required samples.

## Risks and Mitigations

- **A late semantic failure loses its full fingerprint** → construct the combined fingerprint before state-invariant checks and carry it in `_InvalidEvidence`.
- **An early parser failure skips changing live skills** → run one raw completion scan before producing an invalid sample identity.
- **A cached mount set hides a same-device bind-mount race** → prefer descriptor-bound Linux `mnt_id`; when Linux needs a fallback, keep the live per-directory mount-table check rather than caching it.
- **Instrumentation overfits implementation details** → assert complete-payload byte counts and mount discovery bounds while separately testing unchanged public classifications.
