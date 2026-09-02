## Context

Maintainer coordinates survived in seven files that are intentionally shipped to users. Source-only extraction logs and backlogs are already excluded by the versioned file contract; the problem is limited to runtime-eligible references and therefore cannot be solved by adding more broad exclusions without discarding useful methodology.

## Goals / Non-Goals

Goals:

- make every installed reference usable without the repository checkout;
- retain all substantive methods, provenance identifiers and legal stop rules;
- distinguish a bibliographic/source fingerprint from an unavailable local file location;
- prevent literal, JSON-escaped and Unicode-normalized local coordinates from returning;
- publish and install one exact verified payload.

Non-goals:

- publish private source PDFs, transcripts, complaint samples or maintenance logs;
- claim public access where only bibliographic metadata is available;
- remove source-only maintainer evidence from the repository;
- alter a method card, legal conclusion, promotion policy or filing gate.

## Decisions

1. **Rewrite, do not exclude.** The seven references contain user value. Only their unavailable coordinates are removed.
2. **Provenance without capability theatre.** Bibliography, DOI, hashes, source counts and public URLs remain. Where an original is not bundled, the reference says so and blocks direct quotation until the user separately obtains and checks it.
3. **Lawinfo schema 2.0.** Removing three maintainer-only JSON metadata fields is explicit. Stable replacements name the bundled Markdown (`runtime_reference`), state the availability boundary (`source_materials_bundled=false`) and identify the public lookup route (`public_locator_field=sources[].doi`). All `sources`, `cards`, `quarantine` and `promotion_policy` projections are hash-pinned.
4. **One portable gate.** `validate_ksrf_skillset.py` attempts UTF-8 decoding for every manifest-eligible artifact in both profiles and scans every successful decode regardless of suffix, including text disguised with a binary extension. It uses the same source-only and generated-artifact boundaries as publication. Only a non-decodable artifact with a versioned binary suffix is non-applicable to text scanning; an undecodable unknown format fails closed instead of receiving false `validated` coverage.
5. **Fail closed across encodings.** JSON values are strictly decoded before scanning and all inspected text is normalized with NFKC and path-separator normalization. Duplicate keys, invalid JSON and undecodable unknown formats fail closed. A marker cannot bypass the gate by using `\uXXXX` JSON escapes, mixed separators or full-width characters.
6. **No policy-owner blind spot.** The portable validator and offline self-containment verifier construct marker constants by concatenation and are scanned like every other runtime file. No file, basename or directory-wide exception is allowed.
7. **No readiness inference.** Passing the self-containment gate proves only location independence of the installed payload; it does not validate legal substance or authorize publication, filing or method promotion.

## Risks / Trade-offs

- **Useful provenance is lost** → retain bibliographic identifiers, hashes, dates, counts and public URLs; pin the substantive JSON projections.
- **A user assumes an unavailable source is bundled** → state the availability boundary next to the provenance and direct quotation rule.
- **The scanner blocks a harmless negative example** → limit markers to repository-local coordinates and runtime-eligible files; negative fixtures remain source-only under `tests/`.
- **Source-only evidence becomes impossible to maintain** → skip only paths classified source-only by the shared versioned contract and keep source/repository security scans unchanged.
- **A future JSON edit hides a path with escaping** → decode JSON and normalize Unicode before marker matching.

## Migration Plan

1. Freeze live SHA, manifest, exact occurrences and semantic projections.
2. Record and strictly validate this OpenSpec change.
3. Add failing portable and root regressions for local coordinates, escaped JSON and semantic preservation.
4. Rewrite the seven runtime references and add the shared portable gate.
5. Regenerate the manifest and run focused/full tests, source strict, clean-room runtime strict, OpenSpec strict and independent review.
6. Commit on the isolated branch, merge to `main`, confirm live SHA, install and validate the exact global payload.
7. Archive the change, regenerate the manifest from the merge SHA and publish the final evidence commit.

Rollback is a normal revert of the atomic release. No user data or external source corpus is modified.
