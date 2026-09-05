## ADDED Requirements

### Requirement: Native finalization comparison has stable fail-closed process outcomes

The system SHALL give the installed native finalization comparison stable process outcomes.
The exact `judicial_meaning.py quality native-reliability compare-finalizations`
command MUST use the fixed state priority
`unreadable > invalid > mismatch > match`. `unreadable` covers an unavailable
path, descriptor, bounded read, filesystem/ACL inspection capability, resource
bound, input drift, failed final recapture, or unconfirmed close. `invalid` covers
stable readable input that violates SHA syntax, distinct-sibling/common-parent
topology, ownership/mode/link/ACL privacy, exact inventory, canonical encoding, or
a closed artifact contract. `mismatch` covers valid prerequisites with a failed
self-digest, receipt-to-file binding, uncertain internal relation, repeated native
relation including its external anchor, or exact raw four-file equality. Only
all-true checks MAY yield `match`.

The command MUST return `0` only for `match`, `3` only for `mismatch`, and `2` for
`invalid` or `unreadable`. Every handler outcome MUST emit one complete closed
report on stdout with empty stderr before returning its code. Parser faults before
the handler and stdout write/flush/interruption use the existing exit-`2` error path
and cannot promise a complete report. No existing doctor, finalizer, quality-gate,
handoff, or complaint-cycle process outcome may change.

#### Scenario: Exact externally anchored comparison returns zero

- **WHEN** every capture, privacy, contract, digest, relation, byte-equality, and
  final-recapture check succeeds
- **THEN** the report has `status=match`,
  `recovery_comparison_valid=true`, and process code `0`
- **AND** empty stderr and code `0` grant no recovery eligibility, authentication,
  legal, publication, claim, or filing authority

#### Scenario: Valid directories differ

- **WHEN** every required prerequisite is valid but a relation, external anchor, or
  corresponding file byte comparison fails
- **THEN** the report has `status=mismatch` and process code `3`
- **AND** stderr remains empty and neither directory is modified

#### Scenario: Static contract violation returns two

- **WHEN** readable stable input violates topology, privacy, inventory, canonical
  encoding, closed artifact structure, or expected-digest syntax
- **THEN** the report has `status=invalid` and process code `2`
- **AND** stderr remains empty and no repair occurs

#### Scenario: Read or recapture uncertainty returns two

- **WHEN** a required inspection/read cannot complete or any captured object changes
  before final recapture completes
- **THEN** the report has `status=unreadable` and process code `2`
- **AND** no lower-priority match or mismatch is trusted

#### Scenario: Higher-priority fault accompanies byte mismatch

- **WHEN** one observable byte relation differs and a safe independent check also
  establishes input drift or invalid structure
- **THEN** `unreadable` or `invalid` wins according to the fixed priority
- **AND** the reason list retains only safely evaluated closed reasons in fixed order

#### Scenario: Parser syntax never masquerades as comparison

- **WHEN** a required option is omitted, lacks its token, is abbreviated, or an
  unknown option prevents handler entry
- **THEN** argparse returns code `2` and emits no comparison JSON
- **AND** no input directory is opened by the comparison handler
