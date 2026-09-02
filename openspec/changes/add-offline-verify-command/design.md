## Context

The public wrapper already has three disjoint paths: normal installation,
read-only structural `--status`, and online `--verify-current`. The runtime
validator already supports the exact offline operation needed here through
`--profile runtime --strict`; the missing piece is a short trusted entry point.
The target may be stale or locally modified, so verification policy must come
from the repository checkout rather than from the installed target.

## Goals / Non-Goals

**Goals:**

- Expose complete offline runtime validation as `./install.sh --verify`.
- Reject incomplete or unsafe target structure before content validation.
- Preserve non-mutating, no-network execution and stable exit codes.
- Keep every existing install, status, JSON, and online-verification contract.

**Non-Goals:**

- Prove that installed bytes came from this repository.
- Compare against GitHub or prove legal/source freshness.
- Run source-only tests/evals, repair an installation, acquire the writer lock,
  or change the transaction implementation.
- Add a second JSON schema to the shell wrapper.

## Decisions

1. **Delegate to one repo-side coordinator.** The wrapper resolves its own
   checkout and invokes an internal verification mode in
   `tools/install_skillset.py`. That coordinator dynamically loads the fixed
   repo-side validator and never executes code from TARGET. Reusing the canonical
   validator avoids a second content algorithm and keeps the runtime identity
   contract exact.

2. **Bind one target identity across all phases.** Before status preflight the
   coordinator opens the root with no-follow directory flags and retains that
   descriptor through postflight. Status samples use the descriptor directly;
   policy and validator reads run from the descriptor-held working directory
   with a relative root, after which the original working directory is restored.
   Device, inode, file type, and strict lexical path are also sampled at phase
   boundaries. A replacement therefore cannot redirect reads or inherit success.
   Output is delayed until these checks finish.

3. **Sandwich autonomous policy with stable content identities.** The first
   complete runtime validation establishes a baseline; autonomous CORE/UID
   policy reads the same descriptor-held root; a final complete validation must
   produce the same content identity. The observation remains read-only and does
   not claim an atomic snapshot or detection of a complete replace-and-restore
   cycle wholly between observable samples.

4. **Keep offline and online modes separate.** `--verify` never passes
   `--check-updates` or `--require-current`. `--verify-current` keeps its
   existing network and 0/10/20 freshness semantics. Both modes reject
   `--status`, each other, and wrapper `--json` with usage code 2.

5. **Propagate validator outcomes.** A strict runtime validation failure is code
   1; invalid wrapper usage or an unexpected validator failure is code 2. A
   successful code 0 means only that the sampled local runtime is complete,
   self-contained, and internally valid.

## Risks / Trade-offs

- **Filesystem reads are not a universal lock** → root/content identity checks
  and descriptor-bound traversal stop success from transferring to a replacement,
  while documentation still makes no atomic-snapshot claim against arbitrary
  non-cooperating writers.
- **Users may read “passed” as “current”** → runtime output and public guidance
  explicitly say network freshness was not checked and point to
  `--verify-current`.
- **A stale checkout supplies stale policy** → the result is described as
  integrity under that repo-side validator, not proof of provenance or current
  release identity.
- **Wrapper JSON remains status-only** → automation can use exit codes or invoke
  the validator directly when its detailed JSON report is required.

## Migration Plan

Additive release: publish the coordinator, wrapper, tests, and documentation;
install the manifest-bound runtime normally. Rollback is removal of the new
option/coordinator guard and its guidance, with no target-data migration.

## Open Questions

None.
