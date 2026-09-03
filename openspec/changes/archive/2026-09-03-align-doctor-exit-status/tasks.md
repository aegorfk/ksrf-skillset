## 1. Contract and RED regressions

- [x] 1.1 Specify ready/degraded/blocked process codes, output channels, and
  non-goals.
- [x] 1.2 Reproduce the blocked-report code-0 false-green through both public
  launchers.
- [x] 1.3 Add deterministic source and clean-install tests for ready, degraded,
  blocked, and invalid-manifest controls.

## 2. Shared runtime implementation

- [x] 2.1 Derive the doctor exit code from only the top-level report state.
- [x] 2.2 Preserve report JSON/human output, error channels, probes, and every
  non-doctor command path.
- [x] 2.3 Document the exit-code meaning in repository and installed guidance.

## 3. Verification and review

- [x] 3.1 Prove the focused RED-to-GREEN transition for both launchers and
  clean installation.
- [x] 3.2 Run full root and skill suites, strict source/runtime, OpenSpec,
  offline containment, quick validation, manifest, and clean-install checks.
- [x] 3.3 Obtain implementation, adversarial, and trust-boundary review and
  resolve every in-scope P1/P2.

## 4. Atomic publication and installation

- [x] 4.1 Archive the validated change and synchronize its base capability.
- [x] 4.2 Regenerate the manifest and create one atomic release commit.
- [x] 4.3 Push feature and `main` refs to the same SHA and confirm remote state.
- [x] 4.4 Install that published runtime globally and verify exact identity.
