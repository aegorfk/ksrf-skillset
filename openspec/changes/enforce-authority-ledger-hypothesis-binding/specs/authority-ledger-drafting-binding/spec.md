## ADDED Requirements

### Requirement: Drafting authorities belong to the block hypothesis

The authority-ledger validator MUST reject every authority reference in a
drafting block when the referenced authority's `hypothesis_ids` does not
contain that block's `hypothesis_id`.

#### Scenario: Cross-hypothesis authority is rejected

- **GIVEN** an otherwise valid drafting ledger
- **AND** block `B1` has `hypothesis_id = H1`
- **AND** `B1.authority_ids = [A1]`
- **AND** authority `A1.hypothesis_ids = [H2]`
- **WHEN** the ledger is validated
- **THEN** validation fails
- **AND** the error identifies `$.drafting_blocks[0].authority_ids[0]`

#### Scenario: Multi-hypothesis authority is accepted

- **GIVEN** an otherwise valid drafting ledger
- **AND** block `B1` has `hypothesis_id = H1`
- **AND** `B1.authority_ids = [A1]`
- **AND** authority `A1.hypothesis_ids = [H1, H2]`
- **WHEN** the ledger is validated
- **THEN** the block-to-authority hypothesis check passes

#### Scenario: Every referenced authority is checked

- **GIVEN** a drafting block for H1 references authorities A1 and A2
- **AND** A1 declares H1
- **AND** A2 does not declare H1
- **WHEN** the ledger is validated
- **THEN** validation fails on the reference to A2

#### Scenario: Non-drafting ledgers remain unaffected

- **GIVEN** a research or audit ledger without drafting blocks
- **WHEN** the ledger is validated
- **THEN** no hypothesis-binding error is added solely because the ledger has
  no drafting blocks
