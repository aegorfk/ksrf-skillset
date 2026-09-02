## MODIFIED Requirements

### Requirement: Validator distinguishes source and runtime assurance

The portable validator MUST provide explicit `source` and `runtime` profiles. The `source` profile MUST validate behavioral and trigger evals, security-scan all source-only assets, invoke the canonical public-source artifact contract, and remain the default. The `runtime` profile MAY skip only eval-specific checks, MUST reject any remaining source-only `tests/`, `evals/`, versioned maintainer specifications, or exact maintainer-file artifact, and MUST preserve all other package, content, link, metadata, security, and cross-contract checks. Every report MUST identify the profile, coverage, source-release eligibility, and a deterministic identity for the runtime-eligible bytes observed. A runtime report MUST NOT expose a `publish_manifest`, and runtime CLI invocation MUST reject standalone manifest output.

Runtime freshness lookup MUST be disabled by default. An explicit runtime-only update check MUST first resolve canonical GitHub `main` through the fixed GitHub REST ref endpoint. Every permitted freshness HTTP attempt MUST run as one fixed-route request in an isolated helper process under a parent-enforced 10-second monotonic execution deadline that begins before process spawn and covers interpreter startup, DNS, TCP/TLS, headers, and complete bounded body delivery; the socket inactivity timeout MUST remain only defense in depth and response progress MUST NOT extend the parent deadline. One immutable deadline MUST be rechecked after spawn, after every selector wake before reading, after EOF, and after process wait; an observation at or after the deadline MUST be rejected as `network_error` even if bytes are ready or the leader reports exit `0`. The parent MUST launch the absolute current Python interpreter and validator with isolated no-site/no-bytecode startup, no shell or stdin, suppressed stderr, filesystem-root working directory, a minimal environment with no inherited proxy, credential, Python-path, or CA-override variable, and a route-specific stdout cap. The helper MUST accept only the three fixed route identifiers and, for immutable manifest routes, one lowercase 40-hex SHA; it MUST NOT accept an arbitrary URL, host, header, method, output path, or mutable branch. On deadline, output-cap, selector, process, or protocol failure, the parent MUST kill the helper process group, perform bounded cleanup, and expose no raw diagnostic. Before returning any result, including after a completed leader, the runner MUST idempotently terminate its private process group, reap the direct child within a separate cleanup bound, close its selector and stdout handle, and leave no live member in that helper process group; it MUST NOT claim containment of a descendant that deliberately escapes the group.

Only when the REST ref request fails with bounded reason `network_error`, including aggregate deadline expiry, the validator MUST attempt exactly once to use a non-interactive, time- and output-bounded Git subprocess when an absolute Git executable is available through the fixed system search; an absent or unusable executable MUST yield `unknown/network_error`. The subprocess MUST use the fixed canonical HTTPS repository, exact `refs/heads/main`, isolated process environment and configuration, disabled repository discovery, and no shell. The ref fallback MUST accept exactly one byte-canonical lowercase 40-hex commit record for that exact ref; it MUST NOT run after an invalid, redirected, oversized, or otherwise hostile REST ref response or after any immutable-manifest failure. All freshness HTTP routes MUST disable ambient proxy discovery so proxy URLs or credentials from environment variables cannot alter the request path or add headers. After one SHA is resolved, the validator MUST request the manifest first from the fixed immutable raw URL. Only when that raw request fails with bounded `network_error`, including aggregate deadline expiry, it MUST attempt exactly once to request raw manifest media at `https://api.github.com/repos/aegorfk/ksrf-skillset/contents/skills-manifest.json?ref=<same-lowercase-40-hex-sha>` with `Accept: application/vnd.github.raw+json`, `X-GitHub-Api-Version: 2026-03-10`, `User-Agent: ksrf-runtime-validator/1`, and no authorization, cookie, compressed-content negotiation, or environment-derived header. The Contents request MUST use no mutable ref, returned download URL, metadata/base64 decoder, or alternate content route. For both immutable-manifest routes, transport/socket failures and HTTP `408`, `429`, or `5xx` MUST be `network_error`; any other HTTP error, redirect, missing/non-`200` response status, or changed URL coordinate MUST be `invalid_response`. The manifest fallback MUST NOT run after an invalid, redirected, oversized, or otherwise hostile raw response, and every Contents failure MUST be terminal. Both manifest routes MUST use the same strict byte cap and the same strict UTF-8, duplicate-key/non-finite JSON, schema, count, and identity validation. The validator MUST report `current`, `different`, or `unknown` without writing files. By default freshness MUST NOT change validation exit semantics. The additive current-required mode MUST be accepted only with a complete runtime update check and, after validation/strict failure precedence, MUST return `0` for `current`, `10` for `different`, and `20` for `unknown`. Candidate `current` MUST be confirmed by a second local runtime identity pass after the network lookup and by stable device/inode/type/resolved-path identity of the lexical runtime root; a changed tree or root MUST fail validation and MUST NOT retain `current`. Current-required mode MUST reject file report output before validation/network so its final target observation is not invalidated by its own write. JSON shape on stdout MUST remain unchanged, while current-required human output MUST name the overall outcome without a false-green heading. The validator MUST NOT call unequal content definitely outdated, MUST NOT turn unavailable coverage into a current result, and MUST NOT represent runtime or freshness validation as source-release, publication, legal, or filing authority.

#### Scenario: Default runtime validation is offline

- **WHEN** runtime validation is invoked without an update-check option
- **THEN** no network opener, HTTP helper, or Git subprocess is called, the report includes the local runtime identity, and freshness is `not_checked`

#### Scenario: Runtime identity is emitted

- **WHEN** all runtime-eligible files remain stable while validation hashes them
- **THEN** the report exposes the same aggregate tree SHA-256, file count, and byte count as the canonical release manifest algorithm, while `publish_manifest` remains null

#### Scenario: Runtime file changes between manifest and identity passes

- **WHEN** a runtime file becomes unreadable or its size or digest changes before aggregate identity is finalized
- **THEN** validation records a bounded error, emits no passing local identity, and any requested freshness result is `unknown`

#### Scenario: Installed content equals current main

- **WHEN** explicit runtime update checking resolves one valid canonical `main` commit, the pinned manifest tree hash equals the local runtime tree hash, and the post-network local pass confirms the same identity
- **THEN** freshness is `current`, reports the compared remote SHA and hashes, and explains byte equivalence without claiming installation provenance

#### Scenario: One HTTP attempt has a hard aggregate deadline

- **WHEN** a permitted freshness endpoint continuously delivers small fragments before every child socket timeout but does not complete before the parent deadline
- **THEN** progress does not reset the deadline, the entire helper process group is terminated, bounded cleanup occurs, and the attempt yields only `network_error` without partial evidence or diagnostics

#### Scenario: Spawn time is part of the HTTP deadline

- **WHEN** helper startup consumes the complete execution window before the parent can begin response polling
- **THEN** the first deadline sample predates process creation, no fresh deadline is granted after spawn, the private process group is cleaned up, and the attempt yields `network_error`

#### Scenario: Exact deadline boundary rejects late success

- **WHEN** a selector wake, final bytes, EOF, or exit `0` is observed exactly at or after the immutable deadline
- **THEN** the parent rejects the late evidence as `network_error`, discards partial output, and performs bounded process-group cleanup before returning

#### Scenario: Completed helper leader cannot leave a same-group descendant

- **WHEN** a helper leader closes its output and exits while another process in its private process group remains alive
- **THEN** the parent terminates the remaining group member and completes bounded cleanup before returning or classifying the helper protocol

#### Scenario: REST deadline uses only the fixed Git fallback

- **WHEN** the REST ref helper exceeds its aggregate deadline and the hardened Git command returns one valid exact-ref SHA
- **THEN** exactly one Git fallback runs, the timed-out HTTP helper cannot continue, and manifest retrieval proceeds only at the Git-resolved immutable SHA

#### Scenario: REST network failure uses the fixed Git fallback

- **WHEN** the REST ref lookup fails with bounded `network_error` and the hardened Git command returns exactly one lowercase 40-hex SHA for `refs/heads/main`
- **THEN** the validator fetches the manifest only at that immutable SHA and completes the existing current-or-different comparison

#### Scenario: Git fallback output is ambiguous or malformed

- **WHEN** the fallback is absent, times out, exits nonzero, is signaled, exceeds its output cap, or emits anything other than one byte-canonical record for the exact ref
- **THEN** freshness is `unknown` with bounded `network_error`, `invalid_response`, or `response_too_large` according to the failure class, no Git diagnostic is exposed, and no manifest request is made

#### Scenario: Hostile REST evidence cannot trigger ref fallback

- **WHEN** the REST ref response is redirected, oversized, malformed, schema-invalid, or otherwise classified as `invalid_response` or `response_too_large`
- **THEN** no Git subprocess is invoked and freshness remains `unknown` with the original bounded reason

#### Scenario: Raw deadline uses only same-SHA Contents fallback

- **WHEN** one valid SHA is resolved and the immutable raw helper exceeds its aggregate deadline
- **THEN** exactly one Contents helper is started for that same SHA, no ref route is repeated, and the timed-out raw helper cannot continue

#### Scenario: Raw manifest network failure uses exact-SHA Contents fallback

- **WHEN** a valid immutable SHA is resolved, the raw-host manifest request fails with bounded `network_error`, and the fixed Contents API raw-media request returns a valid manifest for that same SHA
- **THEN** the validator completes the existing current-or-different comparison without resolving the branch again

#### Scenario: Contents deadline is terminal

- **WHEN** the exact-SHA Contents helper exceeds its aggregate deadline
- **THEN** freshness is `unknown/network_error`, no third content route, Git subprocess, or repeated ref request is started, and no partial helper output is accepted

#### Scenario: Both availability fallbacks preserve one immutable coordinate

- **WHEN** the REST ref route has a `network_error`, the fixed Git fallback resolves one SHA, the raw-host route has a `network_error`, and the Contents route returns a valid manifest
- **THEN** exactly one Git invocation and one Contents request occur, both manifest requests use that Git-resolved SHA, and neither ref route is repeated

#### Scenario: Ambient proxy credentials cannot enter freshness requests

- **WHEN** the process environment contains HTTP or HTTPS proxy URLs, including proxy credentials
- **THEN** the parent helper environment omits them, every freshness HTTP route ignores ambient proxy settings, and no environment-derived proxy authorization header is sent

#### Scenario: Helper success preserves strict response gates

- **WHEN** an isolated helper exits successfully with response bytes
- **THEN** the parent accepts them only after the existing route cap, strict UTF-8, duplicate-key/non-finite JSON, schema, count, hash, and immutable-coordinate gates all pass

#### Scenario: Hostile raw manifest evidence cannot trigger content fallback

- **WHEN** the raw-host response is redirected, oversized, malformed, schema-invalid, or otherwise classified as `invalid_response` or `response_too_large`
- **THEN** the Contents API is not called and freshness remains `unknown` with the original bounded reason

#### Scenario: Contents manifest evidence remains strict and bounded

- **WHEN** the Contents API request fails, changes host/path/query, redirects, exceeds the cap, ignores raw media, or returns malformed or schema-invalid content
- **THEN** freshness is `unknown` with a bounded reason, no returned download URL is followed, and no further manifest or ref request is made

#### Scenario: Immutable manifest failure cannot trigger Git ref fallback

- **WHEN** the raw route fails with a non-fallback reason, or an eligible Contents fallback also fails, so that no valid manifest identity remains after the applicable route or routes
- **THEN** no new Git subprocess or repeated ref lookup is invoked and freshness remains `unknown`

#### Scenario: Installed content changes during online comparison

- **WHEN** the local runtime identity differs between the pre-network and post-network passes
- **THEN** validation records `RUNTIME_IDENTITY_CHANGED`, freshness is `unknown`, and current-required mode returns validation failure rather than `0`

#### Scenario: Runtime root is rebound during online comparison

- **WHEN** the lexical runtime root no longer resolves to the initially observed regular directory identity
- **THEN** validation records `RUNTIME_ROOT_CHANGED`, freshness is `unknown`, and current-required mode returns validation failure rather than `0`

#### Scenario: Installed content differs from current main

- **WHEN** both local and pinned remote identities are valid but unequal
- **THEN** freshness is `different` and explains that the local tree may be older, customized, or locally modified

#### Scenario: Freshness evidence is unavailable

- **WHEN** both permitted ref-resolution routes are unavailable, the applicable permitted immutable-manifest route or routes cannot establish identity, a permitted remote operation exceeds its bound, a permitted response fails strict validation, or local identity is unavailable
- **THEN** freshness is `unknown` with a bounded reason code and the report does not claim current content

#### Scenario: Branch moves after ref resolution

- **WHEN** canonical `main` advances after its SHA was resolved by either permitted ref route
- **THEN** both manifest routes remain pinned to the already resolved immutable SHA rather than refetching by branch name

#### Scenario: Source caller requests online freshness

- **WHEN** `--check-updates` is combined with the source profile
- **THEN** CLI rejects the combination as a usage error before network, HTTP helper, or Git subprocess access

#### Scenario: Partial runtime caller requests online freshness

- **WHEN** `--check-updates` is combined with a package selection smaller than the canonical 15-package runtime
- **THEN** CLI rejects the combination before network or subprocess access because the partial local tree is not comparable with the canonical remote manifest

#### Scenario: Current-required mode lacks complete update scope

- **WHEN** `--require-current` is used without `--check-updates`, the runtime profile, or the complete canonical package set
- **THEN** CLI returns usage code `2` before validation, network, HTTP helper, or Git subprocess access

#### Scenario: Current-required mode requests report file output

- **WHEN** `--require-current` is combined with `--report-out`
- **THEN** CLI returns usage code `2` before validation, network access, subprocess access, or any report-file write

#### Scenario: Current-required outcomes

- **WHEN** complete runtime validation passes and current-required freshness is respectively `current`, `different`, or `unknown`
- **THEN** the process returns respectively `0`, `10`, or `20`, while calls without current-required mode retain prior validation exit behavior

#### Scenario: Freshness result is rendered

- **WHEN** runtime validation emits human or JSON output
- **THEN** JSON keeps its bounded stable fields, current-required human output names the effective validation/freshness outcome, and runtime/source-release boundaries remain explicit
