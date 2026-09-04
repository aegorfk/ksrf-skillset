## ADDED Requirements

### Requirement: Native reliability inputs and compatibility limit are visible in Russian

Installed Russian help SHALL name the finalization receipt file and the separate
`--expected-finalization-receipt-sha256` input for `quality uncertainty-profile`,
`handoff create`, and complaint-cycle `result import`. It MUST say to take that
digest only from finalizer stdout followed by normal successful return and MUST
explain that the value inside the receipt is not a substitute. Handoff help MUST
show that the explicit value pairs with the one receipt `--quality-binding`; result
import help MUST explain that its independently supplied value is recorded in the
immutable import event and rechecked later.

Help MUST describe standalone `quality coding-reliability` as compatibility-only
diagnostics even when `complete=true`, without hiding or removing that command.

#### Scenario: User follows the complete downstream route

- **WHEN** the user opens the three relevant help surfaces
- **THEN** the Russian text supplies copyable argument names, identifies the
  out-of-band source, and distinguishes diagnostic reliability from native claim
  use

#### Scenario: User tries to copy the receipt member

- **WHEN** migration guidance explains a missing external digest
- **THEN** it prohibits reconstructing the expectation from the receipt and points
  to unchanged-input finalizer recovery

### Requirement: Native-binding failures stay actionable and value-free

Russian CLI errors SHALL identify the next technical action for missing, partial,
mismatched, or historical native bindings without repeating private input content or
absolute paths. Help MUST state that success proves only bounded technical lineage
and does not authenticate a person or establish legal correctness, current law,
publication permission, approval, or filing readiness.

#### Scenario: Imported handoff lacks an independent anchor

- **WHEN** complaint-cycle result import receives a handoff but no independent
  expected finalization receipt digest
- **THEN** the CLI stops with a concise Russian remediation and stores no new
  claim-eligible import event
