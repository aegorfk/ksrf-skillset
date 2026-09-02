## Why

The exact installed payload still contains 15 repository-local markers on 14 lines across seven runtime references. Paths such as `ТЗ/...` and `<project-root>/ТЗ/...` do not exist after a normal skill installation. They make maintenance provenance look like a user capability, and several sentences tell the user to open source files that are not shipped.

## What Changes

- Remove all unavailable repository coordinates from the seven affected installed Markdown/JSON references.
- Preserve bibliographic descriptions, DOI values, source hashes, corpus sizes, operational method cards, legal boundaries and public URLs.
- Replace local-path instructions with truthful routes: bundled reference content, public/official sources, DOI/bibliographic lookup, or an explicit statement that a source artifact is not installed and cannot be quoted without separate access.
- Bump the Lawinfo method-card JSON schema to 2.0, remove the maintainer-only `original_inbox`, `archive_roots` and `excluded_path` fields, and replace them with stable runtime metadata: `runtime_reference`, `source_materials_bundled=false` and `public_locator_field`. Preserve its 16 sources, 15 cards and two quarantine records unchanged.
- Add one portable runtime-self-containment gate used by both validation profiles. It attempts UTF-8 decoding for every manifest-eligible artifact and scans every successful decode regardless of suffix; only non-decodable declared binary formats are non-applicable. It strictly decodes JSON, normalizes Unicode and separators, and rejects repository-local markers while honoring only the shared source/generated publication boundaries. Enforcement code constructs marker constants without embedding a literal bypass.
- Add RED/GREEN regressions, exact semantic-preservation checks, clean-room installation checks and publication evidence.

## Capabilities

### Modified Capabilities

- `ksrf-runtime-payload-boundary`: every installed user reference is location-independent and validation fails closed when a repository-local coordinate returns.

## Impact

- Frozen live base: `ad980d5cbe648e58fed28ec97645f3125c90791f`.
- Runtime baseline: 15 packages / 234 files / 8,014,038 bytes / tree SHA-256 `0067e91e9a2a038eac41474a3cc24adad43e8fc19aa8439cd0c814863b95c140`.
- Baseline exposure: 15 marker occurrences, 14 affected lines, seven installed files; five occurrences include `<project-root>`.
- Lawinfo semantic baselines: 16 sources (`cc3fd54ef9b6c370dc1063908bc8838c5b2920774fb2878230ae5ffcca5a56f0`), 15 cards (`55039ef631e8845b2f8078b9ea808bb33e7cee174ee9d637744e45eb5fcda68b`), two quarantine records (`570eb92339e51512bc4e507fe1b47ef9ada5021a4edc613d0ccbe0e75cd7c5d6`) and unchanged promotion policy (`ba8d82b99f2d00879642cf7e04eff22b7865f8c794fa31e16629d75c0babddb5`).
- Final runtime: 15 packages / 234 files / 8,022,354 bytes / tree SHA-256 `d3193937fd539c7d4142c05f3312620ddba4a1de6f8f43cce187c23e43ca2654`; release tree remains `afe11148478193f80ef30f8af08beac7ee82d0d2ff747c984dc62f550b613851`; manifest-covered local-coordinate findings: zero.
- Final cleaned-reference SHA-256 values: argument techniques `9de68157ba91a84ba71a36a7149bac0d9b22c731241df54f991a41fb88911839`, constitutional methods `86f3273e06f6514dcbe81bda0c3ea2a39ed2c8bd3dfa757bf46d40ebd9ad9d06`, hearing techniques `4e47d23d8efc5637ad976cd930c416961069701d69709277f7644e3f7a4d84f8`, Lawinfo Markdown `fea883658d15a40352e87c918916a4684afc6e8318df01e493a4efdd77f7467f`, Lawinfo JSON `4afd31ca35e25ab5f67402f6d25eb8e2dbd7cbdb5dc91e0a12b44def5f0b7911`, embedded guides `2fe041a6fec775158198d9c9326ec7a6724690be7aef334fded42db36f492d17`, science pack `1c35517669c33376f787b7119fa96cda6a48c8c4fe90d5a1dc29660732e18c48`.
- No legal holding, official-source status, method promotion, admissibility gate, filing authority or user data changes.
