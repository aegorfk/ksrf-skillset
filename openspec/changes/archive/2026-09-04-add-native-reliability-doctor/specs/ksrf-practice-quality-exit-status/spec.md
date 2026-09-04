## ADDED Requirements

### Requirement: Native reliability doctor has stable fail-closed process outcomes

The installed `judicial_meaning.py quality native-reliability doctor` command MUST
use one fixed state priority:
`unreadable > invalid > incomplete > mismatch > valid`. A supplied file that
cannot be opened or read as bytes MUST be `unreadable`. Readable input with
invalid UTF-8, strict JSON, closed artifact contract, exact canonical reliability
bytes, or expected-digest syntax MUST be `invalid`. An absent option MUST be
`incomplete` unless a higher-priority supplied-input fault exists. Individually
valid complete members with a failed self/external/file/plan/candidate relation
MUST be `mismatch`. Only a fully verified triple MUST be `valid`.

The command MUST return `0` only for `valid`, `3` for `incomplete` or `mismatch`,
and `2` for `invalid` or `unreadable`. Every invocation that reaches the handler
MUST emit the complete closed report on stdout with empty stderr before returning
its code. It MUST NOT accept `--output` or persist a report. Argparse faults that
occur before the handler, and a failure of stdout itself, retain the existing
exit-`2` error path and cannot promise a doctor report. These rules MUST NOT alter
the process outcomes or output channels of existing quality commands.

#### Scenario: Verified triple returns zero

- **WHEN** every exact native-reliability contract and relation check succeeds
- **THEN** the doctor emits `status=valid` on stdout and returns `0`
- **AND** empty stderr and code `0` grant no legal or filing authority

#### Scenario: Missing member returns three

- **WHEN** the invocation reaches the handler with at least one of the three
  input options absent and no supplied-input invalidity
- **THEN** the doctor emits `status=incomplete` on stdout and returns `3`
- **AND** stderr remains empty

#### Scenario: Relation mismatch returns three

- **WHEN** all three members are individually valid but at least one exact
  relation check fails
- **THEN** the doctor emits `status=mismatch` on stdout and returns `3`
- **AND** stderr remains empty

#### Scenario: Invalid or unreadable input returns two

- **WHEN** a supplied path cannot be read or a supplied value violates its
  encoding, strict JSON, closed object, canonical byte, or SHA-256 syntax contract
- **THEN** the doctor emits `status=unreadable` or `status=invalid` on stdout and
  returns `2`
- **AND** stderr remains empty and no partial artifact is written

#### Scenario: Higher-priority fault accompanies an omission

- **WHEN** one input option is absent and another supplied input is invalid or
  unreadable
- **THEN** the doctor reports the higher-priority `invalid` or `unreadable` state
  and returns `2`
- **AND** its reason list may also retain the bounded missing-member code in the
  fixed report order

#### Scenario: Parser syntax never masquerades as a relation report

- **WHEN** an option lacks its required token or an unknown option prevents
  argparse from invoking the handler
- **THEN** the command returns the standard parser code `2`
- **AND** it emits no doctor JSON report
