## Why

The current `SentenceEvidence.release_supported` check accepts a `practice_claim` sentence whenever the caller supplies any non-empty `evidence_ids` and a trusted-looking support status. A fictional finding, a result for another claim, a stale corpus or attachment, an expired pre-filing refresh, or a sentence never approved by the practice-analysis workflow can therefore enter a release manifest. A raw string is also coerced into one-character evidence identifiers.

## What Changes

- Treat `practice_claim.evidence_ids` as a strict unique sequence of exact practice-analysis `finding_id` values rather than caller labels.
- Preserve distinct constitutional `claim_id`, native `practice_claim_id`, exact `issue_option_id`, and `maximum_supported_inference` for every release-significant practice sentence and derive a deterministic `practice_binding_sha256` from the exact sentence and scope.
- Resolve every practice sentence at release time through a host authority that reopens the current practice-analysis workspace, runs filing-stage validation, and returns exact current claim, result, wording-review, finding, trust-anchor, and pre-filing-refresh projections.
- Require a host-attested issue-scope approval and a separate complete index of all `practice_claim` lines in the exact draft, including the authoritative empty set.
- Persist immutable practice receipts and the complete-index receipt in the filing package; re-resolve both before expert approval and before human signing/filing readiness.
- Keep legacy unbound practice sentences readable as working drafts, but block their release.
- Add adversarial and positive behavioral evals to `ksrf-cassation-judicial-meaning` and the complaint QA surface.
- **BREAKING**: `practice_claim` can no longer satisfy release support through arbitrary IDs plus caller-supplied `verified|human_approved`.

## Capabilities

### New Capabilities

- `ksrf-practice-claim-evidence-binding`: Claim-scoped, release-time proof that an empirical statement exactly matches the current reviewed practice-analysis result, its permitted inference, and its fresh official-corpus check.

### Modified Capabilities

None.

## Impact

- Runtime: complaint composition, practice-analysis current projection, release verification, approval, and workflow dependency injection.
- Contract: structured-complaint and filing-package schemas advance from version 1.2 to 1.3.
- Methodology and evaluation: `ksrf-cassation-judicial-meaning`, `ksrf-complaint-qa`, and complaint-cycle filing references/evals.
- Compatibility: legacy payloads still normalize for draft work; a release containing an unbound `practice_claim` is blocked.
- Publication remains candidate-only; no merge to `main` or global-skill installation is authorized.
