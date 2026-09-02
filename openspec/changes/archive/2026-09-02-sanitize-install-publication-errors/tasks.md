## 1. Failure Contract Tests

- [x] 1.1 Make the canonical shell refusal test require exact fixed Russian stderr, suppression of hostile nested stdout/stderr, exact status propagation, and no writer/success/export.
- [x] 1.2 Pin unchanged detailed stderr and exit semantics of the direct publication verifier.
- [x] 1.3 Confirm explicit non-canonical installation still bypasses publication verification.

## 2. Public Wrapper and Guidance

- [x] 2.1 Implement Bash 3.2-compatible conditional guard execution with both nested streams suppressed and exact status preserved.
- [x] 2.2 Add fixed bounded Russian refusal text without interpolated repository, path, SHA, Git output, or exception details.
- [x] 2.3 Update README with the public refusal boundary and direct maintainer diagnostic route.

## 3. Verification and Publication

- [x] 3.1 Run targeted tests, full root and skill suites, source/runtime validation, self-containment, Bash syntax, diff checks, and strict OpenSpec QA.
- [x] 3.2 Obtain independent reviews of shell exit semantics, public sanitization, and cross-spec consistency.
- [x] 3.3 Archive OpenSpec, synchronize base specs, bind the manifest to the current live `main` parent, and stage one complete release diff before any feature commit.
- [x] 3.4 Create and verify one single-parent release commit containing implementation, archived change, synchronized specs, tests, docs, and manifest; fast-forward and push `main` only to that exact commit, with no intermediate `main` publication.
