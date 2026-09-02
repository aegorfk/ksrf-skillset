## Why

The admissibility workflow already promises to revalidate current official authority and current issue bindings during `admissibility status`. Its existing revocation-oriented workflow tests replace `_resolve_current_source_authority` and `_validate_current_issue_bindings` with mocks. Those tests prove orchestration and route precedence, but they do not prove that a revocation written to the real trusted-approval ledger propagates through the native source-evidence repository or issue-gate evaluator, through persisted event reload, and into the status result. A regression at any of those seams could leave an earlier `GO_TO_KSRF` looking current after its supporting human approval has been revoked.

## What Changes

- Add one non-mocked end-to-end regression that creates current official `SourceEvidence` under a real source-identity approval, derives `GO_TO_KSRF`, revokes that exact approval in the native trusted-approval ledger, and proves that `admissibility status` returns `ABSTAIN_PENDING_RECORD` with a current official-authority blocker.
- Add one non-mocked end-to-end regression that persists a genuinely passing issue candidate and its real gate/selection approvals, derives `GO_TO_KSRF`, revokes the exact human issue-selection approval, and proves that `admissibility status` returns `ABSTAIN_PENDING_RECORD` with an issue-binding blocker.
- In both paths, capture the exact prior result-object bytes and prior workflow-event bytes before revocation, then prove that status appends a new event without modifying either earlier artifact.
- Exercise the existing `WorkflowRouter`, `SourceEvidenceRepository`, `TrustedApprovalLedger`, issue-gate evaluator, content-addressed store, and append-only ledger directly. Do not patch the two revalidation methods or substitute precomputed authority results.
- Keep the public CLI, schemas, runtime-verifier profiles, installation manifest, network boundary, route precedence, and human filing gates unchanged. If a RED test exposes a defect, limit any correction to the existing local status-revalidation path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-admissibility-routing`: real local approval revocations must propagate through status revalidation, downgrade stale GO recommendations, and preserve prior content-addressed and event bytes.

## Impact

- Tests: two deterministic, non-network end-to-end regressions in the complaint-cycle admissibility workflow suite.
- Runtime: no new route, command, validator mode, schema, service, or dependency; only a minimal correction to the existing revalidation path is in scope if the native RED test reveals one.
- Storage: verification covers the existing content-addressed result object and append-only workflow ledger; no storage format changes.
- Legal boundary: a revoked proof source blocks planning readiness, but no automated legal judgment, approval, transmission, signature, payment, or filing is introduced.
