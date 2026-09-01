## Why

`SentenceEvidence.role` is currently an open string. Only eight exact values are treated as filing-significant, so a typo such as `application_findng` or `practice_cliam` becomes release-exempt and reports `release_supported=true` even with no evidence. Missing roles and legacy raw strings also become `narrative`, while the release package has no complete host-owned registry that can distinguish legitimate narrative from a downgraded filing claim.

## What Changes

- Define one canonical sentence-role registry: `narrative` plus the eight existing filing-significant roles.
- Preserve every explicit non-blank string role byte-for-byte in legacy working drafts, but make every unknown role a sentence-specific exact machine blocker; reject explicit blank/non-string roles and never trim, alias, or silently map them to `narrative`.
- Require every ready release to re-resolve a complete host-owned sentence-role index for the exact matter and draft. Bind every entry to a continuous global 1-based draft ordinal, sentence ID, section, exact text hash, canonical role, one index hash, one authority revision, and one stable snapshot check time.
- Detect role downgrade, deletion, insertion, sentence reordering (including reordering sentence-bearing sections), text substitution, unknown host roles, incomplete indexes, mismatched blocker markers, and stale/replayed receipts before expert review and again before human signing/filing readiness.
- Advance only the filing-package contract to schema version `1.4`; keep structured complaint schema `1.3` draft-readable, while conditionally restricting roles and requiring the complete index for ready manifest statuses.
- Add focused regression tests, schema checks, filing-contract documentation, and behavioral evals.
- **BREAKING at release only**: an unknown sentence role or a ready package without a current complete sentence-role index can no longer pass release verification.

## Capabilities

### New Capabilities

- `ksrf-sentence-role-integrity`: Fail-closed role validation and host-attested complete sentence-role inventory for filing release.

### Modified Capabilities

None.

## Impact

- Runtime: complaint release support, pack construction, manifest verification, approval, and workflow dependency injection.
- Contract: filing-package schema advances from `1.3` to `1.4`; structured complaint stays at `1.3` so unknown legacy draft roles remain readable.
- Methodology and evaluation: complaint-cycle release reference plus complaint QA and complaint-cycle behavioral evals.
- Compatibility: only an omitted role and a raw legacy sentence retain the existing explicit `narrative` default outside the requested-remedy section; that section coerces absent/raw and explicitly canonical roles to `requested_remedy`, while preserving explicit unknown strings for blocked repair. Explicit string values survive without whitespace normalization, explicit blank/non-string values are invalid, and unknown strings block every release-ready path.
- Publication remains candidate-only; no merge to `main` or global-skill installation is authorized.
