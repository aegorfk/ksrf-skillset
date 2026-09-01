## Why

The current `SentenceEvidence.release_supported` check accepts a `legal_holding` sentence whenever it carries any non-empty `evidence_id` and a trusted-looking support status. A fictional ID, evidence belonging to another claim, a stale source revision, or an official act without the cited pinpoint can therefore pass the generic sentence gate and enter a release manifest.

## What Changes

- Preserve a claim-scoped `maximum_supported_inference` for every release-significant `legal_holding` sentence.
- Require exact, non-coerced evidence identifiers and a deterministic holding-binding fingerprint.
- Resolve each holding at release time through a host authority that returns the full native `SourceEvidence v1`, its recomputed `current_filing_authority` result, and a separate claim-scope record with exact `source_id`, role `ksrf_legal_holding`, official locator, pinpoint, raw SHA, verification revision, latest-record identity, and scope ceiling.
- Require a host-attested scope receipt whose request and source fingerprints are locally reconstructed, plus an independent complete index of all legal-holding lines in the draft; a ready manifest requires this index even when its authoritative binding set is empty.
- Revalidate the exact receipts and complete index from persisted manifests before expert approval and again before human signing/filing readiness.
- Keep legacy unbound holdings readable as working drafts, but fail closed whenever they are present in a release candidate.
- Add adversarial and positive evals to `ksrf-rights-argument-builder`.
- **BREAKING**: a `legal_holding` can no longer satisfy release support through caller-supplied IDs and `verified|human_approved` alone.

## Capabilities

### New Capabilities

- `ksrf-legal-holding-evidence-binding`: Claim-scoped, release-time proof that each legal proposition is no broader than current official source material and its exact pinpoint.

### Modified Capabilities

None.

## Impact

- Runtime: complaint composition, release verification, and workflow dependency injection in `skills/ksrf-complaint-cycle/lib/ksrf/filing/`.
- Contract: structured-complaint and filing-package schemas advance to version 1.2.
- Methodology and evaluation: `skills/ksrf-rights-argument-builder` instructions, workflow reference, and evals.
- Compatibility: legacy payloads still normalize for draft work; a release containing an unbound `legal_holding` is blocked.
- Publication remains candidate-only; this change does not authorize installation into global skills or merge to `main`.
