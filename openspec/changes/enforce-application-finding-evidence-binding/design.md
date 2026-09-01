## Context

`application_finding` is a filing-significant sentence role used to state that the challenged norm was applied in the applicant's case. The application-evidence subsystem already models exact records, full-act locators, application classification, chain survival, norm-version prerequisites, preservation, and trusted human review. The filing runtime currently does not consult those records for application-finding sentences: it accepts arbitrary caller IDs and status strings, while the new sentence-role index intentionally proves only identity and role completeness.

The remedy, holding, and practice changes established dependency-injected authorities, immutable receipts, complete host indexes, and manifest-time revalidation. This change applies the same trust boundary to application findings while reusing the existing `ApplicationEvidenceRecord` and application-review contracts.

## Goals

- Bind every present `application_finding` sentence to exact current records from the same claim and norm-version passport.
- Require a surviving application chain, full-act evidence locators, current trusted application approvals, and exact reviewed wording/inference scope.
- Detect fictional, foreign-claim, stale, malformed, coerced, downgraded, deleted, substituted, or newly inserted application-finding lines.
- Preserve draft readability and every existing human legal, publication, signature, payment, and filing gate.

## Non-Goals

- Automatically infer application of a norm from an outcome, mention, affirmance, or similarity.
- Rewrite the sentence, select records, or create legal approval.
- Treat the general sentence-role index as evidence sufficiency.
- Merge, install, sign, pay, transmit, or file.

## Decisions

### 1. An application-finding request is an exact-byte contract

For role `application_finding`, the normalized sentence preserves non-empty `claim_id`, `norm_passport_id`, strict unique `application_record_ids`, strict unique `evidence_ids`, and non-empty `maximum_supported_inference`. The runtime hashes schema version, matter/draft/sentence/section identity, exact sentence text and SHA-256, claim and passport identity, sorted record/evidence sets, and inference ceiling into `application_binding_sha256`. Nulls, booleans, non-string values, blanks, duplicates, and caller fingerprints are rejected rather than coerced.

### 2. Legacy findings remain repairable drafts

A legacy application finding missing any binding field remains readable and serializes as `application_binding_status=unbound`. Its existing record and evidence identifiers are preserved for repair. It cannot satisfy release support. Other sentence roles retain their current behavior.

### 3. The host revalidates native application state

The injected `ApplicationFindingEvidenceBindingAuthority` receives a deep copy of the canonical request and resolves current host-owned state. The closed response distinguishes the caller-selected positive `application_record_ids` from a separately resolved, host-attested complete `chain_records` inventory for the same claim/norm chain. The inventory carries its own immutable chain revision, checked time, ordered record IDs, record fingerprints, and chain fingerprint; it is resolved from the current case registry rather than constructed from the selected request. This prevents a caller from omitting a later superseding or adverse act.

The response also contains the current `NormVersionPassport`, its trusted gate receipt, and one current application-gate receipt for each selected positive record. The runtime rejects duplicate or non-canonical chain stage ordering, reconstructs all record fingerprints and classifications, and calls `assess_application_chain()` over the complete host chain. Selected records must be a subset of the positive supporting records, have status `explicitly_applied|implicitly_applied_proven`, have `outcome_causation=determinative|contributory`, and pass the current preservation and norm-version prerequisites; a final incorporation-only record may belong to the complete chain without requiring an impossible positive-record approval of its own. Each selected record's approval request must nevertheless bind the same complete chain fingerprints, norm-version and preservation prerequisites, and a pre-existing trusted human approval.

Requested evidence must equal the exact complete positive proof set: for direct application, non-contradicted full-act court spans whose roles are `express_norm_use|operative_rule` plus the required non-contradicted full-act court/disposition `outcome_link`; for implicit application, only the non-contradicted evidence IDs that satisfy their own named premise's exact role/speaker rule, including court/disposition `outcome_link|counterfactual_analysis` for the counterfactual premise and human-confirmed reviewer `alternative_ground_analysis`; and any non-contradicted full-act court/disposition incorporation evidence carried by the surviving chain. Every requested ID must occur exactly once, belong to the same record act/stage, claim, and norm, and have the required full-act locator and speaker/role. Arbitrary spans returned by the broad compatibility classification are not positive proof. Every `incorporated_record_id` must resolve uniquely to an earlier record in the complete chain. The chain must be `survived|incorporated|concurrent`; a bare affirmance, omitted or unresolved later/earlier record, contradicted incorporation span, duplicate/non-canonical stage order, superseded basis, unclear application, or stale/mutated record fails closed. An embedded `passed`, caller status, or ordinary reviewer name is not authority.

### 4. Exact wording and inference scope are independently reviewed

The host response includes a pre-existing application-finding scope record for the same matter, draft, sentence, section, claim, passport, selected record/evidence sets, and complete host chain. Its canonical content fingerprint binds exact UTF-8 `reviewed_statement` bytes and SHA-256, independently stored `maximum_supported_inference`, passport fingerprint/revision, complete-chain fingerprint/revision/check time, scope revision/check time, and the selected sets. The chain inventory revision/check time are independent from the top-level draft-index authority revision, so an unrelated registry revision does not require a new legal scope approval while actual chain drift does. A trusted scope approval carries a canonical request that the local runtime reconstructs over all those fields. The release sentence is parsed without whitespace normalization and must byte-equal the reviewed statement; its inference ceiling must equal the independently stored ceiling. Echoing the current request without a current scope record and approval fails.

### 5. Completeness is independently attested

After resolving individual lines, the host resolves a complete application-finding index from a pre-existing draft registry, never from the caller manifest. Each binding contains sentence ID, section, role, claim ID, norm-passport ID, and `application_binding_sha256`. The runtime compares the exact set and hash and requires the same top-level host authority revision across the index and every per-line resolution receipt. Nested norm, preservation, application, and scope approvals retain their own immutable approval/revision identities and are not forced to share the index revision. Deletion, insertion, substitution, role downgrade, and cross-snapshot replay therefore fail. Every ready manifest requires the current index, including authoritative `bindings=[]` when no application finding exists.

### 6. Persisted manifests revalidate authority

Structured-complaint schema `1.4` preserves the new binding fields and status. Filing-package schema `1.5` stores per-line application receipts plus one complete index and includes them in the release-basis hash. A blocked diagnostic manifest may carry empty receipts and a null index. Every ready status requires a current index; when findings exist, every line must be bound with its exact current receipt. Render/status, pack build, manifest verification, expert approval, and human signing readiness re-resolve current authority and compare exact receipts/index.

### 7. Authority is dependency-injected and absent means blocked

Composer, release, approval, and workflow paths accept the injected application-finding authority. No caller-owned cache, manifest projection, process-global registry, or historical JSON is authoritative. A missing or failing adapter blocks release while preserving diagnostic draft artifacts.

## Risks and Mitigations

- **Duplicate application logic:** native `ApplicationEvidenceRecord`, chain assessment, and approval-request builders remain the source of truth; the new module validates their closed projections instead of creating a second admissibility model.
- **Overclaim hidden in prose:** exact reviewed wording and independently stored inference ceiling are both bound.
- **Chain drift and TOCTOU:** full record fingerprints, chain fingerprints, common authority revision, and current re-resolution are mandatory at every release decision.
- **False confidence:** passing this gate proves only technical evidence binding; human legal review remains mandatory.
- **Compatibility:** incomplete legacy findings stay visible but cannot be released.

## Verification

- Focused RED/GREEN tests for dropped identifiers, fictional/coerced/cross-claim evidence, incomplete locators, unclear/superseded chains, stale approvals, wording/inference mismatch, request/response mutation, missing authority, index deletion/insertion/downgrade, and a positive multi-line case.
- Full complaint-cycle, cassation-skill, and root suites.
- Strict JSON Schema, skillset, and OpenSpec validation.
- Independent contract and code review with no unresolved P1/P2.
- Exact candidate manifest generation and remote feature-branch SHA verification.
