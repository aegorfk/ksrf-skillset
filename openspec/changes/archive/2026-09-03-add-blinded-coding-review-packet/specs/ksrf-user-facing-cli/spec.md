## ADDED Requirements

### Requirement: Audit preparation help identifies the independent-review handoff

The clean-installed Russian help for `quality coding-audit-prepare` MUST state
that the produced directory is the custodian bundle containing primary answers,
that only `independent-review-packet.zip` is intended for the independent coder,
and that the archive contains the selected full texts, blank templates, neutral
frozen-plan brief, built-in neutral codebook, and instructions but no primary coding
answers or hashes. It MUST describe the blinding as limited to the first coder's
answer and specific sampling lane, without claiming that membership in the union
sample is hidden; warn that the court text itself reveals facts and outcome; and
state that the full-text archive is not automatically safe to publish. It MUST also
explain that `--codebook-version` is required, that this release supports exactly
`1.0`, that the primary value is checked only for equality, and that successful JSON
output contains
`independent_review_packet_sha256`, that the custodian must retain and communicate
this expected digest separately from the archive, and that the reviewer must compare
it before using the ZIP.

#### Scenario: User reads preparation help before transferring files

- **WHEN** a user invokes `quality coding-audit-prepare --help`
- **THEN** the help names the one archive to transfer and says not to send the
  parent directory to the second coder
- **AND** it names required `--codebook-version 1.0` as the custodian's independent
  selection of the built-in neutral codebook, not a value learned from primary coding
- **AND** it explains how the separately retained ZIP SHA-256 anchors the exact
  transferred bytes without claiming a signature or reviewer authentication
- **AND** it preserves the separate human-review, privacy, legal-approval, and
  filing gates

#### Scenario: Successful preparation exposes the transfer digest

- **WHEN** `quality coding-audit-prepare` successfully publishes a new `1.1`
  custodian bundle
- **THEN** its stdout JSON contains
  `independent_review_packet_sha256=<64 lowercase hex>`
- **AND** that value equals the parent manifest file digest for
  `independent-review-packet.zip`
- **AND** stdout does not expose primary coding, primary hashes, first-coder
  identity, or sample-lane membership

#### Scenario: Embedded instructions are independently actionable

- **WHEN** the second coder opens `REVIEW-INSTRUCTIONS.md` without the parent
  custodian directory
- **THEN** the guide explains digest comparison and the exact closed 20-field
  completion contract, including enums, nested alternative grounds, identity
  preservation, and strict UTF-8 JSONL return requirements
- **AND** the attached neutral brief supplies exactly one directional
  `hypothesis_under_test` and the neutral plan rules needed to apply the attached
  codebook, without search/match/lane or custodian-review metadata
- **AND** it says that no native decision import, text-verification receipt,
  agreement result, legal approval, or filing permission has been created
