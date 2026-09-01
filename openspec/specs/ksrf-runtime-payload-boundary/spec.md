# ksrf-runtime-payload-boundary Specification

## Purpose
TBD - created by archiving change exclude-development-tests-from-installed-payload. Update Purpose after archive.
## Requirements
### Requirement: Installed payload excludes maintainer-only tests

The canonical KSRF install contract MUST exclude files under any skill-relative `tests` or `evals` path component and MUST exclude only the versioned exact maintainer-file pairs below while retaining all of those files in the source repository:

- `ksrf-argument-patterns/references/hearing_argument_techniques.json`
- `ksrf-argument-patterns/references/language_formulas.json`
- `ksrf-argument-patterns/references/evidence_maps.json`
- `ksrf-argument-patterns/references/argument_techniques_from_decisions.json`
- `ksrf-complaint-cycle/scripts/add_reference_tocs.py`

#### Scenario: Skill contains unit tests, fixtures, and eval suites

- **WHEN** manifest generation or installation enumerates a skill containing `tests/test_example.py`, `tests/fixtures/example.json`, `evals/evals.json`, and `evals/trigger-evals.json`
- **THEN** none of those files is included in the manifest-covered payload or copied to the install target

#### Scenario: Exact maintainer files are enumerated

- **WHEN** manifest generation or installation reaches any of the five versioned skill/path pairs
- **THEN** that file is omitted from the runtime payload while its tracked source copy remains unchanged

#### Scenario: Runtime package contains ordinary resources

- **WHEN** the same skill contains `SKILL.md`, `agents/`, `lib/`, `references/`, `schemas/`, or `scripts/` outside the exact source-only contract
- **THEN** those files remain eligible for the payload under the existing secret/runtime exclusions

#### Scenario: Similar names must not overmatch

- **WHEN** another skill contains `references/evidence_maps.json` or the target skill contains `references/evidence_maps-guide.json`, active `constitutional_graph.json`, schemas, configs, or an ordinary runtime script
- **THEN** the file remains runtime-eligible

#### Scenario: Global skills are synchronized back to source

- **WHEN** the canonical reverse-sync command replaces repository runtime files from global skills
- **THEN** tracked target `tests/`, `evals/`, and five exact maintainer files are preserved byte-for-byte while stale runtime files are removed

### Requirement: One exact file contract governs distribution

Manifest generation, runtime installation, and tree-hash verification MUST use the same runtime file-selection contract and MUST fail when installed bytes differ from the manifest. Reverse sync MUST invoke an explicit source-preserving mode instead of treating the installed runtime tree as a complete source package. Installation MUST fail before writing when the source and target paths are equal or either path contains the other.

#### Scenario: Clean-room install is verified

- **WHEN** a release candidate is installed into an empty target
- **THEN** its file count, total bytes, package hashes, and top-level tree hash exactly match the regenerated manifest

#### Scenario: Install target overlaps the source tree

- **WHEN** an operator selects the source directory itself, one of its descendants, or one of its ancestors as the install target
- **THEN** installation is refused before any source or target file is replaced

### Requirement: Cleanup does not weaken development or legal gates

Excluding source-only assets from the installed payload MUST NOT delete source QA assets, remove OpenSpec evidence, bypass public-source safety checks, or expand legal, human-review, filing, or publication authority.

#### Scenario: Source release is prepared

- **WHEN** the cleaned runtime payload is published
- **THEN** source tests, behavioral/trigger eval validation, strict OpenSpec, source-only artifact checks, and skillset validation pass from the canonical checkout and all legal gates remain unchanged

#### Scenario: Forbidden public artifact is hidden under development paths

- **WHEN** a complaint-like or otherwise forbidden source artifact is placed under `tests/`, `evals/`, or one of the exact maintainer-only paths
- **THEN** repository publication validation still rejects it even though distribution excludes that file

#### Scenario: Installed guide discusses retrieval evaluation

- **WHEN** a user reads the runtime retrieval guide after installation
- **THEN** it does not require absent eval datasets or runner scripts and instead gives manual evidence checks and stop rules

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

