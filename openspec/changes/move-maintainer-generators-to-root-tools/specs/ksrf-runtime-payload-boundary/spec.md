## MODIFIED Requirements

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
