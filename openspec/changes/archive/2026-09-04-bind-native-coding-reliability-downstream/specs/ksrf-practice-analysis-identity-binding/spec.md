## ADDED Requirements

### Requirement: Result import independently anchors native coding reliability

Complaint-cycle `result import` MUST require
`--expected-finalization-receipt-sha256` for a v2 claim-bearing result. The importer
MUST independently compare it with the special quality binding's
`expected_receipt_sha256` and the recomputed finalization receipt self-digest after
validating the exact six-binding native relationship. It MUST record the explicit
value in the append-only `result_import` event, include it in the event digest, and
reject an idempotent re-import whose supplied value differs from the existing event.

`run attach` MUST remain unchanged because attachment precedes creation of the
finalization receipt. Legacy or unanchored results MAY remain audit-readable under
their existing status, but they MUST NOT be eligible for drafting or claim use.

#### Scenario: Independent import anchor matches the handoff

- **WHEN** a v2 result, attached trusted source, and independently supplied digest
  all bind the same native finalization receipt
- **THEN** import records that digest in the immutable event and may preserve the
  existing drafting-eligibility path

#### Scenario: Transported and local expectations differ

- **WHEN** the explicit import argument differs from the handoff binding or receipt
  self-digest
- **THEN** import fails before writing the result or event even if outer handoff
  hashes are valid

#### Scenario: Re-import supplies another expectation

- **WHEN** the same result identifier already has an immutable import event and a
  later invocation supplies a different expected digest
- **THEN** the importer rejects it rather than returning the earlier event as an
  idempotent success

### Requirement: Derived claim state rechecks the immutable native anchor

State derivation MUST reopen the selected result and import event and revalidate
the exact equality among event `expected_finalization_receipt_sha256`, special
binding `expected_receipt_sha256`, and receipt self-digest. It MUST also repeat the
six-binding and profile-origin relationship needed for claim use. The expected
digest MUST remain in exact-material ready bindings and prefiling refresh identity
so a later result/event substitution revokes readiness.

#### Scenario: Imported result changes after the event

- **WHEN** the stored result or any native binding changes after import while event
  bytes remain unchanged
- **THEN** state becomes blocked or stale and no wording, refresh, drafting, or
  filing transition remains ready

#### Scenario: Historical event lacks the expected digest

- **WHEN** state derives from an older result-import event without the new field
- **THEN** the event remains audit-readable but cannot contribute a current ready
  binding

### Requirement: Complaint-sentence binding independently enforces native lineage

The filing `practice_binding` consumer MUST independently verify the exact six
quality bindings, the finalization receipt self-digest and external expectation,
the receipt-to-reliability file/plan/candidate links, the uncertainty profile's
three origin links, and equality with the current claim state's immutable import
expectation. It MUST fail before emitting a complaint-sentence evidence receipt if
any relation is absent or mismatched, regardless of outer hashes or
`drafting_ready=true`.

#### Scenario: Ready state is cross-bound to another receipt

- **WHEN** a result and state are individually rehashed but carry different native
  finalization expectations
- **THEN** sentence evidence binding rejects the practice claim and emits no
  evidence receipt

#### Scenario: Standalone reliability replaces the finalizer output

- **WHEN** a complete compatibility reliability object is substituted without its
  exact native receipt relationship
- **THEN** both complaint-cycle consumers block claim use with value-free reasons
