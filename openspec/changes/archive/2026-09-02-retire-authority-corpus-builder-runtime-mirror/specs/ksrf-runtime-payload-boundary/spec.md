## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Prebuilt constitutionalist corpus survives builder retirement

Removing the installed corpus builder MUST preserve the prebuilt `constitutionalist-authority-corpus.json` and `constitutionalist-authority-corpus.md` byte-for-byte, preserve their runtime membership and owner route, and preserve every source-status and non-promotion boundary. Runtime documentation MUST direct users to the prebuilt corpus and MUST NOT claim that unavailable source inputs or corpus regeneration are installed.

#### Scenario: User opens the argument-pattern skill

- **WHEN** the user needs constitutionalist methods for one matter
- **THEN** the skill routes to the installed prebuilt corpus, explains its bounded status, and does not instruct the user to run the retired builder

#### Scenario: Maintainer rebuilds the corpus

- **WHEN** all four external input families are available in the source-maintenance environment
- **THEN** the single root release-covered builder remains available without a second copy in any skill

#### Scenario: Cleanup candidate is installed

- **WHEN** the candidate is copied into a clean runtime or exactly replaces an older global runtime
- **THEN** both corpus outputs are byte-identical to the baseline while the retired script is absent and runtime strict validation passes
