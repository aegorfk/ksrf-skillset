## ADDED Requirements

### Requirement: Native audit-bundle comparison has stable fail-closed outcomes

The exact `quality native-reliability compare-audit-bundles` command MUST use fixed
priority `unreadable > invalid > mismatch > match`. `unreadable` covers unavailable
path/read/inspection/codebook/ACL capability, bounded resource rejection,
memory/recursion failure, drift, failed recapture, or close uncertainty. `invalid`
covers stable expected-digest syntax, topology, privacy, inventory, canonical/ZIP/
closed-contract, or installed-codebook-binding violations. `mismatch` covers valid
external expectations that disagree or independently valid packages with unequal raw
files. Only all required successful checks MAY yield `match`.

The command MUST return `0` only for `match`, `3` only for `mismatch`, and `2` for
`invalid` or `unreadable`. Every handler outcome MUST emit one complete canonical
report on stdout with empty stderr. Parser faults before handler entry use the
existing exit-`2` path. Interrupted, short, or failed stdout write/flush returns `2`
without retrying output, writing stderr, or disclosing the stream exception; a
complete report cannot be promised. No existing command outcome changes.

#### Scenario: Exact two-anchor equality returns zero

- **WHEN** all capture, privacy, contract, codebook, external-anchor, raw-byte, and
  recapture checks succeed
- **THEN** the report is `match`, recovery comparison is true, and exit is `0`
- **AND** this creates no recovery, authentication, legal, publication, or filing
  authority

#### Scenario: Valid inputs differ

- **WHEN** valid stable prerequisites expose an anchor or raw-byte mismatch
- **THEN** the report is `mismatch` and exit is `3`
- **AND** neither package is modified

#### Scenario: Static invalidity returns two

- **WHEN** stable input violates syntax, topology, privacy, inventory, canonical
  artifact structure, or codebook binding
- **THEN** the report is `invalid` and exit is `2`

#### Scenario: Read or recapture uncertainty returns two

- **WHEN** inspection cannot complete or any captured object changes
- **THEN** the report is `unreadable` and exit is `2`
- **AND** no lower-priority result is trusted

#### Scenario: Parser syntax is not a comparison report

- **WHEN** an option is missing, lacks its value, is abbreviated, or is unknown
- **THEN** argparse exits `2` without comparison JSON
- **AND** the handler opens no package

#### Scenario: Output cannot be delivered completely

- **WHEN** the single stdout write is short or write/flush raises a stream error
- **THEN** the command returns `2`, leaves stderr empty, and never retries output
- **AND** no source path, digest, or exception text is added to the output
- **AND** the input packages and installed codebook remain unchanged
