## ADDED Requirements

### Requirement: Explicit offline runtime verification has stable outcomes

The public installer wrapper MUST expose `--verify [--target PATH]` as a
read-only, repo-side, strict runtime-content verification mode. It MUST perform
the existing structural status preflight before validation, MUST execute the
repository validator with the complete canonical runtime scope, and MUST NOT
request network freshness, install, recover, clean, acquire the writer lock, or
run source-only tests/evals. Success MUST mean only that the sampled local
runtime is complete, self-contained, and internally valid under the repo-side
validator; it MUST NOT claim provenance, current-release identity, source/release
QA, legal freshness, or filing readiness.

#### Scenario: Complete valid runtime

- **WHEN** `./install.sh --verify` observes a structurally clean target and the strict complete runtime validator passes
- **THEN** it exits `0`, prints the runtime identity and coverage boundary, and states that online freshness was not checked

#### Scenario: Offline boundary

- **WHEN** `--verify` runs
- **THEN** it passes neither `--check-updates` nor `--require-current`, performs no network request, and does not mutate the target or source checkout except for filesystem read-side effects such as `atime`

#### Scenario: Unsafe or incomplete target

- **WHEN** the structural status preflight is non-clean
- **THEN** the wrapper exits `1` before invoking the content validator and reports that a safe complete installation is required

#### Scenario: Runtime validation fails

- **WHEN** the preflight is clean but strict runtime validation finds an error or warning
- **THEN** the wrapper exits `1` and cannot report offline verification success

#### Scenario: Installed target data is unreadable

- **WHEN** a runtime policy file is malformed, not valid UTF-8 where text is required, or becomes unreadable
- **THEN** the wrapper reports a bounded validation finding and exits `1`, reserving code `2` for a coordinator or trusted-policy malfunction

#### Scenario: Unexpected validator failure

- **WHEN** the repo-side validator cannot be trusted or returns its unexpected-failure outcome
- **THEN** the wrapper exits `1` for a missing or unsafe local prerequisite and `2` for an unexpected validator outcome, without installing or repairing anything

#### Scenario: Verification modes are exclusive

- **WHEN** `--verify` is combined with `--status`, `--verify-current`, or `--json`
- **THEN** the wrapper exits with usage code `2` before any status, validation, network, or installation operation

#### Scenario: Existing modes remain compatible

- **WHEN** callers use normal installation, `--status [--json]`, or `--verify-current` without `--verify`
- **THEN** their arguments, behavior, output boundaries, and exit-code contracts remain unchanged
