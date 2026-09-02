## 1. Contract

- [x] 1.1 Define ordered offline-first and optional-online clean status guidance.
- [x] 1.2 Preserve the status schema, exit codes, read-only boundary, and non-clean actions.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. Test-Driven Implementation

- [x] 2.1 Add failing human and JSON tests for two exact-target commands in order.
- [x] 2.2 Add failing safety tests proving one fixed fallback and no partial command.
- [x] 2.3 Render the shared entry point and exact target into offline and online commands.
- [x] 2.4 Keep status offline and preserve every existing status classification and schema key.

## 3. User Guidance and Release

- [x] 3.1 Update README status guidance with the two ordered verification steps.
- [x] 3.2 Regenerate the exact release manifest.
- [x] 3.3 Pass focused/full tests, strict validators, shell syntax, OpenSpec, and diff checks.
- [x] 3.4 Obtain independent review with no unresolved P1/P2.
- [x] 3.5 Commit/push, merge/publish exact `main`, install globally, and verify live human/JSON output.
- [ ] 3.6 Archive the OpenSpec change and publish the final manifest-bound commit.
