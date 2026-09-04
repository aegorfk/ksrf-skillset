# ksrf-native-coding-reliability-binding Specification

## Purpose
TBD - created by archiving change bind-native-coding-reliability-downstream. Update Purpose after archive.
## Requirements
### Requirement: Native coding reliability is an exact verified triple

The system MUST describe coding reliability as native for claim use only after it
verifies the unchanged closed `coding_reliability` v1.1 object, the closed
`coding_audit_finalization_receipt` object, and an independently supplied lowercase
SHA-256 retained from successful finalizer stdout. It MUST recompute both object
digests, require the expected digest to equal the receipt self-digest, and require
the receipt `coding_reliability_file_sha256` to equal SHA-256 of the canonical
compact sorted-key UTF-8 reliability JSON with `ensure_ascii=false`,
`allow_nan=false`, and exactly one trailing LF. It MUST also require exact
audit-plan, candidate-order, completion, and current-plan equalities where the
consumer has a current plan.

The implementation MUST NOT add or infer `native=true`, revise the
`coding_reliability` v1.1 fields, or treat a receipt member as the independently
supplied expectation.

#### Scenario: Confirmed Release16 pair becomes native input

- **WHEN** the exact finalizer reliability file and receipt are supplied with the
  separately retained successful stdout `receipt_sha256`
- **THEN** the verifier accepts native technical lineage only if every digest,
  plan, candidate, and completion equality holds
- **AND** acceptance does not assert authenticated review or legal authority

#### Scenario: Self-consistent artifacts lack an external expectation

- **WHEN** reliability and receipt are internally valid but the caller omits the
  expected digest or derives it only from the receipt being checked
- **THEN** native status is unavailable and every claim-use consumer fails closed

#### Scenario: Outer artifacts are rehashed after substitution

- **WHEN** any reliability, receipt, audit-plan, candidate population, or expected
  digest is replaced and surrounding hashes are recomputed
- **THEN** independent cross-artifact verification rejects the substituted triple

### Requirement: Finalization receipt is the sole four-field quality binding

Claim-bearing quality bindings MUST contain exactly six unique required types. The
`coding_audit_finalization_receipt` binding MUST contain exactly
`quality_type`, `artifact_sha256`, `artifact`, and
`expected_receipt_sha256`. Its `artifact_sha256` MUST bind the complete receipt
object, while `expected_receipt_sha256` MUST equal the independently supplied
external expectation and the recomputed receipt self-digest. Every other quality
binding MUST retain exactly `quality_type`, `artifact_sha256`, and `artifact` and
MUST reject `expected_receipt_sha256`.

#### Scenario: Six bindings preserve two different receipt digests

- **WHEN** a reviewed result carries all six required bindings
- **THEN** the receipt binding keeps the full-object artifact digest distinct from
  the out-of-band receipt self-digest and both are independently verified

#### Scenario: Generic binding smuggles an expectation

- **WHEN** a non-receipt binding includes `expected_receipt_sha256`, or the receipt
  binding omits it
- **THEN** the closed discriminated-union validator rejects the result

### Requirement: Native-binding diagnostics disclose no review content

Every new native-binding failure MUST emit only bounded reason codes, field names,
counts, permitted candidate identifiers, and SHA-256 values. It MUST NOT echo
coding values, quotations, substantive labels, pseudonyms, person-attributable
timestamps, complete input objects, or absolute paths. A valid triple MUST remain
only evidence of bounded technical lineage and MUST NOT establish reviewer
identity, authorship, independence, packet use, legal correctness, norm temporal
applicability, freshness, publication permission, approval, or filing readiness.

#### Scenario: Hostile private values fail verification

- **WHEN** an invalid reliability or receipt embeds distinctive private strings
- **THEN** the returned error or incomplete-status projection identifies only the
  bounded failure class and never repeats those strings or their path

### Requirement: Release16 migration never reconstructs a missing anchor

Existing Release16 finalization output SHALL satisfy the new verifier without
regenerating finalization only when the exact successful stdout digest was retained
outside the directory. Downstream uncertainty, handoff, import, state, and evidence
artifacts MUST be regenerated under the new contract. If the external digest is
missing or its confirmation was interrupted or uncertain, the system MUST direct
the user to the existing unchanged-input/new-sibling/byte-compare recovery and MUST
NOT read the expected value from the receipt.

#### Scenario: Existing confirmed finalization is migrated

- **WHEN** a user retains the exact two files and independently recorded successful
  stdout digest from Release16
- **THEN** only downstream artifacts need regeneration and the original
  finalization directory remains immutable

#### Scenario: Only the receipt survives

- **WHEN** the user has the receipt but no trustworthy external confirmation
- **THEN** the receipt self-digest remains audit-readable but cannot be promoted to
  the missing expectation
