## Context

`SentenceEvidence.release_supported` currently decides support from only a non-empty `evidence_ids` tuple and a status string. `build_structured_complaint` discards claim, selected-issue, passport, and application-record identity at sentence scope. The same weak check is used by both render and release paths, so a cross-claim evidence carryover is deterministic and filing-significant.

The skillset already has immutable `IssueCandidate` and `ApplicationEvidenceRecord` contracts, content fingerprints, a computed `NormVersionPassport`, trusted approval gates, and source-evidence resolvers. This change must reuse those authorities rather than treating a new caller-declared `passed` field as proof.

## Goals / Non-Goals

**Goals:**

- Keep the exact claim/issue/passport/application references for every `requested_remedy` sentence.
- Re-resolve exact upstream artifacts at release support and validate their claim, norm, edition, evidence, locator, fingerprint, and gate-receipt relationships.
- Fail closed when the host authority is absent or any reference is incomplete, malformed, duplicate, unknown, stale, or cross-claim.
- Support independent principal and reserve remedy lines.
- Keep old unbound payloads usable for draft editing without letting them pass a release gate.

**Non-Goals:**

- Introduce a second demand ontology or a caller-controlled `demand_id`; the stable `sentence_id` remains the identity of the requested-remedy line.
- Change the issue-generation, norm-version, application-admissibility, authority-research, or formal-filing gates.
- Infer a multi-line binding from the legacy singular top-level `issue_option_id`.
- Merge to `main`, install global skills, or authorize filing.

## Decisions

### 1. Sentence-scoped binding references are explicit and content-bound

Each sentence in the `requested_remedy` section is normalized to the `requested_remedy` role and carries a strict globally unique sentence ID. A bound sentence carries non-empty `claim_id`, `issue_option_id`, `norm_passport_id`, and a canonical unique `application_record_ids` list. The structured complaint also carries plural `issue_option_ids`; the legacy singular field remains a diagnostic alias only. A deterministic SHA-256 binds the complaint, sentence text, evidence IDs, and all binding references and is emitted in `SentenceEvidenceMap`. Legacy lines emit `relief_binding_status=unbound`; bound lines emit `bound` from normalized fields rather than a caller flag.

This is preferred to a new `demand_id`: the existing stable sentence ID already provides deterministic line identity, while a second identifier would create an avoidable reconciliation problem.

### 2. Release validation uses a host-attested resolver, not payload gate flags

`require_release_support` receives an optional `ReliefEvidenceBindingAuthority`. For each remedy line it sends the exact binding request and fingerprint. The authority must resolve the exact `IssueCandidate`, `NormVersionPassport`, `ApplicationEvidenceRecord` snapshots, same-claim source-evidence entries, and content-bound receipts produced by the existing trusted gates.

Absence of the authority blocks release. The complaint payload cannot self-assert that a binding passed. Direct release and workflow entrypoints accept the authority through dependency injection; default CLI behavior remains fail-closed.

Alternative considered: embed a `passed=true` receipt in the complaint. Rejected because the caller could manufacture or replay it without current source and approval checks.

The authority also exposes a separate draft-registry lookup, `resolve_relief_evidence_binding_index({schema_version, matter_id, draft_id})`. It returns the complete current, canonical set of requested-remedy entries (`sentence_id`, `section_code`, `role`, and `relief_binding_sha256`) plus an authority revision and timestamp. This set is not derived from the mutable complaint or manifest: release support and later manifest verification compare their projections with the host registry. Removing one of several remedy lines together with its receipt therefore remains detectable even after the caller recomputes the release basis.

### 3. Composer revalidates the resolved graph locally

The composer parses resolved issue and application snapshots through the existing immutable contracts and recomputes their content fingerprints. It validates:

- exact issue/passport/application IDs and exact binding SHA;
- same `claim_id`, `norm_id`, and `norm_version_id` across issue, passport edition, and every application record;
- principal/reserve human selection and content-bound trusted gate receipts;
- exact equality of the full approval requests recomputed by `issue_approval_requests`, `norm_version_review_approval_request`, `application_review_approval_request`, and `preservation_rule_review_approval_request`, including the complete required issue approval-key set;
- exact application-record set with no missing or duplicate record;
- each issue application-evidence ID and sentence evidence ID is present in a same-claim resolved record or same-claim source-evidence receipt with a usable locator;
- every receipt fingerprint matches the resolved artifact and carries the required trusted approval reference.
- every host-resolved graph identifier, stage, and locator is already a canonical string before the existing deserializers run; issue/passport/application schema versions are pinned to `1.0.0`; adapter-side coercion, whitespace normalization, version drift, or mutation of the lookup request is a blocker;
- every requested same-claim source-evidence entry is projected into a full receipt containing its claim/norm/edition identity, status, content SHA-256, verification revision, verifier, checked time, locator, and deterministic content fingerprint; unused resolver extras are not part of the line receipt.
- source and index checked times are validated explicitly as canonical timezone-bearing RFC3339 values rather than relying on optional JSON Schema format checking.

This local structural check prevents an authority adapter from accidentally returning a valid artifact from the wrong claim, old edition, or stale approval basis. A merely non-empty fingerprint or approval ID is never accepted as a substitute for the exact helper-derived request. Existing upstream gate functions remain the source of substantive pass/fail authority.

### 4. Version 1.1 reads legacy drafts but never promotes them

The emitted structured-complaint schema becomes `1.1`. Missing binding fields do not prevent draft normalization: the serialized line is explicitly `unbound`, remains schema-valid, and `require_release_support` names and blocks it. A line claiming `bound` without the complete fields is schema-invalid. New malformed or duplicate binding or sentence identifiers are rejected during normalization rather than silently coerced or deduplicated.

### 5. One gate is shared by render and release

Both renderer preparation and release-pack construction continue to call the same `require_release_support` function. The authority dependency is threaded through those entrypoints so a positive, fully resolved fixture can pass without creating a parallel release check.

The filing-package manifest schema becomes `1.1` and always carries the plural issue/passport projections, sentence evidence map, relief-receipt array, and nullable authoritative index receipt. A `blocked` manifest may keep empty receipts, a null index, and explicit `unbound` diagnostic lines; either ready status requires at least one fully `bound` remedy, receipt schema `1.1.0`, and current non-null index receipt. Manifest revalidation repeats strict noncoercing sentence/evidence/application identifier validation before authority resolution; omission, duplication, role/status downgrade, stale source content, or malformed IDs remain blockers even if a caller recomputes manifest hashes.

## Risks / Trade-offs

- [Existing unbound drafts stop releasing] → Preserve draft normalization and return sentence-specific migration blockers.
- [Authority integration is unavailable in a host] → Default to `relief_binding_authority_required`; do not fall back to embedded flags.
- [A valid shared factual baseline is rejected] → Allow same-claim evidence resolved either through bound application records or an exact claim-scoped source-evidence receipt.
- [Schema and runtime diverge] → Test runtime serialization against the 1.1 JSON Schema and include positive/negative multi-line fixtures.
- [Existing 1.0 filing manifests stop validating] → Keep them readable as historical JSON, require rebuild under manifest 1.1 before any new release approval, and never reinterpret 1.0 as current authority.
- [Upstream artifact changes after approval] → Recompute content fingerprints at each release-support check; stale receipts fail closed.
- [Manifest deletes one line and its receipt] → Compare the remaining projection with the independent host-authoritative complete remedy index.
- [Authority adapter mutates or coerces a request] → Send a deep copy, retain an immutable canonical request, and reject any mutation or noncanonical raw graph value.

## Migration Plan

1. Emit binding fields and plural issue IDs from new draft producers.
2. Configure the host authority adapter to resolve current upstream artifacts and trusted gate receipts.
3. Existing unbound payloads remain editable but show a release blocker until each remedy sentence is rebound.
4. Rollback is removal of the candidate branch; no main or global installation occurs in this change.

## Open Questions

None for this candidate scope. A later change may define a portable signed authority-receipt format; this change deliberately keeps the authority host-bound.
