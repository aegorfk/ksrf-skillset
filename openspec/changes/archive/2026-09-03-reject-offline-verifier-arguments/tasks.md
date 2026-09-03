## 1. Contract and Red Regression

- [x] 1.1 Record the closed argument grammar and the distinction between the
  self-relative fallback and trusted repository-side target verification.
- [x] 1.2 Add direct RED coverage proving help and invalid arguments cannot call
  the validation scan.
- [x] 1.3 Add subprocess RED coverage for Russian help, typo, positional,
  combined-help, and invented-target arguments with exact output channels and
  exit classes, plus installed-tree preservation without an environment guard.
- [x] 1.4 Bind the existing no-argument success behavior before implementation.

## 2. Minimal Runtime Fix

- [x] 2.1 Parse an empty sequence or one exact help flag before all validation
  and directory enumeration, with option abbreviation disabled.
- [x] 2.2 Suppress sibling-policy bytecode generation during direct import and
  restore the interpreter setting afterward.
- [x] 2.3 Emit Russian help on stdout with code `0` and argument errors on
  stderr with code `2`, never alongside a verification result.
- [x] 2.4 Preserve validation functions, no-argument output, offline policy,
  runtime target semantics, and readiness boundaries.

## 3. Verification and Review

- [x] 3.1 Prove the focused RED-to-GREEN transition and run existing verifier,
  installer, runtime-command, and help contracts.
- [x] 3.2 Run full root and skill suites, strict source/runtime validation,
  offline containment, quick skill checks, manifest, and clean-install checks.
- [x] 3.3 Obtain independent implementation, parser-adversarial, and trust
  review; resolve every in-scope P1/P2.

## 4. Atomic Publication and Installation

- [x] 4.1 Archive the validated change and synchronize its base capability.
- [x] 4.2 Regenerate the manifest and create one atomic release commit.
- [x] 4.3 Push the feature ref and `main` to the identical commit and confirm
  the live SHA.
- [x] 4.4 Install the exact published runtime globally and verify its identity.
