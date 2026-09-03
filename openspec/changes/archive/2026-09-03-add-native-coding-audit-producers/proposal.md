## Why

The closed coding-reliability gate is now fail-closed, but users must still hand-build audit-specific candidate IDs, primary records, hashes, and review templates even though the ordinary workspace already contains the frozen plan, screening frame, approved coding, and source texts. That manual transcription is slow and creates avoidable identity and digest errors at the exact boundary meant to improve reliability.

## What Changes

- Add an installed `quality coding-audit-prepare` producer that reads one existing workspace and creates a new immutable audit-input bundle in an absent output directory.
- Derive stable candidate IDs from the frozen plan plus canonical chain/document identity; project ordinary approved coding into the exact audit primary contract and recheck it against the stored full text.
- Produce the closed screening frame, exact primary decisions, frozen audit plan, a non-authoritative secondary-review queue, blank secondary-coding templates, and a content manifest in one staged directory publication.
- Fail before publishing the bundle when the plan is not valid and frozen, source/coding identity is missing or ambiguous, primary coverage is not exact, quoted text is not present, or the destination already exists.
- Keep independent secondary coding and adjudication human-authored: generated templates remain visibly pending and cannot satisfy `coding-reliability` without separate completion and wrapping.
- Correct the audit-plan annotation to match the existing deterministic sampling rule: the general and exclusion samples may overlap and configured sizes are maxima when the frame is smaller.
- Replace the installed statement that no native producer exists with an executable Russian producer-to-consumer workflow and preserve the old exact manual inputs as compatible expert inputs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-practice-quality-exit-status`: add a first-party, provenance-bound producer for the frozen coding-audit inputs and state the exact sampling semantics.
- `ksrf-user-facing-cli`: expose the producer and its safety/human-review boundaries in installed Russian help.

## Impact

- Quality builders and validation in `practice_quality.py` and `analysis.py`.
- CLI routing, staged directory output, and workspace source verification in `cli.py`.
- Audit definitions in `practice-quality.v1.json` and installed reference guidance.
- Source/install parity, schema, atomic-output, malformed-input, and no-fabricated-approval tests.
- No network access, legal conclusion, automatic secondary coding, adjudication, approval, filing, or overwrite is introduced.
