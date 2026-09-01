# ksrf-runtime-payload-boundary Specification

## Purpose
TBD - created by archiving change exclude-development-tests-from-installed-payload. Update Purpose after archive.
## Requirements
### Requirement: Installed payload excludes maintainer-only tests

The canonical KSRF install contract MUST exclude files under any skill-relative `tests` or `evals` path component and MUST exclude only the versioned exact maintainer-file identities. The two retired runtime identities `ksrf-argument-patterns/scripts/enrich_ksrf_argument_patterns.py` and `ksrf-argument-patterns/scripts/extract_ksrf_argument_patterns.py` MUST NOT exist as tracked skill duplicates; their canonical root-only copies MUST remain under `tools/` and covered by the release manifest.

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

Manifest generation, runtime installation, tree-hash verification, release-tool ownership, and reverse synchronization MUST use the same versioned contract. Mirrored runtime tools, root-only release tools, and explicitly retired mirrors MUST be disjoint. Reverse sync MUST require and copy only active mirrored tools and MUST neither require nor remove root-only tools.

#### Scenario: Global runtime is synchronized back to source

- **WHEN** global KSRF skills do not contain the two root-only generators
- **THEN** reverse sync succeeds, preserves both root tools byte-for-byte, and still mirrors `build_constitutionalist_authority_corpus.py`

#### Scenario: Release manifest is generated

- **WHEN** `skills-manifest.json` is rebuilt
- **THEN** release files include both root-only tools and their exact hashes even though the runtime skill file list excludes the retired nested paths

#### Scenario: Root enrich tool uses defaults

- **WHEN** the root enrich tool is invoked without `--skill`
- **THEN** its default target resolves to `<repo>/skills/ksrf-argument-patterns`

#### Scenario: Root-only release tool contains unsafe local material

- **WHEN** either root-only tool contains an embedded token, private-key marker, secret assignment, or absolute local path
- **THEN** source/release validation fails before manifest publication without echoing the secret value

### Requirement: Cleanup does not weaken development or legal gates

The ownership migration MUST preserve source/public security checks, source tests and evals, strict OpenSpec validation, explicit publication authority, and all legal/human review gates.

#### Scenario: Retired path is accidentally reintroduced with unsafe content

- **WHEN** either retired exact skill path reappears with a secret, absolute local path, symlink, or complaint-like artifact
- **THEN** source/repository validation rejects both the duplicate identity and its unsafe content even though the runtime contract excludes it

### Requirement: Validator distinguishes source and runtime assurance

The portable validator MUST provide explicit `source` and `runtime` profiles. The `source` profile MUST validate behavioral and trigger evals, security-scan all source-only assets, invoke the canonical public-source artifact contract, and remain the default. The `runtime` profile MAY skip only eval-specific checks, MUST reject any remaining source-only `tests/`, `evals/`, or exact maintainer-file artifact, and MUST preserve all other package, content, link, metadata, security, and cross-contract checks. Every report MUST identify the profile, state whether evals, skill-source safety, and repository-source safety were validated, and state whether it is eligible as source-release evidence. Missing public-source contract coverage or absence of a repository-wide scan in the canonical source checkout MUST prevent source release eligibility. A runtime report MUST NOT expose a `publish_manifest`, and runtime CLI invocation MUST reject standalone manifest output.

#### Scenario: Source profile has missing evals

- **WHEN** a source package is validated with the `source` profile and either eval file is absent
- **THEN** validation fails with the existing missing-eval findings

#### Scenario: Source profile contains an exact maintainer file

- **WHEN** source validation reaches one of the five exact files
- **THEN** the file is excluded from the portable publish manifest but remains covered by secret, local-path, symlink, and public-source checks

#### Scenario: Runtime profile validates an installed package

- **WHEN** the same runtime package has no source-only artifacts
- **THEN** validation can pass if every non-eval check passes and the report says eval validation was not checked, `source_release_eligible=false`, and `publish_manifest=null`

#### Scenario: Runtime profile is used on source checkout

- **WHEN** runtime-profile validation finds a file under any `tests/` or `evals/` path component or at one of the five exact maintainer paths
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

