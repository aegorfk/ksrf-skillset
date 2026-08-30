## ADDED Requirements

### Requirement: Reject non-string transfer limits without traceback

The authority-ledger validator MUST report a non-string
`authorities[].transfer.limit` as a structural validation error and MUST NOT invoke
string methods on the untrusted value. The standalone CLI MUST retain its existing
validation-failure exit code and `ERROR:` diagnostics.

#### Scenario: Drafting-ready ledger contains a container limit

- **WHEN** an authority has `drafting_ready` set to `true` and `transfer.limit` is
  `null`, a number, a boolean, an array, or an object
- **THEN** validation exits with code `1`, reports the field as `expected string`,
  emits no traceback, and does not write or mutate the input ledger

#### Scenario: Drafting-ready ledger contains a string limit

- **WHEN** `transfer.limit` is a string
- **THEN** validation uses the existing empty/non-empty rule and preserves all other
  authority-ledger behavior
