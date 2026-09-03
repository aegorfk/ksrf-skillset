## 1. Contract and RED regressions

- [x] 1.1 Specify total validation, addressed type errors, deterministic order,
  and unchanged CLI channels.
- [x] 1.2 Reproduce every current exception family with JSON-derived payloads.
- [x] 1.3 Add source and clean-installed CLI regressions with unchanged-file
  assertions and an exact valid-artifact control.

## 2. Minimal runtime implementation

- [x] 2.1 Validate reference-array containers and entries before set logic.
- [x] 2.2 Guard enum and principal membership against non-string JSON values.
- [x] 2.3 Preserve independent checks, valid output, and read/syntax failures.
- [x] 2.4 Document the installed validator failure contract for users.

## 3. Verification and review

- [x] 3.1 Prove the focused RED-to-GREEN transition for source and install.
- [x] 3.2 Run full root and skill suites, strict source/runtime, OpenSpec,
  offline containment, quick validation, manifest, and clean-install checks.
- [x] 3.3 Obtain implementation, adversarial, and trust-boundary review and
  resolve every in-scope P1/P2.

## 4. Atomic publication and installation

- [x] 4.1 Archive the validated change and synchronize its base specification.
- [x] 4.2 Regenerate the manifest and create one atomic release commit.
- [x] 4.3 Push feature and `main` refs to the same SHA and confirm remote state.
- [x] 4.4 Install that published runtime globally and verify exact identity.
