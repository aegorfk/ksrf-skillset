## MODIFIED Requirements

### Requirement: Explicit current-release verification has stable outcomes

The public installer SHALL provide `--verify-current` as an explicitly online,
non-installing route that first applies the existing offline status preflight,
then validates the complete runtime target and compares its exact runtime
identity with the manifest at the immutable SHA resolved from canonical
`main`. It SHALL use the repository-side validator with runtime, strict,
update-check, and current-required modes. After existing validation failures
take precedence, the process SHALL return `0` for `current`, `10` for
`different`, and `20` for `unknown`. Public human output SHALL be rendered from
the structured report in concise Russian, preserve counts, content identity,
remote version evidence, and bounded readable findings, and SHALL NOT expose normal
users to internal coverage labels or enum tokens such as `runtime`, `evals`,
`not_checked`, `validated`, `public-source`, `public-repository`, or
`source/release QA`. The machine report and direct maintainer renderer SHALL
remain unchanged. Human output SHALL preserve that equality is not installation
provenance, legal-source freshness, publication authority, or filing readiness.
Public wrapper errors SHALL use fixed actionable Russian wording and SHALL NOT
expose `repo-side`, `preflight`, `postflight`, trusted-policy implementation
terms, Python exception classes, or raw exception text.

#### Scenario: Human current verification

- **WHEN** a user runs `install.sh --verify-current [--target PATH]`
- **THEN** the command performs no installation or recovery and prints a plain-Russian result for the exact target without maintainer coverage labels

#### Scenario: Matching published content

- **WHEN** runtime validation passes and freshness is `current`
- **THEN** human output says the installed content matches the current published version, shows its version SHA and local content digest, and does not claim provenance or legal freshness

#### Scenario: Known content difference

- **WHEN** runtime validation passes and any manifest identity field differs, including file count or byte count when the tree hash is equal
- **THEN** the report remains `freshness.status=different`, current-required mode returns `10` without calling the installer, and human output says the installed content differs without calling it corrupt or obsolete

#### Scenario: Incomplete freshness evidence

- **WHEN** runtime validation passes but remote SHA or manifest evidence cannot be established
- **THEN** the report remains `freshness.status=unknown`, current-required mode returns `20`, and human output says comparison could not be completed without emitting a positive conclusion

#### Scenario: Existing validation failure takes precedence

- **WHEN** runtime validation fails or strict warnings exist
- **THEN** the existing validation code is returned before freshness-specific codes and human output says the installed content did not pass validation without a current/different success heading

#### Scenario: Public findings remain readable and bounded

- **WHEN** offline or current verification returns validator findings
- **THEN** the public installer prints at most 50 Russian severity, escaped bounded location, and escaped bounded message entries, replaces exception-derived diagnostics and internal runtime markers with fixed Russian explanations, omits internal finding codes, and states how many further findings were not printed while the structured report remains complete

#### Scenario: Exit-code automation

- **WHEN** automation runs `--verify-current` for a structurally clean target
- **THEN** the exit code distinguishes current, different, unknown, validation failure, and usage failure without parsing prose

#### Scenario: Explicit network boundary

- **WHEN** neither `--verify-current` nor the internal `--check-updates` flag is selected
- **THEN** installation and status do not initiate the freshness network lookup

#### Scenario: Unsafe or incomplete target

- **WHEN** the selected target is missing, structurally incomplete, a symlink, `/`, HOME, a file, or otherwise non-clean under the read-only status contract
- **THEN** current verification returns local prerequisite failure `1` before invoking the validator network lookup and gives a plain-Russian next action without raw exception details

#### Scenario: Trusted verification cannot complete

- **WHEN** the repository-side policy raises unexpectedly or returns malformed current-release evidence
- **THEN** the public wrapper returns `2`, prints no positive result, and asks the user in plain Russian to update the repository and retry without exposing implementation names or exception text

#### Scenario: Target changes during the network window

- **WHEN** a candidate-current local tree changes after its first identity pass and before the post-network identity pass
- **THEN** the report fails with `RUNTIME_IDENTITY_CHANGED`, freshness is `unknown`, and no `current` success is emitted

#### Scenario: Target root is replaced during verification

- **WHEN** the lexical runtime root is replaced, rebound, or converted to a symlink after preflight
- **THEN** current-required validation fails with `RUNTIME_ROOT_CHANGED` and cannot return `0`

#### Scenario: Invalid option combinations

- **WHEN** `--verify-current` is combined with `--status` or `--json`, `--json` is used without `--status`, or validator `--require-current` lacks its required runtime update-check scope
- **THEN** the relevant CLI exits with usage code `2` before installation or freshness success is reported

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

#### Scenario: Existing modes remain compatible

- **WHEN** callers use normal installation, `--status [--json]`, or `--verify-current` without `--verify`
- **THEN** their arguments, behavior, output boundaries, and exit-code contracts remain unchanged
