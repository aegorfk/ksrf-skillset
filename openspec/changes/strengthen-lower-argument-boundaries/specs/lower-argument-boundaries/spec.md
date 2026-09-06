# Lower argument boundaries

## ADDED Requirements

### Requirement: Container boundaries remain visible
The autonomous method SHALL separate original judicial text from editorial or unrelated fragments and SHALL distinguish complete supplied text from a complete original act.

#### Scenario: Citation overlaps an excluded fragment
- WHEN a declared exact excluded span intersects a claim citation
- THEN the portable checker blocks the input without deleting the original text.

### Requirement: Grounds belong to identified demands
The checker SHALL validate optional demand branches using explicit claim roles and each ground's demand references.

#### Scenario: Ground is borrowed from another demand
- WHEN a branch uses a ground that does not identify that demand
- THEN the input is invalid, even if both demands appear in one act.

### Requirement: Autonomous candidate context
The method SHALL work with only supplied new-case materials and bundled resources and SHALL retain candidate status and exact input identity.

#### Scenario: A claim changes under the same ID
- WHEN its text or any dependent branch changes
- THEN the context digest changes, without implying legal approval.

#### Scenario: Missing document completeness
- WHEN completeness or original source quality is unknown
- THEN the method does not infer that no further grounds or facts exist.
