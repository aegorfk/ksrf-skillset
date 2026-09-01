## MODIFIED Requirements

### Requirement: Installed payload excludes maintainer-only tests

The canonical KSRF install contract MUST exclude files under any skill-relative `tests` or `evals` path component while retaining those files in the source repository.

#### Scenario: Skill contains unit tests, fixtures, and eval suites

- **WHEN** manifest generation or installation enumerates a skill containing `tests/test_example.py`, `tests/fixtures/example.json`, `evals/evals.json`, and `evals/trigger-evals.json`
- **THEN** none of those files is included in the manifest-covered payload or copied to the install target

#### Scenario: Runtime package contains ordinary resources

- **WHEN** the same skill contains `SKILL.md`, `agents/`, `lib/`, `references/`, `schemas/`, or `scripts/`
- **THEN** those files remain eligible for the payload under the existing secret/runtime exclusions

#### Scenario: Global skills are synchronized back to source

- **WHEN** the canonical reverse-sync command replaces repository runtime files from global skills
- **THEN** tracked target `tests/` and `evals/` files are preserved byte-for-byte while stale runtime files are removed

### Requirement: Cleanup does not weaken development or legal gates

Excluding tests and evals from the installed payload MUST NOT delete source QA assets, remove OpenSpec evidence, bypass public-source safety checks, or expand legal, human-review, filing, or publication authority.

#### Scenario: Source release is prepared

- **WHEN** the cleaned runtime payload is published
- **THEN** source tests, behavioral/trigger eval validation, strict OpenSpec, and skillset validation pass from the canonical checkout and all legal gates remain unchanged

#### Scenario: Forbidden public artifact is hidden under development paths

- **WHEN** a complaint-like or otherwise forbidden source artifact is placed under a source `tests/` or `evals/` directory
- **THEN** repository publication validation still rejects it even though distribution excludes that directory

#### Scenario: Installed guide discusses retrieval evaluation

- **WHEN** a user reads the runtime retrieval guide after installation
- **THEN** it does not require absent eval datasets or runner scripts and instead gives manual evidence checks and stop rules

## ADDED Requirements

### Requirement: Validator distinguishes source and runtime assurance

The portable validator MUST provide explicit `source` and `runtime` profiles. The `source` profile MUST validate behavioral and trigger evals, invoke the canonical public-source artifact contract over source-only assets, and remain the default. The `runtime` profile MAY skip only eval-specific checks, MUST reject any remaining source-only `tests/` or `evals/` artifact, and MUST preserve all other package, content, link, metadata, security, and cross-contract checks. Every report MUST identify the profile, state whether evals, skill-source safety, and repository-source safety were validated, and state whether it is eligible as source-release evidence. Missing public-source contract coverage or absence of a repository-wide scan in the canonical source checkout MUST prevent source release eligibility. A runtime report MUST NOT expose a `publish_manifest`, and runtime CLI invocation MUST reject standalone manifest output.

#### Scenario: Source profile has missing evals

- **WHEN** a source package is validated with the `source` profile and either eval file is absent
- **THEN** validation fails with the existing missing-eval findings

#### Scenario: Runtime profile validates an installed package

- **WHEN** the same runtime package has no `evals/` directory and is validated with the `runtime` profile
- **THEN** validation can pass if every non-eval check passes and the report says eval validation was not checked, `source_release_eligible=false`, and `publish_manifest=null`

#### Scenario: Runtime profile is used on source checkout

- **WHEN** a runtime-profile validation finds a file under any `tests/` or `evals/` path component
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
