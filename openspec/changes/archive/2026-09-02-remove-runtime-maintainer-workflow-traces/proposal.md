## Why

The installed runtime already excludes repository specs, tests, and evals, but three runtime-eligible files still mention `OpenSpec change` or numbered maintainer tasks. Those references do not help a skill user, imply a repository dependency that is unavailable after installation, and weaken the public/runtime boundary.

## What Changes

- Replace the three maintainer-workflow references with plain user-facing language while preserving every artifact, evaluation, leakage, observability, and human-approval gate they currently express.
- Add a fail-closed runtime validator check for repository change-workflow names and numbered internal task coordinates in runtime-eligible text.
- Keep repository specs, tests, evals, and other source-only evidence unchanged and excluded from installation.
- Add exact-payload and injected-file tests so the public error remains bounded and the internal wording cannot silently return.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-runtime-payload-boundary`: the runtime payload must omit maintainer change-management traces while retaining the substantive safety gates in user-readable language.

## Impact

- Three runtime files receive wording-only cleanup.
- The portable validator gains one stable finding code and one bounded marker classifier.
- Runtime bytes and the release manifest change; legal methodology and filing authority do not.
