# Change: Preflight matter workspace artifacts before initialization writes

## Why

`initialize_matter()` creates directories and ledgers before it validates the
complete artifact layout. A pre-existing nested symlink such as
`workspace/evidence -> outside` therefore receives five JSON ledgers outside the
selected matter folder. A late conflicting ledger similarly leaves earlier
ledgers and directories behind. The CLI eventually reports an error, but only
after unauthorized or partial writes have already happened.

## What Changes

- Inspect the workspace root, `matter.json`, and every existing component of
  every declared `ARTIFACT_PATHS` route before the first initialization write.
- Reject a symlink at the workspace root or on any planned route, a resolved
  route outside the workspace, a non-directory route ancestor, an incompatible
  or non-empty reserved directory endpoint, and any pre-existing ledger when no
  valid `matter.json` owns the workspace.
- Perform no explicit mutation whenever this preflight rejects initialization,
  including through the public CLI: path kinds, link targets, modes, directory
  entries, and regular-file bytes remain unchanged. Reads may update filesystem
  access-time metadata.
- Preserve valid new initialization and valid idempotent reopening of an
  existing matter, including all privacy, evidence, expert-review, signature,
  payment, and filing controls.
- Make no claim of a descriptor-held transaction against a privileged or
  concurrent path replacement after preflight; this change closes hazards that
  already exist when initialization begins.

## Impact

- Affected runtime: `ksrf/filing/matter.py` and the existing `ksrf matter init`
  error route.
- Affected source QA: new direct and CLI subprocess regressions plus the full
  root/skill/runtime/install suites.
- User-visible benefit: an unsafe or conflicting folder is rejected before the
  initializer creates anything, so the error no longer leaks ledgers outside
  the selected folder or leaves a misleading partial workspace.
