## Why

Release16 can produce a complete `coding-reliability.json` and a native
`coding-audit-finalization-receipt.json`, but current downstream consumers accept
the reliability object alone. That lets a standalone compatibility report with
`complete=true` be used for a claim even though it does not prove native
finalization of all imported differences or the final packet-text checks.

## What Changes

- Define native coding-reliability status as one verified triple: the exact
  `coding-reliability.json`, the exact
  `coding-audit-finalization-receipt.json`, and the independently retained
  `receipt_sha256` from successful finalizer stdout.
- Verify the receipt's closed contract and self-digest, the external digest, the
  exact reliability-file binding, and the shared audit-plan/candidate state. Do
  not add a `native` Boolean and do not change the `coding_reliability` v1.1
  contract.
- **BREAKING** Make the uncertainty-profile claim-use dimension, portable
  handoff validator, complaint-cycle result importer, and complaint-sentence
  evidence binder fail closed unless that exact triple is present and valid.
- Require the complaint-cycle `result import` caller to supply the external
  finalization receipt digest independently, persist it in the immutable import
  event, and recheck it during state derivation instead of trusting the value
  transported inside the handoff.
- Keep standalone `quality coding-reliability` output readable as
  compatibility-only diagnostics; it cannot independently make a profile,
  handoff, result, sentence, draft, or filing path claim-usable.
- Preserve value-free diagnostics: downstream failures expose bounded reason
  codes and digests, never coding values, quotations, labels tied to people,
  person-attributable timestamps, or absolute paths.
- Provide a migration path for existing Release16 finalization output. If its
  successful external receipt digest was retained, users can bind the existing
  exact pair and regenerate only downstream artifacts. If that anchor is absent
  or confirmation was uncertain, the digest must not be reconstructed from the
  receipt; native finalization must be repeated under its existing recovery
  rules.
- Keep all authentication, independence, legal-correctness, temporal-
  applicability, publication, approval, and filing gates separate.

## Capabilities

### New Capabilities

- `ksrf-native-coding-reliability-binding`: exact triple verification,
  compatibility boundary, value-free failure semantics, and Release16 migration
  rules shared by all claim-use consumers.

### Modified Capabilities

- `ksrf-practice-quality-exit-status`: uncertainty-profile and portable-handoff
  completion now require receipt-bound native coding reliability rather than a
  complete reliability object alone.
- `ksrf-user-facing-cli`: installed Russian help and errors expose the required
  receipt file, external digest, compatibility limit, and migration/recovery
  route.
- `ksrf-practice-analysis-identity-binding`: result import and derived claim state
  now preserve and recheck the independently supplied finalization receipt digest.

## Impact

- Expected runtime impact: `judicial_meaning.practice_quality`,
  `judicial_meaning.cli`, `judicial_meaning.handoff_workbench`, their schemas and
  tests, plus both independent complaint-cycle consumers
  (`scripts/ksrf_practice_analysis.py` and
  `ksrf.filing.practice_binding`).
- The complaint-cycle result-import event contract gains the independently
  supplied expected finalization receipt digest; historical events remain
  audit-readable but cannot drive a current claim-use state.
- Expected installed guidance impact: practice-quality and complaint-cycle
  instructions that currently describe a reliability object as sufficient for
  claim use.
- Existing Release16 finalization files remain usable when accompanied by the
  separately retained successful stdout digest. Existing standalone reliability
  reports and downstream artifacts remain audit-readable but must be regenerated
  before claim use.
- No network, model, database, source refresh, reviewer authentication, legal
  approval, publication, deletion, or filing action is introduced.
