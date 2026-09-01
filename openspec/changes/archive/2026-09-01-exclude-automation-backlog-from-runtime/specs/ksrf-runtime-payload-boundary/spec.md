## MODIFIED Requirements

### Requirement: Installed payload excludes maintainer-only tests

The canonical KSRF install contract MUST exclude files under any skill-relative `tests` or `evals` path component and MUST exclude only the versioned exact maintainer-file identities. It MUST classify both `ksrf-argument-patterns/references/complaint-methodology-sources.md` and `ksrf-argument-patterns/references/automation-backlog.md` as tracked source-only maintainer documents and MUST exclude those exact identities from user installation without excluding similarly named Markdown files. The two retired runtime identities `ksrf-argument-patterns/scripts/enrich_ksrf_argument_patterns.py` and `ksrf-argument-patterns/scripts/extract_ksrf_argument_patterns.py` MUST NOT exist as tracked skill duplicates; their canonical root-only copies MUST remain under `tools/` and covered by the release manifest.

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

- **WHEN** manifest generation, installation, or runtime validation encounters either retired exact skill path
- **THEN** the path is excluded from runtime, runtime validation reports `SOURCE_ONLY_ARTIFACT_PRESENT`, and similarly named files outside the exact identity remain eligible

#### Scenario: Source repository is prepared

- **WHEN** source/release validation inspects the repository
- **THEN** both nested duplicates are absent, both root-only tools are regular tracked files, and both remain included in release-file hashes

#### Scenario: Benign nested duplicate is reintroduced

- **WHEN** either retired exact skill path exists again even with otherwise safe content
- **THEN** canonical repository/manifest validation and portable source validation fail closed instead of silently excluding the duplicate

### Requirement: One exact file contract governs distribution

Manifest generation, runtime installation, tree-hash verification, source-only maintainer ownership, release-tool ownership, and reverse synchronization MUST use the same versioned contract. Both source-only Markdown files MUST remain byte-preserved by reverse sync and MUST NOT be required in installed runtime. No installed user-facing `SKILL.md`, Markdown/JSON reference, or operational builder/verifier MAY refer to either excluded basename; the portable validator MAY retain exact identities solely as fail-closed policy data.

#### Scenario: Global runtime is synchronized back to source

- **WHEN** global KSRF skills do not contain either source-only Markdown file or the two root-only generators
- **THEN** reverse sync succeeds, preserves every source-owned file byte-for-byte, and still mirrors the canonical runtime builder

#### Scenario: Clean-room runtime is inspected

- **WHEN** the exact manifest payload is installed to an empty directory
- **THEN** neither source-only Markdown file nor any user-facing backlink to either basename exists, and all replacement routes resolve inside runtime

#### Scenario: Same or similar basename is encountered outside the exact identity

- **WHEN** another package contains `references/automation-backlog.md` or the canonical package contains `references/automation-backlog-runtime.md`
- **THEN** it remains runtime-eligible if it passes all other checks

### Requirement: Cleanup does not weaken development or legal gates

Runtime cleanup MUST preserve source/public security checks, source tests and evals, strict OpenSpec validation, explicit publication authority, all legal/human review gates, and an independently reviewed ownership map for every removed source-only method or proposed checker. Automated validation MUST cover exact payload behavior, route existence and dead runtime backlinks; it MUST NOT represent a planned automation as shipped functionality or an ownership table as substantive legal validation.

#### Scenario: Source-only backlog contains unsafe source material

- **WHEN** the tracked backlog contains a secret, absolute local path, symlink, or complaint-like artifact
- **THEN** source/repository validation rejects it even though runtime distribution excludes it

#### Scenario: Replacement route is absent

- **WHEN** a runtime backlink is removed but its referenced operational owner does not exist in the installed payload
- **THEN** regression validation blocks publication

### Requirement: Validator distinguishes source and runtime assurance

The portable validator MUST provide explicit `source` and `runtime` profiles. The `source` profile MUST validate behavioral and trigger evals, security-scan all source-only assets, invoke the canonical public-source artifact contract, and remain the default. The `runtime` profile MAY skip only eval-specific checks, MUST reject any remaining source-only `tests/`, `evals/`, or versioned exact maintainer-file artifact, and MUST preserve all other package, content, link, metadata, security, and cross-contract checks. Every report MUST identify the profile, state whether evals, skill-source safety, and repository-source safety were validated, and state whether it is eligible as source-release evidence. Missing public-source contract coverage or absence of a repository-wide scan in the canonical source checkout MUST prevent source release eligibility. A runtime report MUST NOT expose a `publish_manifest`, and runtime CLI invocation MUST reject standalone manifest output.

#### Scenario: Source profile has missing evals

- **WHEN** a source package is validated with the `source` profile and either eval file is absent
- **THEN** validation fails with the existing missing-eval findings

#### Scenario: Source profile contains an exact maintainer file

- **WHEN** source validation reaches any versioned exact maintainer file
- **THEN** the file is excluded from the portable publish manifest but remains covered by secret, local-path, symlink, and public-source checks

#### Scenario: Runtime profile validates an installed package

- **WHEN** the same runtime package has no source-only artifacts
- **THEN** validation can pass if every non-eval check passes and the report says eval validation was not checked, `source_release_eligible=false`, and `publish_manifest=null`

#### Scenario: Runtime profile is used on source checkout

- **WHEN** runtime-profile validation finds a file under any `tests/` or `evals/` path component or at any versioned exact maintainer path
- **THEN** validation fails with `SOURCE_ONLY_ARTIFACT_PRESENT`

#### Scenario: Runtime result is rendered or serialized

- **WHEN** a runtime-profile report is emitted as text or JSON
- **THEN** it visibly states that runtime validation does not replace source/release QA

#### Scenario: Runtime caller requests standalone publish manifest

- **WHEN** CLI is invoked with `--profile runtime --manifest-out`
- **THEN** it exits nonzero without writing a manifest

#### Scenario: Partial source validation succeeds

- **WHEN** source profile validates fewer than the exact canonical 15 packages
- **THEN** the report sets `source_release_eligible=false` even if the selected packages pass

#### Scenario: Canonical public-source contract is unavailable

- **WHEN** source profile cannot load the canonical public-source artifact validator
- **THEN** it reports both public-source coverage fields as `not_checked`, emits a warning, and keeps `source_release_eligible=false`

#### Scenario: Unknown profile reaches the Python API

- **WHEN** a caller supplies a validation profile other than `source` or `runtime`
- **THEN** validation fails closed before producing a passing report
