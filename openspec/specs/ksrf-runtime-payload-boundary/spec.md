# ksrf-runtime-payload-boundary Specification

## Purpose
TBD - created by archiving change exclude-development-tests-from-installed-payload. Update Purpose after archive.
## Requirements
### Requirement: Installed payload excludes maintainer-only tests

The canonical KSRF install contract MUST exclude files under any skill-relative `tests` or `evals` path component and MUST exclude only the versioned exact maintainer-file identities. It MUST classify both `ksrf-argument-patterns/references/complaint-methodology-sources.md` and `ksrf-argument-patterns/references/automation-backlog.md` as tracked source-only maintainer documents and MUST exclude those exact identities from user installation without excluding similarly named Markdown files. The three retired runtime identities `ksrf-argument-patterns/scripts/enrich_ksrf_argument_patterns.py`, `ksrf-argument-patterns/scripts/extract_ksrf_argument_patterns.py`, and `ksrf-argument-patterns/scripts/build_constitutionalist_authority_corpus.py` MUST NOT exist as tracked skill duplicates; their canonical root-only copies MUST remain under `tools/` and covered by the release manifest.

#### Scenario: Source-only maintainer document is installed

- **WHEN** manifest generation or installation encounters either exact source-only Markdown identity
- **THEN** it is omitted, while source validation still scans it and lookalike Markdown remains eligible

#### Scenario: Runtime contains the automation backlog

- **WHEN** runtime-profile validation encounters the exact backlog identity
- **THEN** validation fails with `SOURCE_ONLY_ARTIFACT_PRESENT`

#### Scenario: Source repository contains the automation backlog

- **WHEN** source/release validation inspects the canonical tracked backlog
- **THEN** it remains required and covered by secret, local-path, symlink and public-artifact checks but is absent from the portable publish manifest

#### Scenario: Retired nested generator is encountered

- **WHEN** manifest generation, installation, or runtime validation encounters any of the three retired exact skill paths
- **THEN** the path is excluded from runtime, runtime validation reports `SOURCE_ONLY_ARTIFACT_PRESENT`, and similarly named files outside the exact identity remain eligible

#### Scenario: Source repository is prepared

- **WHEN** source/release validation inspects the repository
- **THEN** all three nested duplicates are absent, all three root-only tools are regular tracked files, and all three remain included in release-file hashes

#### Scenario: Benign nested duplicate is reintroduced

- **WHEN** any retired exact skill path exists again even with otherwise safe content
- **THEN** canonical repository/manifest validation and portable source validation fail closed instead of silently excluding the duplicate

### Requirement: One exact file contract governs distribution

Manifest generation, runtime installation, tree-hash verification, source-only maintainer ownership, release-tool ownership, and reverse synchronization MUST use the same versioned contract. Both source-only Markdown files MUST remain byte-preserved by reverse sync and MUST NOT be required in installed runtime. Installed user-facing `SKILL.md`, Markdown/JSON references, and operational builders/verifiers MUST NOT route users to either exact source-only Markdown basename or to the retired nested command `scripts/build_constitutionalist_authority_corpus.py`; the portable validator MAY retain exact identities solely as fail-closed policy data.

#### Scenario: Global runtime is synchronized back to source

- **WHEN** global KSRF skills contain a stale former builder mirror but the source target has already retired that nested path
- **THEN** reverse sync filters the stale mirror out of the copied payload, preserves every source-owned file byte-for-byte, leaves all three canonical root-owner contents unchanged, and keeps them executable

#### Scenario: Clean-room runtime is inspected

- **WHEN** the exact manifest payload is installed to an empty directory
- **THEN** neither source-only Markdown file nor any retired nested generator or user-facing backlink to an excluded basename exists, and all replacement routes resolve inside runtime

#### Scenario: Same or similar basename is encountered outside the exact identity

- **WHEN** another package contains `scripts/build_constitutionalist_authority_corpus.py` or the canonical package contains a different builder path
- **THEN** it remains runtime-eligible if it passes all other checks because exclusion is bound to the full exact skill-relative identity

### Requirement: Cleanup does not weaken development or legal gates

Runtime cleanup MUST preserve source/public security checks, source tests and evals, strict OpenSpec validation, explicit publication authority, all legal/human review gates, and an independently reviewed ownership map for every removed source-only method or proposed checker. Automated validation MUST cover exact payload behavior, route existence and dead runtime backlinks; it MUST NOT represent a planned automation as shipped functionality or an ownership table as substantive legal validation.

#### Scenario: Source-only backlog contains unsafe source material

- **WHEN** the tracked backlog contains a secret, absolute local path, symlink, or complaint-like artifact
- **THEN** source/repository validation rejects it even though runtime distribution excludes it

#### Scenario: Replacement route is absent

- **WHEN** a runtime backlink is removed but its referenced operational owner does not exist in the installed payload
- **THEN** regression validation blocks publication

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

### Requirement: Prebuilt constitutionalist corpus survives builder retirement

The root-only corpus builder and installed `constitutionalist-authority-corpus.json` and `constitutionalist-authority-corpus.md` MUST preserve the complete searchable authority/work registry, its runtime membership and owner route, every source-status and non-promotion boundary, and work-level provenance. The installed corpus MUST NOT expose repository-local source coordinates, a maintainer extraction queue, or unverified planning text as if it were an author holding. Runtime documentation MUST direct users to the prebuilt corpus and maintained method-card collections and MUST NOT claim that unavailable source inputs or corpus regeneration are installed.

#### Scenario: User opens the authority corpus

- **WHEN** the user needs constitutionalist methods for one matter
- **THEN** the corpus exposes the full registry, source-status warnings, research routes and clickable maintained-card references without a maintainer queue or unusable local path

#### Scenario: Maintainer rebuilds the corpus

- **WHEN** all four external input families are available in the source-maintenance environment
- **THEN** the single root release-covered builder emits schema 2.0 without `local_source_hint` or `next_extraction_wave`, while authority/work data and provenance roles remain intact

#### Scenario: Cleaned candidate is installed

- **WHEN** the candidate is copied into a clean runtime or exactly replaces an older global runtime
- **THEN** JSON and Markdown contain all 1,652 authority rows and 4,178 work links, omit the retired maintainer surfaces, retain the reviewed-card routes, and runtime strict validation passes

#### Scenario: Historical extraction targets are removed

- **WHEN** the 31-item maintainer queue is deleted
- **THEN** every queued authority ID still resolves to a normal authority row, all 276 linked works remain in the registry, and no removed focus string is represented as a verified author proposition

#### Scenario: Corpus provenance is inspected

- **WHEN** a user or validator inspects source and work records
- **THEN** source kind, label, coverage, public URL where available, work bibliography and work-level source identity remain, while no `ТЗ/...` coordinate is presented as a usable source

#### Scenario: Corpus boundary is missing or corrupted

- **WHEN** either validation profile encounters a missing corpus, malformed structure, a schema other than 2.0, a retired key at any nesting level, a `ТЗ/` coordinate, inverted canonical warnings or legends, non-canonical source kinds or semantic SHA, a status/review/summary value inconsistent with curated evidence, duplicate identities or routes, missing or undeclared work provenance, or a non-public URL in the exact corpus JSON
- **THEN** validation fails closed with a corpus-contract finding before the payload can be treated as release-ready or runtime-clean

### Requirement: Installed references are location-independent

Every runtime-eligible textual artifact in the canonical KSRF payload MUST be usable without the maintainer repository or its private source tree. Installed Markdown, JSON, YAML, text and executable guidance MUST NOT contain a repository-local `ТЗ/...` coordinate, a `<project-root>` placeholder, or a macOS, Linux or Windows user-home absolute path. Source-only artifacts MAY retain maintenance provenance only when the shared versioned file contract excludes them from installation and source/repository security validation still covers them. Policy-owner scripts MUST be scanned under the same rule and MUST construct enforcement markers without embedding an exempt literal.

#### Scenario: Clean-room runtime is inspected

- **WHEN** the exact manifest payload is installed into an empty directory
- **THEN** every runtime-eligible artifact is free of repository-local coordinates, all 15 packages validate in runtime profile, and bundled links still resolve

#### Scenario: User opens derived methodology

- **WHEN** a reference was derived from a source artifact that is not shipped
- **THEN** it preserves usable bibliography, DOI, hash, public URL or source-count provenance where available, states the availability boundary, and does not instruct the user to open a nonexistent local path

#### Scenario: Local coordinate returns in Markdown or code

- **WHEN** either validation profile encounters a runtime-eligible artifact containing `ТЗ/...`, `<project-root>` or a user-home absolute path
- **THEN** validation fails with a runtime-self-containment finding before the payload is treated as release-ready or runtime-clean

#### Scenario: Local coordinate is JSON-escaped

- **WHEN** a runtime JSON string encodes the same coordinate with Unicode or slash escapes
- **THEN** the portable validator decodes and normalizes it and fails with the same runtime-self-containment finding

#### Scenario: Source-only maintainer evidence contains a coordinate

- **WHEN** source validation encounters a coordinate inside an exact source-only artifact
- **THEN** the runtime-self-containment gate does not overmatch it, the artifact remains absent from the publish manifest, and existing source/repository safety checks remain active

#### Scenario: Policy owner contains an operational coordinate

- **WHEN** the portable validator, offline self-containment verifier or a lookalike script contains a literal operational coordinate
- **THEN** it fails closed like any other runtime file; policy constants avoid self-triggering through construction rather than a file-level exception

#### Scenario: Portable locator is used

- **WHEN** an installed artifact uses a skill-relative placeholder, a documented environment root, a generic example path or a valid HTTP(S) URL with a non-empty host
- **THEN** the self-containment gate allows it, including URL path segments that happen to resemble a local directory name

#### Scenario: Generated artifact contains a marker

- **WHEN** a cache, compiled file or other exact runtime-artifact exclusion contains a local marker
- **THEN** it is ignored because it is outside the publication contract, while a manifest-covered text file with the same marker fails closed

#### Scenario: New textual suffix enters the payload

- **WHEN** a manifest-covered UTF-8 file uses a suffix not previously listed as textual
- **THEN** the same self-containment scan applies regardless of suffix; only a non-decodable versioned binary format MAY be exempt, while an undecodable unknown format fails with unchecked-format coverage instead of being reported as validated

### Requirement: Lawinfo method cards preserve substance without maintainer paths

The installed Lawinfo method-card JSON MUST use schema 2.0, MUST omit `original_inbox`, `archive_roots` and `excluded_path`, MUST name the bundled companion as `runtime_reference=lawinfo-constitutional-methods-2023-2026.md`, MUST disclose `source_materials_bundled=false`, MUST identify `sources[].doi` as its `public_locator_field`, and MUST preserve the complete source, card, quarantine and promotion-policy projections. Its companion Markdown MUST direct users to DOI/bibliographic or separately obtained source material for direct quotation and MUST NOT claim that the maintainer PDF archive is available after installation.

#### Scenario: Cleaned Lawinfo payload is installed

- **WHEN** a user or validator opens the JSON and Markdown pair
- **THEN** all 16 sources, 15 method cards and two quarantine records remain with unchanged semantic hashes, no maintainer path key or value remains, and the source-availability boundary is explicit

#### Scenario: Maintainer metadata is reintroduced

- **WHEN** a future edit restores a local path value anywhere in the installed JSON
- **THEN** decoded runtime-self-containment validation fails even if the edit changes field names or JSON escaping

### Requirement: Installed command examples resolve the actual skill root

Every runtime Markdown and public README invocation of a bundled script MUST resolve through a quoted `KSRF_SKILLS_ROOT`. If the variable is unset, the documented resolution MUST use `CODEX_HOME/skills` when `CODEX_HOME` is set and otherwise `$HOME/.codex/skills`. User-facing commands MUST NOT contain `<skill-dir>`, `<skill-root>`, `/path/to/installed/skills` or a fixed `~/.codex/skills` program path. Installation MUST print a shell-safe export for the resolved target and MUST NOT edit a shell profile.

#### Scenario: Default installation command is copied

- **WHEN** a user copies a bundled command without defining any root variable
- **THEN** it resolves the program below `$HOME/.codex/skills`, quotes the program path, and preserves every documented subcommand and option

#### Scenario: Installed public wrapper starts

- **WHEN** the public `ksrf.py` command is invoked from a clean-room installation
- **THEN** it imports the bundled `lib/ksrf` implementation without requiring a repository checkout or a `src` package

#### Scenario: Installed command surface is smoke-tested

- **WHEN** each of the eight unique bundled CLIs named by user-facing documentation is invoked with `--help` from an unrelated working directory
- **THEN** every program loads only its installed dependencies, prints help and exits successfully without mutating user data

#### Scenario: Custom CODEX_HOME or explicit skill root is used

- **WHEN** `CODEX_HOME` or `KSRF_SKILLS_ROOT` points to a directory containing spaces
- **THEN** the same command resolves and executes the bundled program without word splitting, with explicit `KSRF_SKILLS_ROOT` taking precedence

#### Scenario: Custom-target installation completes

- **WHEN** `install.sh --target PATH` succeeds
- **THEN** it prints one POSIX-shell-safe `export KSRF_SKILLS_ROOT=PATH` for the resolved target and does not modify a shell profile

#### Scenario: An unresolved runtime command returns

- **WHEN** either validation profile or the offline verifier encounters an executable bundled-script path using a placeholder or fixed default root
- **THEN** it fails with a command-path resolution finding before the payload is treated as source- or runtime-clean

#### Scenario: Bundled companion reference is named

- **WHEN** a runtime skill links to a companion file in its own `references` directory
- **THEN** the exact relative target resolves inside the installed package and Markdown link validation fails if the target is missing

### Requirement: External HUDOC command resolution is explicit and deterministic

The installed HUDOC KB and vector launchers MUST execute only an exact CLI path
configured by their command-specific override or a version-compatible CLI
resolved below an explicit `HUDOC_KS_PARSER_REPO`. They MUST NOT derive a
repository from HOME, the current working directory or another ambient
filesystem location. Repository worktree lookup, interface-version checks,
subprocess working directory and `PYTHONPATH` composition MUST remain supported.
The installed guidance MUST state that the HUDOC engine is external and not
bundled. When and only when both relevant configuration keys are absent, an
exact lone `-h` or `--help` MAY return local resolver-setup guidance without
candidate discovery or execution; every other unconfigured invocation MUST fail
closed as before, and every present configuration MUST retain the existing
exclusive resolution and version gates.

#### Scenario: Exact HUDOC CLI override is configured

- **WHEN** the command-specific CLI variable names an existing
  version-compatible executable
- **THEN** the launcher uses that exact file without searching HOME, cwd or a
  repository fallback

#### Scenario: Explicit HUDOC repository is configured

- **WHEN** `HUDOC_KS_PARSER_REPO` names a repository root or its main checkout
  has compatible Git worktrees
- **THEN** the launcher deterministically resolves a compatible CLI, preserves
  the selected repository as cwd and composes the required `PYTHONPATH`

#### Scenario: HUDOC integration is unconfigured for an operational command

- **WHEN** neither the command-specific CLI variable nor
  `HUDOC_KS_PARSER_REPO` is set and argv is not exactly one help flag
- **THEN** the launcher fails closed with an actionable message naming the
  accepted variables, and the guidance treats this as an unconfigured
  capability rather than an absence finding

#### Scenario: HUDOC integration is unconfigured for exact help

- **WHEN** neither relevant variable is present and argv is exactly `-h` or
  `--help`
- **THEN** the launcher prints local setup guidance without searching for or
  executing an external engine

#### Scenario: Ambient repository exists

- **WHEN** a compatible `ks_parser` checkout exists below HOME or the current
  directory but no explicit HUDOC variable is set
- **THEN** the launcher ignores it and fails closed instead of executing ambient
  code, except that exact local help may describe explicit setup without search

#### Scenario: Explicit target has an incompatible interface

- **WHEN** an exact CLI or configured repository exposes a pre-contract
  interface version
- **THEN** the existing version gate rejects it and no alternate ambient
  checkout or local bootstrap success is selected

### Requirement: Coordinated runtime verification binds one target observation

A trusted repo-side verification coordinator MUST open the runtime root as a
no-follow directory descriptor before structural preflight, retain that
descriptor through final postflight, and bind status, policy, and content reads
to the retained directory object. It MUST also capture and sample the lexical
root's device, inode, file type, and strict resolved path at phase boundaries.
Coordinated offline success MUST require two equal complete runtime content
identities with the autonomous policy observation between them. A changed,
rebound, symlinked, unavailable, or structurally non-clean target MUST NOT
transfer success to a replacement. The coordinator MUST load only its fixed
repo-side validator, MUST NOT execute target-side code, and MUST NOT claim an
atomic snapshot against arbitrary non-cooperating filesystem writers.

#### Scenario: Lexical root is replaced during validation

- **WHEN** the lexical target is replaced, rebound, converted to a symlink, or resolves elsewhere after its initial anchor
- **THEN** validation reads remain bound to the retained directory object, a replacement cannot inherit its success, and any mismatch present at a phase boundary prevents success

#### Scenario: A transient replacement is restored between samples

- **WHEN** a non-cooperating writer replaces and restores the same lexical path wholly between observable phase-boundary samples
- **THEN** any result describes only the retained directory object that is again bound at output and does not claim detection of that unobservable history or an atomic snapshot

#### Scenario: Runtime content changes during offline verification

- **WHEN** the complete local runtime identity differs between the coordinated initial and final content observations
- **THEN** offline verification records `RUNTIME_IDENTITY_CHANGED`, clears the passing local identity, and exits `1`

#### Scenario: Autonomous policy and content identity diverge

- **WHEN** target content changes after the autonomous policy observation but before the final complete identity
- **THEN** the final identity cannot inherit the earlier policy success and coordinated verification exits `1`

#### Scenario: Postflight becomes non-clean

- **WHEN** transaction evidence, a missing managed package, or unsafe metadata appears before final postflight
- **THEN** the coordinator exits `1` without printing the earlier validation as successful

#### Scenario: Target-side validator is modified

- **WHEN** TARGET contains its own validator with different behavior
- **THEN** coordinated verification ignores it and uses only the fixed regular non-symlink validator in the repository checkout

#### Scenario: Offline coordinator runs

- **WHEN** coordinated runtime verification is requested without current-release comparison
- **THEN** no network opener is called, freshness remains `not_checked`, and the result states that current `main` was not established

### Requirement: Runtime payload omits maintainer change-management traces

Every runtime-eligible text file and its logical runtime path MUST be understandable without access to repository change-management workflow names or numbered maintainer task coordinates. Substantive artifact, negative/conflict-case, held-out evaluation, leakage, observability, provenance, and human-approval gates MUST remain expressed in plain user-facing language. The runtime validator MUST inspect every runtime-eligible logical path plus every normalized or strictly decoded text payload after the same source-only exclusions used by installation, MUST fail closed with stable code `RUNTIME_MAINTAINER_WORKFLOW_REFERENCE` when a maintainer workflow marker is present, and MUST expose only bounded marker classes, the affected runtime path, and no matched file content or source excerpt. Source-only specs, tests, evals, and exact paths classified source-only by the canonical installation contract MAY retain maintainer workflow coordinates because they MUST remain outside the installed payload.

#### Scenario: Exact installed payload contains no maintainer traces

- **WHEN** the canonical release payload is enumerated through the installation file contract
- **THEN** neither a logical runtime path nor its normalized or strictly decoded text contains a repository change-workflow name or numbered internal task coordinate

#### Scenario: Safety gates remain useful after wording cleanup

- **WHEN** a cleaned runtime guide describes a future implementation or evaluation
- **THEN** it still requires the applicable artifact contract, negative/conflict examples, held-out and leakage checks, reproducible tracing, and explicit human approval in language that does not require repository access

#### Scenario: Runtime workflow reference fails closed

- **WHEN** a runtime-eligible text file contains a maintainer change-workflow name, a dotted task coordinate with explicit `internal`/`maintainer`/`repository` context, or a `tasks.md` coordinate
- **THEN** validation fails with `RUNTIME_MAINTAINER_WORKFLOW_REFERENCE`, reports only bounded marker classes and the runtime path, and does not expose matched file content or a source excerpt

#### Scenario: External checkout name is not a runtime marker

- **WHEN** the physical checkout or installation root contains a maintainer marker but all logical runtime paths and content are clean
- **THEN** validation does not report a maintainer-workflow or local-coordinate finding for that external root

#### Scenario: Logical path is scanned before content decoding

- **WHEN** a logical runtime filename contains a maintainer marker, including when the file has a binary suffix or cannot be decoded as UTF-8
- **THEN** validation fails with `RUNTIME_MAINTAINER_WORKFLOW_REFERENCE` and reports that logical runtime path without exposing file content

#### Scenario: Ordinary user tasks and legal numbering are not maintainer traces

- **WHEN** a runtime file contains a bare user-facing `Task 5.1: ...`, statutory provisions, decimal values, numbered headings, dates, or dotted legal references without explicit maintainer context
- **THEN** the maintainer-workflow check does not reject that content

#### Scenario: Source-only evidence may retain maintainer coordinates

- **WHEN** an exact source-only spec, test, eval, or provenance file contains maintainer workflow coordinates
- **THEN** source validation may inspect that material under its existing contracts, while runtime validation and installation exclude it from the user payload

#### Scenario: Runtime provenance receives no blanket exemption

- **WHEN** a manifest-covered runtime guide or data file explains provenance and remains eligible for installation
- **THEN** its logical path and content receive the same maintainer-trace scan as every other runtime file

