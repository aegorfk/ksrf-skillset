# Argument checks

## ADDED Requirements

### Requirement: Preserve the evidentiary operator
The portable checker SHALL validate declared finding operators and SHALL NOT equate different known operators for the same proposition.

#### Scenario: Non-proof is presented as proof of absence
- **WHEN** an equivalence check connects not_proven and proven_not
- **THEN** the packet is rejected structurally without claiming semantic adjudication.

#### Scenario: The operator is unknown
- **WHEN** equivalence cannot be checked because a declared operator is unknown or missing
- **THEN** the result retains an evidence gap rather than approving equivalence.

### Requirement: Separate existence and extent of the residual measure
The portable checker SHALL require distinct entitlement and extent assessments for an optional residual-ground check and SHALL bind both to grounds of the same branch.

#### Scenario: One ground remains but the original measure is unexplained
- **WHEN** the residual check supports entitlement and leaves extent unknown
- **THEN** it reports needs_evidence and does not infer the original extent.

#### Scenario: A ground belongs to another demand
- **WHEN** a residual check references a ground outside its branch
- **THEN** it is rejected.

### Requirement: Optional checks remain honest and corpus independent
Existing packets SHALL remain supported, missing checks SHALL be reported as not provided, and structural results SHALL NOT establish legal truth or historical eligibility.

#### Scenario: Standalone installed checker has no source corpus
- **WHEN** a synthetic packet is checked from the installed skill alone
- **THEN** the new checks work without network or research artifacts and remain context-hash bound.
