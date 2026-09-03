## Context

The matter manifest declares ten fixed artifact routes. Four are directories
and six are JSON ledgers. Initialization currently creates the directory routes,
then checks and writes each ledger in sequence, then writes `matter.json` and an
audit event. `load_matter()` later resolves declared routes for containment, but
that validation cannot undo writes already made by initialization.

## Goals / Non-Goals

- Goals:
  - detect every deterministic pre-existing hazard across the complete planned
    layout before `mkdir`, ledger creation, manifest creation, or audit writes;
  - reject symlink traversal even when the symlink target remains inside the
    lexical workspace;
  - preserve path kinds, link targets, modes, directory entries, and file bytes
    on preflight failure, while acknowledging that reads may update atime;
  - retain valid first initialization and structurally safe idempotent reopen
    behavior.
- Non-Goals:
  - introduce a new matter schema or artifact route;
  - delete, repair, adopt, or migrate an unsafe partial workspace;
  - claim resistance to concurrent path substitution after a path-based
    preflight; descriptor-relative transactional creation can be specified
    separately if that stronger threat model becomes required.

## Decisions

### Split structural inspection from new-layout conflict inspection

A read-only structural preflight runs before even reading `matter.json`. It uses
no-follow metadata inspection so dangling links remain visible, and rejects a
symlinked workspace, a symlink on any planned route component, containment
resolution failure, escape outside the resolved workspace, or an existing
non-directory route ancestor. The manifest itself must be a regular file before
it can be opened; FIFOs, devices, sockets, and directories fail without a read.
Inspection and resolution errors are normalized to `MatterWorkspaceError` so
the CLI retains its public exit route. This applies equally to a new or existing
workspace.

If a regular `matter.json` exists, the existing strict `load_matter()` contract
remains authoritative for idempotent reopening. If no manifest exists, a second
read-only pass checks all planned directory endpoints and all six ledger
endpoints together. For a new matter, a pre-existing reserved directory is
compatible only when it is a real empty directory; otherwise its records,
objects, release files, or audit events would be silently adopted by the new
manifest. Any incompatible or non-empty reserved directory or existing ledger
rejects the operation before the first mutation, rather than discovering
conflicts in write order.

### Validate the complete static route set

The preflight derives its routes from the same `ARTIFACT_PATHS` mapping that is
written into `matter.json`; it does not maintain a second list of relative
paths. Directory-versus-ledger classification reuses the fixed semantic key set
already used by `load_matter()`.

### Test observable filesystem state

Direct tests snapshot path kind, link target, mode, and regular-file bytes for
both the workspace and an external directory before and after rejection. Cases
cover each top-level write lane (`inputs`, `evidence`, `drafts`, `release`, and
`audit`), a symlinked workspace root, every non-empty reserved directory
endpoint, a non-regular manifest that must not be opened, a late ledger
conflict, and valid idempotent reopening. A real CLI subprocess additionally
proves exit code `2`, no success output, and no explicit filesystem mutation.

## Risks / Trade-offs

- A previously tolerated symlink that points back inside the workspace is now
  rejected. Portable matter integrity is easier to audit when every declared
  route is lexical, so this is intentional fail-closed behavior.
- This preflight narrows deterministic partial writes but does not make the
  multi-file initialization transaction atomic against concurrent local
  mutation. The contract and user messaging must not overstate that boundary.

## Migration Plan

No automatic migration is safe. Existing structurally safe matters reopen
unchanged. A matter that depends on a formerly tolerated internal symlink is
now rejected. Unsafe or partial folders are otherwise left without explicit
mutation so a person can inspect and relocate their contents before selecting a
clean destination.
