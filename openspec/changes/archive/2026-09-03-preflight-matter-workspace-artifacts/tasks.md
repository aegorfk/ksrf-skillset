## 1. Contract and Red Regression

- [x] 1.1 Record the pre-existing-path boundary and explicitly exclude
  concurrent post-preflight substitution from the guarantee.
- [x] 1.2 Add direct RED coverage for a symlink on every top-level artifact
  lane and for a symlinked workspace root.
- [x] 1.3 Add RED coverage for a late ledger conflict that currently leaves an
  earlier partial layout.
- [x] 1.4 Add a real CLI RED proving exit `2`, no success output, and exact
  workspace/external preservation.
- [x] 1.5 Add RED coverage proving a new matter cannot adopt data already stored
  in any reserved directory endpoint.
- [x] 1.6 Add RED coverage proving symlinked or non-regular `matter.json` is
  rejected without opening its target, including dangling-link visibility.
- [x] 1.7 Cover every ledger endpoint and non-regular kind, a nested route
  prefix, pre-existing-manifest scan order, and safe compatibility cases.

## 2. Minimal Runtime Fix

- [x] 2.1 Inspect all planned existing path components and containment before
  the first mutation or manifest read, using no-follow type checks and
  normalized inspection errors.
- [x] 2.2 Preflight every directory endpoint and ledger conflict together when
  no valid manifest owns the workspace; require reserved endpoints to be empty.
- [x] 2.3 Preserve valid initialization, idempotent reopen, schemas, outputs,
  and every legal/evidence/human/filing gate.

## 3. Verification and Review

- [x] 3.1 Prove the focused RED-to-GREEN transition and run matter/CLI contract
  regressions.
- [x] 3.2 Run full root and skill suites, strict source/runtime validation,
  offline containment, quick skill checks, manifest, and clean-install checks.
- [x] 3.3 Obtain independent implementation, filesystem-adversarial, and trust
  review; resolve every in-scope P1/P2.

## 4. Atomic Publication and Installation

- [x] 4.1 Archive the validated change and synchronize its base capability.
- [x] 4.2 Regenerate the manifest and create one atomic release commit.
- [x] 4.3 Push the feature ref and `main` to the identical commit and confirm
  the live SHA.
- [x] 4.4 Install the exact published runtime globally and verify its identity.
