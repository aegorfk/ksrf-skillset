## Why

The current complaint composer treats an `application_finding` sentence as release-supported whenever the caller supplies any non-empty evidence identifier and a trusted-looking support status. It also silently drops `application_record_ids` outside the requested-remedy section. A fictional identifier, a record from another claim, a stale chain, or an unreviewed inference can therefore enter a ready release manifest even though application of the challenged norm in the applicant's own case is a core admissibility gate.

## What Changes

- Preserve exact claim, norm-passport, application-record, evidence, and maximum-inference fields for every `application_finding` sentence.
- Derive a deterministic application-finding binding from the exact sentence bytes and identifiers; never trust a caller-supplied fingerprint.
- Resolve each finding through an injected host authority that returns current native `ApplicationEvidenceRecord` objects, the full chain assessment, current norm-version and application-gate receipts, and an independently stored reviewed wording/inference scope.
- Require a host-attested complete index of every application-finding line, including the canonical empty set.
- Persist per-line receipts and the complete index in the filing manifest, include them in the release basis, and re-resolve them during render/status, build, verify, expert approval, and final signing readiness.
- Keep legacy incomplete findings readable as `unbound` working drafts, but fail closed for release.
- Add exact sentence-specific repair blockers and adversarial/positive evals.
- **BREAKING**: caller-supplied `verified|human_approved`, arbitrary evidence IDs, or the general sentence-role receipt can no longer establish release support for an `application_finding`.

## Capabilities

### New Capabilities

- `ksrf-application-finding-evidence-binding`: Exact current proof that a filing sentence about application of a norm is no broader than the reviewed record and surviving procedural chain in the same claim.

### Modified Capabilities

None.

## Impact

- Runtime: complaint composition, release verification, and workflow dependency injection in `skills/ksrf-complaint-cycle/lib/ksrf/filing/`.
- Contract: structured complaint advances to `1.4`; filing-package manifest advances to `1.5` with application-finding receipts and index.
- Methodology and evaluation: complaint-cycle, complaint-QA, release reference, and behavioral evals.
- Compatibility: legacy payloads remain readable for draft repair; any unbound application finding blocks release.
- Publication remains candidate-only; this change does not authorize merge to `main` or global installation.
