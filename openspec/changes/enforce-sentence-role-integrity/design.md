## Context

The complaint composer recognizes eight filing-significant roles but validates no closed role vocabulary. `filing_significant` is a membership test and `release_supported` returns true for every value outside that set. Both structured-complaint and filing-package schemas accept arbitrary strings. Specialized complete indexes protect `requested_remedy`, `legal_holding`, and `practice_claim`, but there is no complete draft-level role registry for facts, court reasoning, norm text, application findings, adverse authority, or legitimate narrative.

## Goals

- Fail closed for every explicit unknown role without destroying legacy draft content.
- Distinguish a deliberate, host-reviewed narrative line from a downgraded filing-significant line.
- Detect deletion, insertion, role mutation, sentence reordering (including reordering sentence-bearing sections), section movement, and exact-text substitution across the whole sentence inventory.
- Revalidate current host authority at pack build, manifest verification, approval, and final readiness.
- Preserve all existing legal, publication, signature, payment, transmission, and filing gates.

## Non-Goals

- Inferring semantic roles from prose with an LLM or classifier.
- Automatically rewriting aliases, correcting typos, deleting unknown-role lines, or promoting narrative to a legal role.
- Replacing the deeper evidence authorities for remedy, legal holdings, or judicial-practice claims.
- Attesting the relative position of empty section headings; those contain no sentence-role binding and remain protected by rendered-artifact hashes, release-basis hashing, and visual/semantic QA.
- Merging, installing, signing, paying, transmitting, or filing.

## Decisions

### 1. Release roles use a closed canonical vocabulary

The canonical set is `narrative`, `fact`, `court_reasoning`, `norm_text`, `legal_holding`, `application_finding`, `practice_claim`, `adverse_authority`, and `requested_remedy`. Outside the requested-remedy section, only a missing role field and a legacy raw sentence keep the current explicit `narrative` default. The requested-remedy invariant instead coerces absent/raw and explicitly canonical roles to `requested_remedy`; an explicit unknown string is preserved and blocked rather than hidden by that coercion. A present role must be a non-blank string; it is preserved byte-for-byte without trimming or alias conversion. Any exact string outside the set remains visible and produces a separate exact machine blocker `sentence_role_unknown:<sentence_id>:<role>` on every release-support check. A human-readable aggregate error does not substitute for that blocker, and runtime validation correlates the exact sentence/role marker.

### 2. Draft readability and release authority remain separate

Structured complaint schema `1.3` remains open enough to read and migrate a legacy unknown role, including one in the requested-remedy section. That repair path preserves its diagnostic `application_record_ids` by section without treating the line as a bound canonical remedy. A blocked filing manifest may also retain that role as diagnostic evidence only when the exact corresponding machine blocker is present. Ready manifest statuses conditionally require canonical roles only. JSON Schema anchors the machine-blocker shape; runtime performs the cross-field sentence/role equality that portable JSON Schema cannot express. This preserves recoverability without treating compatibility as release authority.

### 3. The host attests the complete sentence-role inventory

The injected `SentenceRoleIndexAuthority` receives only a canonical matter/draft lookup request and resolves a pre-existing host draft registry. It returns a detached projection containing every current sentence exactly once with a continuous global 1-based `ordinal` in actual draft order, strict sentence ID, section code, exact text SHA-256, and canonical role, plus exact matter/draft identity, authority revision, RFC3339 snapshot check time, and a deterministic index SHA-256. The host must return the same `checked_at` for an unchanged authority revision; it is snapshot metadata, not a fresh per-query wall-clock value.

The runtime independently derives the complete expected projection from the normalized complaint, assigns the same global ordinal across section boundaries, canonicalizes by ordinal, and compares exact ordered bindings and index hashes. It rejects malformed containers, duplicate or non-contiguous ordinals, unknown or duplicate host roles/IDs, missing or extra lines, reordered sentences or sentence-bearing sections, role downgrade, section movement, text substitution, wrong matter/draft, dishonest hash, adapter request mutation, and response mutation. Empty section headings do not contribute bindings; an empty authoritative set is valid only when the complaint itself has no sentences.

### 4. Receipt freshness is checked at every release decision

Render build and pack build persist the immutable sentence-role index receipt in their respective operation records. `render/status` rebuilds the stored complaint input, re-resolves every current support authority, and exact-compares the current role receipt; it never republishes cached ready state after a host change or without the stored input/receipt. Manifest verification reconstructs the expected projection from `sentence_evidence_map`, resolves current host authority again, and requires exact equality with the persisted receipt. Expert approval and human signing/filing readiness use the same verifier, so a changed host draft or authority revision stales the prior render status, release basis, and approval.

### 5. The complete role index complements specialized evidence indexes

The new index proves only identity, completeness, exact text, section, and role. It does not prove the truth or sufficiency of evidence. Existing remedy, holding, and practice authorities remain mandatory and continue to validate their richer claim/evidence contracts. A canonical role therefore does not become supported merely by appearing in the complete index.

### 6. Filing-package schema advances independently

The filing-package manifest advances to `1.4` because it gains a `sentence_role_index_receipt` and new ready-state conditions. Structured complaint stays at `1.3` because its draft representation does not gain authority and must remain able to preserve unknown legacy roles. Release-basis hashing includes the new receipt.

## Risks and Mitigations

- **Host index bootstrapping:** the authority must read a pre-existing host draft registry; it must never manufacture the index from the caller's current payload. Absence blocks readiness.
- **Compatibility loss:** unknown lines remain visible in drafts and blocked diagnostic manifests; only readiness is denied.
- **False confidence:** the index is explicitly an integrity receipt, not evidence or legal approval.
- **TOCTOU:** current authority is re-resolved during build, verification, approval, and final readiness; the receipt is content-bound and included in the release basis.
- **Duplicate gates:** specialized indexes remain because they bind richer evidence state; the complete role index covers the cross-role gap only.

## Verification

- RED/GREEN tests for unknown role, missing role, explicit narrative, padded alias/typo, blank/non-string values, downgrade, deletion, insertion, sentence and sentence-bearing-section reordering, text/section mutation, malformed and stale host indexes, exact blocked-diagnostic correlation, Mapping protocol compatibility, and a positive complete index.
- Focused and full complaint-cycle suites plus root tests.
- Strict JSON Schema, skillset, and OpenSpec validation.
- Independent contract/code review with no unresolved P1/P2.
- Exact candidate manifest generation and feature-branch SHA verification.
