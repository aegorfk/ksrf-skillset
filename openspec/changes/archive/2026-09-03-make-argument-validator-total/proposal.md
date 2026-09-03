## Why

`validate_argument_research.py` accepts a JSON file and is supposed to report
contract violations, but several ordinary JSON type mismatches escape as raw
Python exceptions. For example, `null` in `supporting_finding_ids`, an object
inside a reference array, or an object in an enum field raises `TypeError`.
The user gets a traceback, later violations are never reported, and the same
artifact cannot be safely checked in an automated workflow.

## What Changes

- Make validation total for every value that can be produced by `json.loads`:
  semantic mistakes become collected validation errors, not exceptions.
- Validate reference-array containers and entries before set operations;
  malformed entries never participate in cross-reference checks.
- Validate enum and principal-reference types before membership checks.
- Escape JSON strings safely when an identifier is reflected in a diagnostic,
  so unusual Unicode or control characters cannot break output encoding.
- Preserve deterministic error order, the existing valid-artifact success
  output, and the existing read/JSON-syntax failure channel; normalize a
  non-object root into the same `ERROR:` semantic-error channel as other
  decoded contract violations.
- Add source and clean-installed subprocess regressions plus a broad
  JSON-value matrix for every formerly unsafe field family.
- Explain the failure contract in the installed artifact reference.

## Capabilities

### New Capabilities

- `ksrf-argument-research-validator`: total, deterministic validation of the
  installed adaptive argument-research JSON artifact.

### Modified Capabilities

- None.

## Impact

- Runtime: `skills/ksrf-explore-arguments/scripts/validate_argument_research.py`.
- User documentation:
  `skills/ksrf-explore-arguments/references/artifact-contracts.md`.
- QA: new root tests run the source and a clean installed payload.
- No network, model, filing, publication, or legal-readiness authority is added.
