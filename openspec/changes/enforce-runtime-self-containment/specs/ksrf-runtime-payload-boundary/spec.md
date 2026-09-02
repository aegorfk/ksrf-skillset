## ADDED Requirements

### Requirement: Installed references are location-independent

Every runtime-eligible textual artifact in the canonical KSRF payload MUST be usable without the maintainer repository or its private source tree. Installed Markdown, JSON, YAML, text and executable guidance MUST NOT contain a repository-local `ТЗ/...` coordinate, a `<project-root>` placeholder, or a macOS, Linux or Windows user-home absolute path. Source-only artifacts MAY retain maintenance provenance only when the shared versioned file contract excludes them from installation and source/repository security validation still covers them. Policy-owner scripts MUST be scanned under the same rule and MUST construct enforcement markers without embedding an exempt literal.

#### Scenario: Clean-room runtime is inspected

- **WHEN** the exact manifest payload is installed into an empty directory
- **THEN** every runtime-eligible artifact is free of repository-local coordinates, all 15 packages validate in runtime profile, and bundled links still resolve

#### Scenario: User opens derived methodology

- **WHEN** a reference was derived from a source artifact that is not shipped
- **THEN** it preserves usable bibliography, DOI, hash, public URL or source-count provenance where available, states the availability boundary, and does not instruct the user to open a nonexistent local path

#### Scenario: Local coordinate returns in Markdown or code

- **WHEN** either validation profile encounters a runtime-eligible artifact containing `ТЗ/...`, `<project-root>` or a user-home absolute path
- **THEN** validation fails with a runtime-self-containment finding before the payload is treated as release-ready or runtime-clean

#### Scenario: Local coordinate is JSON-escaped

- **WHEN** a runtime JSON string encodes the same coordinate with Unicode or slash escapes
- **THEN** the portable validator decodes and normalizes it and fails with the same runtime-self-containment finding

#### Scenario: Source-only maintainer evidence contains a coordinate

- **WHEN** source validation encounters a coordinate inside an exact source-only artifact
- **THEN** the runtime-self-containment gate does not overmatch it, the artifact remains absent from the publish manifest, and existing source/repository safety checks remain active

#### Scenario: Policy owner contains an operational coordinate

- **WHEN** the portable validator, offline self-containment verifier or a lookalike script contains a literal operational coordinate
- **THEN** it fails closed like any other runtime file; policy constants avoid self-triggering through construction rather than a file-level exception

#### Scenario: Portable locator is used

- **WHEN** an installed artifact uses a skill-relative placeholder, a documented environment root, a generic example path or a valid HTTP(S) URL with a non-empty host
- **THEN** the self-containment gate allows it, including URL path segments that happen to resemble a local directory name

#### Scenario: Generated artifact contains a marker

- **WHEN** a cache, compiled file or other exact runtime-artifact exclusion contains a local marker
- **THEN** it is ignored because it is outside the publication contract, while a manifest-covered text file with the same marker fails closed

#### Scenario: New textual suffix enters the payload

- **WHEN** a manifest-covered UTF-8 file uses a suffix not previously listed as textual
- **THEN** the same self-containment scan applies regardless of suffix; only a non-decodable versioned binary format MAY be exempt, while an undecodable unknown format fails with unchecked-format coverage instead of being reported as validated

### Requirement: Lawinfo method cards preserve substance without maintainer paths

The installed Lawinfo method-card JSON MUST use schema 2.0, MUST omit `original_inbox`, `archive_roots` and `excluded_path`, MUST name the bundled companion as `runtime_reference=lawinfo-constitutional-methods-2023-2026.md`, MUST disclose `source_materials_bundled=false`, MUST identify `sources[].doi` as its `public_locator_field`, and MUST preserve the complete source, card, quarantine and promotion-policy projections. Its companion Markdown MUST direct users to DOI/bibliographic or separately obtained source material for direct quotation and MUST NOT claim that the maintainer PDF archive is available after installation.

#### Scenario: Cleaned Lawinfo payload is installed

- **WHEN** a user or validator opens the JSON and Markdown pair
- **THEN** all 16 sources, 15 method cards and two quarantine records remain with unchanged semantic hashes, no maintainer path key or value remains, and the source-availability boundary is explicit

#### Scenario: Maintainer metadata is reintroduced

- **WHEN** a future edit restores a local path value anywhere in the installed JSON
- **THEN** decoded runtime-self-containment validation fails even if the edit changes field names or JSON escaping
