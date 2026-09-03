## 1. Contract and Red Regression

- [x] 1.1 Record the presence-versus-precedence failure and its narrow trust
  boundary without claiming general `PYTHONPATH` sandboxing.
- [x] 1.2 Add a real subprocess regression for the same-name launchers when the
  bundled `lib/` already appears in `PYTHONPATH`.
- [x] 1.3 Add a poison-package regression for every sibling-lib launcher with
  the poison entry before the already-present bundled library.
- [x] 1.4 Prove the new regression fails for the intended import-ownership
  reason on the release base.

## 2. Minimal Runtime Fix

- [x] 2.1 Put each resolved launcher-owned `lib/` at index zero exactly once
  before the owned package import.
- [x] 2.2 Preserve the relative order and values of every non-owned `sys.path`
  entry.
- [x] 2.3 Preserve public command paths, help, output channels, exit codes, and
  every legal/evidence/human/filing gate.

## 3. Verification and Review

- [x] 3.1 Run focused launcher regressions and the existing CLI contracts.
- [x] 3.2 Run full root and skill suites, strict source/runtime validation,
  offline containment, quick skill checks, manifest, and clean-install checks.
- [x] 3.3 Obtain independent implementation, test, and trust-boundary review;
  resolve every in-scope P1/P2.

## 4. Atomic Publication and Installation

- [x] 4.1 Archive the validated change and synchronize its base capability.
- [x] 4.2 Regenerate the manifest and create one atomic release commit.
- [x] 4.3 Push the feature ref and `main` to the identical commit and confirm
  the live SHA.
- [x] 4.4 Install the exact published runtime globally and verify its identity.
