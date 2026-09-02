## 1. Contract

- [x] 1.1 Define plain-Russian public outcomes for current, different, unknown, and validation failure.
- [x] 1.2 Preserve validator data, direct maintainer output, network behavior, findings, and exit codes.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. Test-Driven Implementation

- [x] 2.1 Add failing renderer tests for all four public outcome classes.
- [x] 2.2 Forbid maintainer labels/codes in public output while retaining digest, counts, SHA, bounded escaped findings, and scope boundaries.
- [x] 2.3 Render `--verify-current` from structured data through a dedicated installer-owned function.
- [x] 2.4 Preserve current `0`, different `10`, unknown `20`, validation/local `1`, and unexpected-report/policy `2` outcomes with fixed public Russian errors.
- [x] 2.5 Bind validator and offline policy to one immutable snapshot, compare it with the final held-root identity, and sanitize all exception-derived public findings.

## 3. User Guidance and Release

- [x] 3.1 Update README verification guidance with the simplified result vocabulary.
- [x] 3.2 Regenerate the exact release manifest.
- [x] 3.3 Pass focused/full tests, strict validators, shell syntax, OpenSpec, and diff checks.
- [x] 3.4 Obtain independent review with no unresolved P1/P2.
- [ ] 3.5 Commit/push, merge/publish exact `main`, install globally, and verify live output.
- [ ] 3.6 Archive the OpenSpec change and publish the final manifest-bound commit.
