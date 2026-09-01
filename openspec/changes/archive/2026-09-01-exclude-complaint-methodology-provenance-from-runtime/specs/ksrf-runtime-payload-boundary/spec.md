## MODIFIED Requirements

### Requirement: Installed payload excludes maintainer-only tests

The canonical KSRF install contract MUST exclude files under any skill-relative `tests` or `evals` path component and MUST exclude only the versioned exact maintainer-file identities. It MUST classify `ksrf-argument-patterns/references/complaint-methodology-sources.md` as a tracked source-only provenance journal and MUST exclude that exact identity from user installation without excluding similarly named Markdown files. The two retired runtime identities `ksrf-argument-patterns/scripts/enrich_ksrf_argument_patterns.py` and `ksrf-argument-patterns/scripts/extract_ksrf_argument_patterns.py` MUST NOT exist as tracked skill duplicates; their canonical root-only copies MUST remain under `tools/` and covered by the release manifest.

#### Scenario: Provenance journal is installed

- **WHEN** manifest generation or installation encounters the exact journal identity
- **THEN** it is omitted, while source validation still scans it and lookalike Markdown remains eligible

#### Scenario: Runtime contains the provenance journal

- **WHEN** runtime-profile validation encounters the exact journal identity
- **THEN** validation fails with `SOURCE_ONLY_ARTIFACT_PRESENT`

#### Scenario: Source repository contains the provenance journal

- **WHEN** source/release validation inspects the canonical tracked file
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

Manifest generation, runtime installation, tree-hash verification, source-only provenance ownership, release-tool ownership, and reverse synchronization MUST use the same versioned contract. The provenance journal MUST remain byte-preserved by reverse sync and MUST NOT be required in the installed runtime. No installed user-facing `SKILL.md`, Markdown/JSON reference, or operational builder/verifier MAY refer to its excluded basename; the portable validator MAY retain the exact identity solely as fail-closed policy data.

#### Scenario: Global runtime is synchronized back to source

- **WHEN** global KSRF skills do not contain the provenance journal or the two root-only generators
- **THEN** reverse sync succeeds, preserves all three source-owned files byte-for-byte, and still mirrors `build_constitutionalist_authority_corpus.py`

#### Scenario: Clean-room runtime is inspected

- **WHEN** the exact manifest payload is installed to an empty directory
- **THEN** neither the provenance journal nor any backlink to its basename exists, and all successor references resolve inside runtime

#### Scenario: Corpus metadata is generated

- **WHEN** the canonical builder regenerates `constitutionalist-authority-corpus.json`
- **THEN** root/mirrored builders and generated metadata refer only to retained runtime references

### Requirement: Cleanup does not weaken development or legal gates

The provenance cleanup MUST preserve source/public security checks, source tests and evals, strict OpenSpec validation, explicit publication authority, all legal/human review gates, and an independently reviewed mapping from every transferable source method/check to `retained`, `superseded`, or `intentionally_rejected`. Automated validation MUST cover exact payload behavior, critical transferred gaps, and dead runtime routes; it MUST NOT be represented as a complete semantic proof of every mapping row.

#### Scenario: Provenance journal contains unsafe source material

- **WHEN** the tracked journal contains a secret, absolute local path, symlink, or complaint-like artifact
- **THEN** source/repository validation rejects it even though the runtime contract excludes it

#### Scenario: Critical transferred methodology is removed or unrouted

- **WHEN** either newly transferred hearing/remedy-access gate or a routed retained successor is absent
- **THEN** regression validation or independent semantic review blocks publication rather than treating source-only exclusion as evidence that methodology survived
