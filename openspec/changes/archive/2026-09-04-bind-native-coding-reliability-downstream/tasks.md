## 1. Contract tests

- [x] 1.1 Add failing judicial-meaning tests for a valid native reliability triple, compatibility-only reliability, partial inputs, every digest/plan/candidate mismatch, and value-free hostile-input failures.
- [x] 1.2 Add failing schema and handoff tests for the exact six-type population, the receipt-only four-field binding, three-way profile binding, trusted-source continuity, and outer-rehash attacks.
- [x] 1.3 Add failing complaint-cycle tests for independent import anchoring, immutable event/state persistence, idempotent-anchor mismatch, historical blocking, filing-validator parity, and self-contained runtime imports.
- [x] 1.4 Add failing CLI/help tests for paired options, Russian bounded errors, no-output input failures, retained-anchor migration, and lost-anchor recovery guidance.

## 2. Native reliability verifier and uncertainty profile

- [x] 2.1 Implement a closed value-free verifier for the unchanged reliability v1.1 object, finalization receipt, independent expected digest, canonical reliability file bytes with one trailing LF, audit plan, candidates, and optional current plan.
- [x] 2.2 Extend the uncertainty-profile builder and schema with `coding_reliability_origin` and exact reliability, receipt, and external-expectation input bindings while keeping standalone reliability diagnostic-only.
- [x] 2.3 Wire paired receipt and expected-digest arguments into `quality uncertainty-profile` with fail-closed code 2 behavior and atomic no-output failures.

## 3. Six-binding handoff

- [x] 3.1 Extend workbench schemas and loaders with exactly one finalization-receipt binding whose explicit expected digest is never inferred from the receipt.
- [x] 3.2 Revalidate the complete native relation and profile cross-bindings in portable handoff creation and checking, including current-plan and ordered-candidate identity.
- [x] 3.3 Bind the complete special receipt binding through trusted-source persistence, trusted result receipts, and handoff import continuity checks.

## 4. Complaint-cycle enforcement

- [x] 4.1 Harden the standalone v2 result validator for the exact six bindings and complete native relation without importing the sibling skill.
- [x] 4.2 Require the independent expected digest at `result import`, persist it in the immutable self-digested event, enforce identical idempotent re-imports, and recheck it during state derivation.
- [x] 4.3 Harden the independently runnable filing `practice_binding` validator and evidence gate with parity across positive and adversarial native-lineage vectors.
- [x] 4.4 Update complaint-cycle schemas so historical artifacts remain audit-readable but cannot satisfy current drafting, ready, or claim-evidence gates.

## 5. User guidance and verification

- [x] 5.1 Update installed Russian help and references with a copyable retained-anchor regeneration sequence, standalone compatibility warning, and new-sibling recovery when the external digest is missing or uncertain.
- [x] 5.2 Run focused tests, full source and Python 3.10/3.13 suites, strict skill/schema checks, OpenSpec validation, install-payload parity, privacy/value-leak checks, and an independent review.
- [x] 5.3 Synchronize validated delta specs, archive the OpenSpec change, build the publication manifest, commit atomically, push main and release branch, and verify exact remote SHA equality.
- [x] 5.4 Install the published runtime globally and pass `install.sh --verify`, `--verify-current`, strict installed-skill validation, and absence checks for maintainer-only payloads.
