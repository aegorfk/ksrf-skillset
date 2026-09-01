## Why

The structured-complaint release gate currently treats a `requested_remedy` sentence as supported when it has any non-empty evidence ID and a trusted-looking status. During normalization it drops the sentence claim binding and the upstream issue, norm-version, and application-record snapshots, so evidence from `CLAIM-A` can release a remedy belonging to `CLAIM-B`.

## What Changes

- Preserve claim-scoped remedy bindings in the structured complaint and its `SentenceEvidenceMap`.
- Require each release-significant `requested_remedy` sentence to bind to one exact selected issue option, one norm-version passport, and canonical application records from the same claim and norm edition.
- Re-evaluate the supplied upstream snapshots at the release-support entrypoint; caller-supplied IDs or embedded `passed` flags are not authority.
- Reject missing, malformed, duplicate, unknown, or cross-claim references with sentence-specific blockers.
- Keep legacy unbound payloads readable as working drafts, but make them fail closed at release support.
- Add adversarial and positive multi-line fixtures to the `ksrf-complaint-facts-demands` contract.
- **BREAKING**: an unbound legacy `requested_remedy` sentence can no longer satisfy `require_release_support()` merely through `evidence_ids` and `support_status`.

## Capabilities

### New Capabilities

- `ksrf-remedy-evidence-binding`: Claim-scoped, release-time validation of requested-remedy sentences against exact issue, norm-version, application, evidence, and trusted-approval artifacts.

### Modified Capabilities

None.

## Impact

- Runtime: `skills/ksrf-complaint-cycle/lib/ksrf/filing/composer.py` and existing filing contract helpers.
- Contract: `skills/ksrf-complaint-cycle/schemas/ksrf_filing/structured-complaint.schema.json`.
- Methodology and evaluation: `skills/ksrf-complaint-facts-demands/SKILL.md`, its workflow reference, and behavioral evals.
- Compatibility: legacy complaint payloads still normalize for draft work, but release validation requires the new exact bindings.
- Publication remains candidate-only; this change does not authorize installation into global skills or merge to `main`.
