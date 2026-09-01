## Context

`practice_claim` is already a filing-significant sentence role, while `ksrf_practice_analysis.py` already maintains a much stronger claim lifecycle: append-only claim revisions, content-bound requests and imported results, exact selected findings, human wording review, source and sibling-workspace trust anchors, and filing-stage refresh. The filing runtime does not consult that lifecycle. It currently proves only that a caller supplied a non-empty identifier and a support-status string.

The remedy and legal-holding changes established dependency-injected authorities, immutable receipts, manifest-time revalidation, and independently attested complete-line indexes. This change applies that trust boundary only to empirical judicial-practice statements and reuses the native practice-analysis contracts instead of inventing a parallel corpus.

## Goals

- Bind every present `practice_claim` sentence to exact current findings for the same native practice claim, constitutional claim, and selected issue option.
- Require exact reviewed wording and an independently stored maximum permitted inference.
- Recheck the current result, source/attachment trust anchors, and pre-filing refresh at every release decision.
- Detect fictional, cross-claim, stale, malformed, coerced, downgraded, deleted, substituted, or newly inserted practice lines.
- Preserve draft readability and every existing human legal and publication gate.

## Non-Goals

- Treating corpus frequency, model output, retrieval rank, or lower-court repetition as KSRF authority.
- Proving that an empirical pattern establishes unconstitutional application in the applicant's own case.
- Binding `court_reasoning`, `application_finding`, `fact`, `norm_text`, `adverse_authority`, or draft-only narrative in this change.
- Automatically approving an issue, merging, installing, signing, paying, transmitting, or filing.

## Decisions

### 1. A practice request is an exact-byte contract

For role `practice_claim`, the normalized sentence preserves constitutional `claim_id`, native `practice_claim_id`, `issue_option_id`, a strict non-empty unique list of `evidence_ids` interpreted as native `finding_id` values, and a non-empty `maximum_supported_inference`. The runtime hashes schema version, matter/draft/sentence/section identity, exact sentence text and its SHA, constitutional claim, practice claim and issue IDs, sorted finding IDs, and the inference ceiling into `practice_binding_sha256`. Raw strings, nulls, booleans, blanks, duplicates, ambiguous claim identities, and caller-supplied fingerprints are rejected. The current practice-analysis ledger claim ID and `PracticeClaimGate.claim_id` must both equal `practice_claim_id`; neither may be inferred from the distinct constitutional `claim_id`.

### 2. Legacy practice sentences remain drafts

A legacy practice sentence missing any binding field remains readable and serializes as `practice_binding_status=unbound`. It cannot satisfy release support. Other filing roles retain their current behavior.

### 3. The host revalidates native practice-analysis state

The injected `PracticeClaimEvidenceBindingAuthority` receives a deep copy of the canonical request and resolves current host-owned state. Its adapter MUST first resolve a host-owned matter/draft-to-case/workspace binding with an exact workspace revision and input-manifest fingerprint; caller paths are never authoritative. It then reopens that bound practice-analysis workspace, runs `validate_workspace(stage="filing")`, and returns a closed projection of the exact active practice claim, current ready binding, the content-bound native research request, imported v2 result identity, complete requested finding records, wording-review event, attachment/result/trust-anchor revisions, filing validation, and pre-filing refresh.

The local runtime snapshots each authority response exactly once into detached plain mappings before validation and receipt construction. It requires exact agreement among host workspace/case identity, private/public practice-claim identity, the distinct constitutional claim and selected issue projection, claim and source SHA values, the native request handoff, `request_sha256`, claim-set digest and canonical request/result claim bindings, result handoff, plan/evidence/fingerprint SHA values, finding claim sets, native finding/candidate wording, reviewed wording text/SHA, finding set, maximum permitted claim, material event identities and timestamps, refresh `ready_claim_set_sha256`, corpus cutoff, and the current filing verdict. Refresh time must not precede any bound native material event; filing generation and validation must follow refresh; authority checking must follow filing validation; and the refresh `as_of` day must equal both the recorded and checked day. The filing report must have `stage=filing`; every projected `state=ready` claim must contain semantically valid material identifiers, timestamps and wording ledger state; the exact target claim must be `state=ready`, `draft_blocked=false`, present in a real list-valued `allowed_claim_ids`, and have no claim-specific blockers; global integrity errors must be empty; and the required current refresh must have `valid=true` and bind the complete ready-claim set. A native `valid=false`, `stage_verdict=partial` report caused only by different isolated claims may still support this exact ready claim, but only when report/state ID lists agree and the error set exactly reconstructs every other blocked claim; a `valid=true` partial projection is inconsistent and fails. A multi-claim v2 result may contain findings belonging solely to other bound claims; exact-set validation applies to every finding whose `claim_ids` contains the target practice claim, so an extra target finding still fails. Missing, duplicate, extra-target, foreign-target, target-blocked, integrity-failed, malformed-container, response-mutation, or stale projections fail closed. An embedded `valid` or `ready` flag without these reconstructable bindings is not authority.

Chronology is evaluated over the whole closed projection: native request creation precedes its attachment and result, and refresh recording follows the latest bound material timestamp of every claim in the complete ready set, not only the target claim.

### 4. Issue selection and human review are separate exact approvals

The host resolution also contains the current selected issue fingerprint and exact `PracticeClaimGate` projection for `issue_option_id` and `practice_claim_id`, plus host-owned approval receipts for both canonical requests: `practice:<practice_claim_id>` and the separate issue `selection`. The runtime reconstructs both requests and fingerprints, requires substantive practice proof, exact statement/finding alignment, a current freshness state, reviewed adverse/counterexample status, `human_selection.state` in `principal|reserve`, and two current trusted approval identities with different receipt IDs. A practice-approved claim on an unselected or rejected issue remains blocked. Complaint fields and raw `human_decision` strings are not approval authority.

### 5. Exact wording and inference ceiling are binding

The release sentence bytes must equal the currently reviewed wording bytes. The wording review must refer to the exact requested findings and current result. `maximum_supported_inference` must equal the independently stored result, wording-review, and host-scope ceilings. A paraphrase, broader formulation, or result echo not covered by the review is blocked for a new review.

### 6. Completeness is independently attested

After individual resolution, the host resolves a complete practice-line index for the matter and draft from a pre-existing host draft registry, never from the caller's current request set. Each binding includes sentence ID, section, role, constitutional claim ID, practice claim ID, issue option ID, and practice-binding SHA. The runtime compares the exact set and index hash and requires every per-line receipt plus the index to carry one identical authority revision; all per-line receipts must also share one workspace revision and input-manifest fingerprint. Deletion, insertion, substitution, cross-snapshot replay, or role downgrade therefore cannot be hidden by dropping or racing the corresponding per-line receipt. Every ready manifest requires the current index even when `bindings=[]`.

### 7. Persisted manifests revalidate authority

Structured-complaint and filing-package contracts advance to `1.3`. A ready manifest stores all practice receipts and one complete-index receipt, requires `blockers=[]`, and includes them in the release-basis hash. Verification reconstructs every request from the persisted sentence map, calls current host authority again, and compares exact receipts and index. Approval and human signing/filing readiness repeat this verification. A blocked diagnostic manifest may carry blockers, empty receipts, and a null index.

### 8. Authority is dependency-injected and absent means blocked

Composer, pack build, manifest verification, approval, and workflow routing accept an injected practice authority. No process-global cache, caller-owned registry, or historical JSON snapshot is authoritative. Failure of the adapter blocks release readiness while preserving diagnostic draft artifacts.

## Risks and Mitigations

- **Duplicate domain models:** native practice-analysis records remain the source of truth; the new module validates closed projections and does not create a second corpus.
- **Caller-controlled readiness:** the host adapter must re-run filing validation and the local verifier checks complete cross-field hashes rather than trusting booleans.
- **Corpus drift and TOCTOU:** detached single-read authority snapshots, ordered refresh/material timestamps, one atomic receipt/index revision, source anchors, and current re-resolution are required on build, verification, approval, and final readiness.
- **Overclaim:** exact wording and the independently stored ceiling are both bound; human legal review remains mandatory.
- **Compatibility:** incomplete legacy practice lines remain drafts but cannot be released.

## Verification

- Focused RED/GREEN tests for fictional/coerced/cross-claim findings, stale result/source/attachment/refresh, wording and inference mismatch, missing issue approval, index mutation, and a positive multi-line case.
- Full complaint-cycle, cassation-skill, and root suites.
- Strict JSON Schema, skillset, and OpenSpec validation.
- Independent contract and code review with no unresolved P1/P2.
- Exact candidate manifest generation and feature-branch SHA verification.
