## MODIFIED Requirements

### Requirement: Validator distinguishes source and runtime assurance

The portable validator MUST provide explicit `source` and `runtime` profiles. The `source` profile MUST validate behavioral and trigger evals, security-scan all source-only assets, invoke the canonical public-source artifact contract, and remain the default. The `runtime` profile MAY skip only eval-specific checks, MUST reject any remaining source-only `tests/`, `evals/`, versioned maintainer specifications, or exact maintainer-file artifact, and MUST preserve all other package, content, link, metadata, security, and cross-contract checks. Every report MUST identify the profile, coverage, source-release eligibility, and a deterministic identity for the runtime-eligible bytes observed. A runtime report MUST NOT expose a `publish_manifest`, and runtime CLI invocation MUST reject standalone manifest output.

Runtime freshness lookup MUST be disabled by default. An explicit runtime-only update check MUST resolve canonical GitHub `main`, fetch the manifest at that immutable commit, and report `current`, `different`, or `unknown` without writing files or changing validation exit semantics. It MUST NOT call unequal content definitely outdated, MUST NOT turn unavailable coverage into a current result, and MUST NOT represent runtime or freshness validation as source-release, publication, legal, or filing authority.

#### Scenario: Default runtime validation is offline

- **WHEN** runtime validation is invoked without an update-check option
- **THEN** no network opener is called, the report includes the local runtime identity, and freshness is `not_checked`

#### Scenario: Runtime identity is emitted

- **WHEN** all runtime-eligible files remain stable while validation hashes them
- **THEN** the report exposes the same aggregate tree SHA-256, file count, and byte count as the canonical release manifest algorithm, while `publish_manifest` remains null

#### Scenario: Runtime file changes between manifest and identity passes

- **WHEN** a runtime file becomes unreadable or its size or digest changes before aggregate identity is finalized
- **THEN** validation records a bounded error, emits no passing local identity, and any requested freshness result is `unknown`

#### Scenario: Installed content equals current main

- **WHEN** explicit runtime update checking resolves one valid canonical `main` commit and the pinned manifest tree hash equals the local runtime tree hash
- **THEN** freshness is `current`, reports the compared remote SHA and hashes, and explains byte equivalence without claiming installation provenance

#### Scenario: Installed content differs from current main

- **WHEN** both local and pinned remote identities are valid but unequal
- **THEN** freshness is `different` and explains that the local tree may be older, customized, or locally modified

#### Scenario: Freshness evidence is unavailable

- **WHEN** the ref or manifest request fails, exceeds its byte cap, redirects outside the fixed allowlist, returns malformed or schema-invalid JSON, contains an invalid SHA/hash/count, or local identity is unavailable
- **THEN** freshness is `unknown` with a bounded reason code and the report does not claim current content

#### Scenario: Branch moves after ref resolution

- **WHEN** canonical `main` advances after its SHA was resolved
- **THEN** the comparison uses the manifest fetched by the already resolved immutable SHA rather than refetching by branch name

#### Scenario: Source caller requests online freshness

- **WHEN** `--check-updates` is combined with the source profile
- **THEN** CLI rejects the combination as a usage error before network access

#### Scenario: Partial runtime caller requests online freshness

- **WHEN** `--check-updates` is combined with a package selection smaller than the canonical 15-package runtime
- **THEN** CLI rejects the combination before network access because the partial local tree is not comparable with the canonical remote manifest

#### Scenario: Freshness result is rendered

- **WHEN** runtime validation emits human or JSON output
- **THEN** the local identity and freshness state use bounded stable fields, Russian human guidance remains concise, and runtime/source-release boundaries remain explicit
