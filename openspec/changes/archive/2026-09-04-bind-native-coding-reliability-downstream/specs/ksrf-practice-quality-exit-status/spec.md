## ADDED Requirements

### Requirement: Uncertainty claim use requires receipt-bound reliability

The uncertainty-profile builder and CLI MUST accept the reliability artifact,
finalization receipt, and origin expected receipt digest as distinct inputs. The
receipt option and expected-digest option MUST be paired and MUST require the
reliability input. A malformed or mismatched supplied triple MUST be rejected as an
input error. Reliability alone MUST remain accepted for compatibility diagnostics,
but its dimension MUST be non-native, `usable_for_claim=false`, and blocking even
when the reliability object's exact `complete` is true.

A claim-usable profile MUST bind the exact reliability artifact digest, complete
receipt artifact digest, and origin expected receipt self-digest in closed
`input_sha256s`. All other dimensions retain their independent gates. Native
reliability verification alone MUST NOT make the whole profile claim-ready.

#### Scenario: Standalone complete reliability remains diagnostic

- **WHEN** uncertainty-profile receives a valid complete v1.1 reliability object
  without both receipt inputs
- **THEN** it returns a value-free compatibility-only coding dimension and
  `claim_use_ready=false`

#### Scenario: Profile binds the confirmed triple

- **WHEN** uncertainty-profile receives an exact valid triple and all other
  dimensions are usable
- **THEN** its closed input hashes preserve all three native origins and the coding
  dimension may participate in `claim_use_ready=true`

#### Scenario: Receipt option is only half supplied

- **WHEN** the caller supplies either the finalization receipt or its expected
  digest without the other required members
- **THEN** the CLI returns the existing invalid-input status without constructing
  a claim-usable profile

### Requirement: Portable handoff revalidates native reliability and trusted origin

Reviewed handoff create MUST require the sixth
`coding_audit_finalization_receipt` quality binding and a separate
`--expected-finalization-receipt-sha256` value. The loader MUST place that explicit
value in the receipt binding's `expected_receipt_sha256` and MUST NOT derive it from
the receipt. Check and import MUST independently verify the exact native triple,
current plan/candidate bindings, and the uncertainty profile's reliability,
receipt, and origin-expected hashes.

The trusted result receipt MUST content-bind the complete special binding,
including the expected digest. Reviewed handoff check/import MUST compare it with
the trusted quality copy and trusted source receipt; that continuity MUST NOT be
called authentication.

#### Scenario: Handoff create receives an explicit anchor

- **WHEN** all six quality files and the matching explicit finalization receipt
  digest are supplied
- **THEN** create emits the special four-field receipt binding and five unchanged
  three-field bindings

#### Scenario: Portable handoff is self-consistently rewritten

- **WHEN** a caller changes a native input or profile origin and recomputes the
  envelope identifier
- **THEN** handoff check/import rejects the result through inner triple or
  trusted-source parity checks

#### Scenario: Receipt binding is absent

- **WHEN** a historical five-binding result is checked for claim use
- **THEN** it remains audit-readable but cannot pass current reviewed-handoff
  validation

### Requirement: Stable schemas disclose native-binding runtime invariants

The established practice-quality, workbench, and handoff schema paths SHALL stay
stable with their top-level versions while claim-use definitions harden in place. They
MUST describe the sixth discriminated binding, exactly-one-LF reliability file
digest, external expectation, cross-artifact equalities, and profile origin links.
They MUST state which digest/set/byte invariants require runtime validation.

#### Scenario: Historical schema-valid artifact reaches current runtime

- **WHEN** an older profile or five-binding handoff lacks the native receipt origin
- **THEN** stable-path schema/runtime validation treats it as historical only and
  requires downstream regeneration
