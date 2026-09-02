## MODIFIED Requirements

### Requirement: Explicit current-release verification has stable outcomes

The public installer SHALL provide `--verify-current` as an explicitly online,
non-installing route that first applies the existing offline status preflight,
then validates the complete runtime target and compares its exact runtime
identity with the manifest at the immutable SHA resolved from canonical
`main`. It SHALL use the repository-side validator with runtime, strict,
update-check, and current-required modes. Every freshness HTTP attempt SHALL run
through the validator's fixed-route isolated helper under a parent-enforced
10-second monotonic execution deadline covering helper startup, DNS, TCP/TLS,
headers, and complete bounded response delivery. Response progress SHALL NOT
extend that deadline. The helper SHALL use isolated Python startup, a minimal
environment without inherited proxy or credential variables, no shell or stdin,
suppressed diagnostics, a route-specific output cap, process-group termination,
and bounded cleanup on timeout or protocol failure. Deadline expiry SHALL remain
the existing `network_error` and SHALL add no report, route, or timing field.
Ref resolution SHALL use REST first and SHALL attempt the validator's fixed,
non-interactive, bounded Git fallback exactly once after a REST ref
`network_error` when fixed-system Git is available; other REST ref evidence
failures and all immutable manifest failures SHALL NOT trigger that Git fallback.
Immutable manifest retrieval SHALL use the fixed raw URL first and SHALL attempt
`https://api.github.com/repos/aegorfk/ksrf-skillset/contents/skills-manifest.json?ref=<same-lowercase-40-hex-sha>`
exactly once only after a raw-route `network_error`, using
`Accept: application/vnd.github.raw+json`, `X-GitHub-Api-Version: 2026-03-10`,
`User-Agent: ksrf-runtime-validator/1`, no credential or compression header, and
the same already-resolved SHA; other raw evidence failures SHALL remain
fail-closed without that content fallback. After existing validation failures
take precedence, the process SHALL return `0` for `current`, `10` for
`different`, and `20` for `unknown`. Public human output SHALL be rendered from
the structured report in concise Russian, preserve counts, content identity,
remote version evidence, and bounded readable findings, and SHALL NOT expose
normal users to internal coverage labels or enum tokens such as `runtime`,
`evals`, `not_checked`, `validated`, `public-source`, `public-repository`, or
`source/release QA`. The machine report and direct maintainer renderer SHALL
remain unchanged. Human output SHALL preserve that equality is not installation
provenance, legal-source freshness, publication authority, or filing readiness.
Public wrapper errors SHALL use fixed actionable Russian wording and SHALL NOT
expose `repo-side`, `preflight`, `postflight`, trusted-policy implementation
terms, Python exception classes, raw transport diagnostics, or raw exception
text.

#### Scenario: Human current verification

- **WHEN** a user runs `install.sh --verify-current [--target PATH]`
- **THEN** the command performs no installation or recovery and prints a plain-Russian result for the exact target without maintainer coverage labels

#### Scenario: Matching published content

- **WHEN** runtime validation passes and freshness is `current`
- **THEN** human output says the installed content matches the current published version, shows its version SHA and local content digest, and does not claim provenance or legal freshness

#### Scenario: Known content difference

- **WHEN** runtime validation passes and any manifest identity field differs, including file count or byte count when the tree hash is equal
- **THEN** the report remains `freshness.status=different`, current-required mode returns `10` without calling the installer, and human output says the installed content differs without calling it corrupt or obsolete

#### Scenario: Trickling REST response remains bounded

- **WHEN** the REST ref helper receives continuous partial progress but exceeds its aggregate deadline
- **THEN** it is terminated as `network_error`, the public route can use only the existing one-shot Git fallback, and no partial response or helper diagnostic appears

#### Scenario: REST ref network failure uses fixed fallback

- **WHEN** explicit current verification receives bounded `network_error` from the REST ref lookup and the fixed Git fallback returns one valid exact-ref SHA
- **THEN** verification compares against the immutable manifest at that SHA with unchanged public output and exit meanings

#### Scenario: Trickling raw and Contents responses preserve fallback limits

- **WHEN** the raw helper exceeds its aggregate deadline and the same-SHA Contents helper either succeeds or also exceeds its own deadline
- **THEN** raw timeout invokes Contents exactly once, Contents timeout is terminal, no ref is repeated, and public current/different/unknown output plus exit meanings remain unchanged

#### Scenario: Raw manifest network failure uses official fallback

- **WHEN** explicit current verification has one valid remote SHA, the immutable raw-host request fails with bounded `network_error`, and the fixed Contents API raw-media request returns a valid manifest at that SHA
- **THEN** verification completes with unchanged current-or-different output and exit meanings

#### Scenario: Incomplete freshness evidence

- **WHEN** runtime validation passes but neither permitted ref-resolution route can establish a valid remote SHA, or the applicable permitted immutable-manifest route or routes cannot establish valid identity evidence
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

#### Scenario: Explicit network and subprocess boundary

- **WHEN** neither `--verify-current` nor the internal `--check-updates` flag is selected
- **THEN** installation, offline verification, and status initiate neither freshness HTTP helper nor the Git subprocess fallback

#### Scenario: Unsafe or incomplete target

- **WHEN** the selected target is missing, structurally incomplete, a symlink, `/`, HOME, a file, or otherwise non-clean under the read-only status contract
- **THEN** current verification returns local prerequisite failure `1` before invoking the validator network lookup and gives a plain-Russian next action without raw exception details

#### Scenario: Trusted verification cannot complete

- **WHEN** the repository-side policy raises unexpectedly or returns malformed current-release evidence
- **THEN** the public wrapper returns `2`, prints no positive result, and asks the user in plain Russian to update the repository and retry without exposing implementation names, transport diagnostics, or exception text

#### Scenario: Target changes during the network window

- **WHEN** a candidate-current local tree changes after its first identity pass and before the post-network identity pass
- **THEN** the report fails with `RUNTIME_IDENTITY_CHANGED`, freshness is `unknown`, and no `current` success is emitted

#### Scenario: Target root is replaced during verification

- **WHEN** the lexical runtime root is replaced, rebound, or converted to a symlink after preflight
- **THEN** current-required validation fails with `RUNTIME_ROOT_CHANGED` and cannot return `0`

#### Scenario: Invalid option combinations

- **WHEN** `--verify-current` is combined with `--status` or `--json`, `--json` is used without `--status`, or validator `--require-current` lacks its required runtime update-check scope
- **THEN** the relevant CLI exits with usage code `2` before installation or freshness success is reported
