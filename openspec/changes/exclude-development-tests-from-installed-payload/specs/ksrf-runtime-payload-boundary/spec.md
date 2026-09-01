## ADDED Requirements

### Requirement: Installed payload excludes maintainer-only tests

The canonical KSRF install contract MUST exclude files under any skill-relative `tests` path component while retaining those files in the source repository.

#### Scenario: Skill contains unit tests and fixtures

- **WHEN** manifest generation or installation enumerates a skill containing `tests/test_example.py` and `tests/fixtures/example.json`
- **THEN** neither file is included in the manifest-covered payload or copied to the install target

#### Scenario: Runtime package contains ordinary resources

- **WHEN** the same skill contains `SKILL.md`, `agents/`, `evals/`, `lib/`, `references/`, `schemas/`, or `scripts/`
- **THEN** those files remain eligible for the payload under the existing secret/runtime exclusions

#### Scenario: Global skills are synchronized back to source

- **WHEN** the canonical reverse-sync command replaces repository runtime files from global skills
- **THEN** tracked target `tests/` files are preserved byte-for-byte while stale runtime files are removed

### Requirement: One exact file contract governs distribution

Manifest generation, runtime installation, and tree-hash verification MUST use the same runtime file-selection contract and MUST fail when installed bytes differ from the manifest. Reverse sync MUST invoke an explicit source-preserving mode instead of treating the installed runtime tree as a complete source package. Installation MUST fail before writing when the source and target paths are equal or either path contains the other.

#### Scenario: Clean-room install is verified

- **WHEN** a release candidate is installed into an empty target
- **THEN** its file count, total bytes, package hashes, and top-level tree hash exactly match the regenerated manifest

#### Scenario: Install target overlaps the source tree

- **WHEN** an operator selects the source directory itself, one of its descendants, or one of its ancestors as the install target
- **THEN** installation is refused before any source or target file is replaced

### Requirement: Cleanup does not weaken development or legal gates

Excluding tests from the installed payload MUST NOT delete source tests, exclude behavioral evals, remove OpenSpec evidence, or expand legal, human-review, filing, or publication authority.

#### Scenario: Source release is prepared

- **WHEN** the cleaned runtime payload is published
- **THEN** source tests and strict OpenSpec/skillset validation still pass from the canonical checkout and all legal gates remain unchanged
