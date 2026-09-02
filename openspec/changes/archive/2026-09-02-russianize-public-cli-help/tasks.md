## 1. Contract and Red Tests

- [x] 1.1 Inventory the documented public help routes and preserve their command/option tokens.
- [x] 1.2 Add a failing clean-runtime subprocess test for Russian scaffolding, actionable descriptions, and empty stderr.
- [x] 1.3 Add a failing check that the test-only fixture switch is absent from help but remains registered.

## 2. Runtime Help

- [x] 2.1 Add bounded Russian `argparse` formatting to both entry points.
- [x] 2.2 Translate doctrine root/subcommand/argument descriptions and authority-ledger descriptions.
- [x] 2.3 Suppress only the doctrine fixture switch from public help; preserve all executable behavior and machine contracts.

## 3. Verification and Review

- [x] 3.1 Prove red-to-green transition for every documented help route.
- [x] 3.2 Run focused, root, skill, strict source/runtime, clean-room, shell, offline, and quick skill checks; rerun the two expected stale-manifest assertions after regeneration in 4.2.
- [x] 3.3 Run strict OpenSpec validation and independent UX/contract review; resolve all P1/P2 findings.

## 4. Atomic Publication and Installation

- [x] 4.1 Archive the validated change and synchronize the new base spec.
- [x] 4.2 Regenerate the manifest against exact current `main` and create one atomic release commit.
- [x] 4.3 Push the feature ref and fast-forward `main` to the identical SHA; confirm publication state.
- [x] 4.4 Install the exact published runtime globally and verify offline/current behavior.
