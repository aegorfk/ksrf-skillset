## MODIFIED Requirements

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
