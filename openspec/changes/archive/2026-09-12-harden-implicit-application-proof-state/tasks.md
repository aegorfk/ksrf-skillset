## 1. Proof-state correction

- [x] 1.1 Reject contradicted or duplicate implicit premise records in both the independent-ground preservation helper and the ordinary conjunctive implicit-proof classifier.
- [x] 1.2 Require a complete diagnostic named-review marker before emitting `implicit_norm_use_preserved` or `implicitly_applied_proven`, without treating that raw marker as trusted approval of fingerprinted content.
- [x] 1.3 Return `application_unclear` with an explicit verification reason when an implicit-use candidate is pending, incomplete, rejected or contradicted while an independent ground controls causation.
- [x] 1.4 Preserve the existing `not_applied` result when a complete independent ground exists and no direct or implicit norm-use candidate is asserted.
- [x] 1.5 Require court or disposition authorship for affirmative non-application evidence so a party-only assertion cannot prove an independent ground.
- [x] 1.6 Filter reported independent-ground evidence by the same proof predicate so an invalid extra span cannot inherit a valid span's status.
- [x] 1.7 Reject a complete-independent-ground assertion unless the canonical outcome-causation axis carries the matching status.
- [x] 1.8 Reject usable court-authored independent-ground evidence that conflicts with the canonical outcome-causation axis.
- [x] 1.9 Mirror duplicate-premise and independent-ground causal-axis invariants in the standalone Draft 2020-12 schema.
- [x] 1.10 Require nonblank quotes for incorporation and later independent-ground chain proof in assessment and binding.
- [x] 1.11 Require a timezone-aware RFC 3339 timestamp before a diagnostic review marker counts as complete.

## 2. Method and executable checks

- [x] 2.1 Clarify the implicit-application reference so that record approval, trusted release approval, norm use, causal harm and structured independent-ground evidence remain distinct and internally consistent.
- [x] 2.2 Add executable tests for approved, pending, contradicted and absent implicit-use records across both independent-ground call paths and the ordinary implicit-proof branch, plus runtime/schema parity for duplicate premises and causal-axis conflicts.
- [x] 2.3 Replace the wave-eight fixture's unbound `approved_full_record` proxy with explicit diagnostic named-review and missing-trusted-approval fields, and bind them to runtime assertions.
- [x] 2.4 Normalize affected SHALL bodies and add a machine-readable JSON test for all continuation clauses missed by strict validation.
- [x] 2.5 Add active-delta and post-archive base-spec JSON assertions so the machine-readable OpenSpec contract is checked on both sides of archive.

## 3. Verification and release

- [x] 3.1 Run focused tests, the full regression, strict OpenSpec validation, skillset validation, offline installation and an independent adversarial probe.
- [x] 3.2 Update verification receipts, archive the corrective OpenSpec change, regenerate the manifest against the exact published parent and publish without force.
- [x] 3.3 Verify live remote SHA and synchronize canonical global skills from the final published tree.
