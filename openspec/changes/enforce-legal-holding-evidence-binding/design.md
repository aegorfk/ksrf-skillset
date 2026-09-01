## Context

`legal_holding` is already a filing-significant sentence role, but its runtime support check only proves that an arbitrary identifier was supplied. The previous remedy-binding change established a host-authority boundary, complete-line index, immutable receipts, and manifest-time revalidation for the requested remedy. Legal propositions need the same trust boundary without treating comparative, doctrinal, applicant, or search material as Russian filing authority.

## Goals

- Bind every present `legal_holding` sentence to exact current official evidence from the same claim.
- Preserve the source's maximum supported inference and reject broader sentence claims.
- Detect fictional, foreign-claim, stale, malformed, duplicate, locator-mismatched, downgraded, deleted, or newly inserted holding lines.
- Preserve existing draft readability and all human release gates.

## Non-Goals

- Proving that a legal conclusion is normatively correct without human legal review.
- Promoting ECHR, comparative, doctrinal, applicant, separate-opinion, or discovery material into Russian filing authority.
- Automatically merging, installing, signing, paying, or filing.
- Retrofitting exact bindings for every other sentence role in this change.

## Decisions

### 1. A legal-holding request is a deterministic exact-byte contract

For role `legal_holding`, the normalized sentence preserves `claim_id`, a strict unique list of `evidence_ids`, and a non-empty `maximum_supported_inference`. The runtime hashes schema version, matter/draft/sentence identity, exact sentence text and its SHA, claim ID, sorted evidence IDs, and inference ceiling into `holding_binding_sha256`. Caller-supplied fingerprints are never authority.

### 2. Legacy holdings remain drafts, not release evidence

Legacy sentences missing one or more binding fields still normalize and serialize as `holding_binding_status=unbound`. Any release candidate containing such a sentence fails closed. Other sentence roles retain their existing behavior.

### 3. The host resolves native SourceEvidence and a separate claim scope

The injected `HoldingEvidenceBindingAuthority` resolves a deep copy of the canonical request. Each requested evidence ID must resolve exactly once to the full native `SourceEvidence v1` object from `source-evidence.v1.schema.json`, together with the current result of `SourceEvidenceRepository.current_filing_authority`. The runtime pins schema `1.0.0`, evidence and verification IDs, `raw_object.sha256`, `verified_official_locator`, exact `filing_ready=true`, and an empty blocker set. It separately requires a host-owned claim-scope record containing the same evidence ID, native `source_id`, claim ID, exact `authority_role=ksrf_legal_holding`, official locator, pinpoint, raw SHA, verification revision, `current_evidence_id`, `freshness_state=current`, scope revision/check time, and maximum inference. Thus a valid official act from the Supreme Court, a lower-court card, application evidence, or a comparative source cannot be relabeled as a KSRF holding merely because SourceEvidence is filing-ready. This separation also avoids inventing claim or pinpoint fields inside immutable SourceEvidence.

The claim-scope layer must also prove that the requested evidence is the latest record for its source/origin. `current_filing_authority` alone is insufficient because an older superseded record may still recompute as individually valid. Raw non-string IDs, nulls, coercible booleans, request mutation, extra or missing requested evidence, mismatched native/scope projections, and superseded records are blockers.

### 4. The inference ceiling is host-attested and locally reconstructed

Every host-owned claim-scope record and the scope receipt must carry the independently stored exact `maximum_supported_inference`; an echo copied only from the current request is not authority. The scope receipt contains the exact requested evidence set, native SourceEvidence fingerprints, claim-scope fingerprints, an authority revision, check time, trusted approval ID, and the complete expected approval request. The local runtime recomputes the approval request fingerprint and rejects an embedded `passed` flag or a receipt with altered scope.

### 5. Completeness is independently attested

After resolving individual lines, the host resolves a complete holding index for the matter and draft from a pre-existing host draft registry, not from the caller's current request set. The index contains every `legal_holding` line with sentence ID, section, role, and binding SHA. The runtime compares the exact set and hash, so deletion, insertion, role downgrade, or line substitution cannot be made valid by deleting the matching per-line receipt. A ready manifest always carries a current index receipt, including the canonical empty `bindings=[]` case.

### 6. Persisted manifests revalidate authority

Structured-complaint and filing-package contracts advance to `1.2`. A filing manifest stores per-line holding receipts and one complete-index receipt. A blocked diagnostic manifest may use empty receipts and a null index. Every ready status requires a current host index even when `bindings=[]`; when any holding exists, every line must be bound and every exact per-line receipt must also be present. Manifest verification reconstructs requests from the sentence map, calls current host authority again, compares exact receipts/index, and includes these projections in the release-basis hash.

### 7. Authority is dependency-injected and absent means blocked

Composer, release build, manifest verification, approval, and workflow routing accept an injected holding authority. No process-global registry or caller-owned cache is authoritative. A missing or failing adapter blocks only release readiness and leaves draft artifacts diagnostic.

## Risks and Mitigations

- **Contract growth:** keep this change limited to `legal_holding`; use separate future changes for facts, practice claims, and adverse authority.
- **Host drift:** persist native SourceEvidence plus claim-scope projections, prove latest-record identity, and re-resolve at every release verification.
- **Overclaim hidden in prose:** bind exact sentence bytes and the separately approved inference ceiling; human legal approval remains mandatory.
- **Authority-role misuse:** require the host scope role `ksrf_legal_holding` bound to the native `source_id`; VSRF/lower-court/application/comparative material stays in its proper lane even when its SourceEvidence is official and filing-ready.
- **Compatibility:** unbound legacy holdings remain readable but cannot be released.

## Verification

- Focused RED/GREEN unit tests for fictional/cross-claim/stale/locator/inference/index/mutation failures and a positive multi-line case.
- Full complaint-cycle and root test suites.
- Strict JSON Schema, skillset, and OpenSpec validation.
- Independent contract and code review with no unresolved P1/P2.
- Exact candidate manifest generation and feature-branch SHA verification.
