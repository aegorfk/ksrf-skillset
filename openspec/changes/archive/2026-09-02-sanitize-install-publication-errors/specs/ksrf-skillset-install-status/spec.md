## MODIFIED Requirements

### Requirement: Status mode is source-independent and install-compatible

Status SHALL require only `--target`; normal installation SHALL continue to
require exactly one of `--repo` or `--source-skills-root` and preserve its
existing installation operations and exit behavior. Its successful and
publication-refusal public presentation SHALL follow the bounded-output
requirement in the installation-transaction capability.

#### Scenario: Direct status invocation

- **WHEN** `tools/install_skillset.py --status --target PATH --json` is invoked without a source option
- **THEN** status runs and returns its classified process code

#### Scenario: Public shell entry point

- **WHEN** `install.sh --status [--target PATH] [--json]` is invoked
- **THEN** it runs status without publication verification, installation, or export output

#### Scenario: Invalid option combination

- **WHEN** `--json` is used without `--status`, or status is combined with source or development-preservation options
- **THEN** the CLI rejects the request as usage error before reading or changing the target

#### Scenario: Shell target value is another option

- **WHEN** `install.sh --target` is followed by `--status`, `--json`, or another option token instead of a path
- **THEN** the shell exits with usage code 2 before publication verification, target creation, or installation

### Requirement: Explicit offline runtime verification has stable outcomes

The public installer wrapper MUST expose `--verify [--target PATH]` as a
read-only, repo-side, strict runtime-content verification mode. It MUST perform
the existing structural status preflight before validation, MUST execute the
repository validator with the complete canonical runtime scope, and MUST NOT
request network freshness, install, recover, clean, acquire the writer lock, or
run source-only tests/evals. Success MUST mean only that the sampled local
runtime is complete, self-contained, and internally valid under the repo-side
validator; it MUST NOT claim provenance, current-release identity,
source/release QA, legal freshness, or filing readiness. Public human output
MUST call the successful outcome `ПРОВЕРКА БЕЗ СЕТИ ПРОЙДЕНА`, explain omitted
source-only tests in ordinary Russian, use the shared bounded readable findings
format, and use the same fixed Russian local/internal error guidance as
`--verify-current`; the machine and maintainer interfaces remain unchanged.

#### Scenario: Complete valid runtime

- **WHEN** `./install.sh --verify` observes a structurally clean target and the strict complete runtime validator passes
- **THEN** it exits `0`, prints the runtime identity and coverage boundary in plain Russian, and states that online freshness was not checked

#### Scenario: Offline boundary

- **WHEN** `--verify` runs
- **THEN** it passes neither `--check-updates` nor `--require-current`, performs no network request, and does not mutate the target or source checkout except for filesystem read-side effects such as `atime`

#### Scenario: One immutable policy snapshot

- **WHEN** installed bytes change temporarily while offline policy checks are running and are then restored
- **THEN** all content and offline-policy checks still read one private immutable snapshot, the snapshot identity is compared with a final held-root validation, and the temporary live-tree state cannot produce a false successful result

#### Scenario: Snapshot capture is bounded and no-follow

- **WHEN** a nested installed entry is replaced by a symlink, becomes a special or hard-linked file, crosses a device or mount boundary, exceeds the per-file limit, or makes the complete capture exceed its entry or byte budget
- **THEN** descriptor-relative snapshot capture stops with local failure `1` before following or copying that entry and cannot report verification success

#### Scenario: Unsafe or incomplete target

- **WHEN** the structural status preflight is non-clean
- **THEN** the wrapper exits `1` before invoking the content validator and reports in plain Russian that a safe complete installation is required

#### Scenario: Runtime validation fails

- **WHEN** the preflight is clean but strict runtime validation finds an error or warning
- **THEN** the wrapper exits `1`, cannot report offline verification success, and renders only bounded readable findings without internal finding codes

#### Scenario: Installed target data is unreadable

- **WHEN** a runtime policy file is malformed, not valid UTF-8 where text is required, or becomes unreadable
- **THEN** the wrapper reports a bounded validation finding and exits `1`, reserving code `2` for a coordinator or trusted-policy malfunction

#### Scenario: Unexpected validator failure

- **WHEN** the repo-side validator cannot be trusted or returns its unexpected-failure outcome
- **THEN** the wrapper exits `1` for a missing or unsafe local prerequisite and `2` for an unexpected validator outcome, without installing or repairing anything and without exposing implementation or exception details

#### Scenario: Verification modes are exclusive

- **WHEN** `--verify` is combined with `--status`, `--verify-current`, or `--json`
- **THEN** the wrapper exits with usage code `2` before any status, validation, network, or installation operation

#### Scenario: Existing read-only modes remain compatible

- **WHEN** callers use `--status [--json]` or `--verify-current` without `--verify`
- **THEN** their arguments, behavior, output boundaries, and exit-code contracts remain unchanged

#### Scenario: Normal installation changes only public presentation

- **WHEN** callers use normal installation without a verification mode
- **THEN** its arguments, installation operations, and exit-code contracts remain unchanged, while canonical-target success omits nested publication evidence and canonical-target publication refusal replaces both nested streams with the fixed Russian message specified by the installation-transaction capability
