## ADDED Requirements

### Requirement: Select methods by the new case
The skills SHALL use the materials of the current dispute to identify the rule, protected interest, harm mechanism, necessary premises and requested protection, regardless of subject matter.

#### Scenario: A non-wage dispute is supplied
- **WHEN** the user provides a dispute unrelated to wages or benefits
- **THEN** the skill chooses operations relevant to its actual mechanism without inventing wage facts, pay formulas or salary comparators
- **AND** subject-specific source cards are optional and require matching premises

#### Scenario: A general operation does not fit
- **WHEN** the required premise of an operation is missing or contradicted
- **THEN** the skill records the gap or rejects that use instead of forcing the dispute into a stored example

### Requirement: Preserve conditional conclusions and source context
The skills SHALL preserve the original context of verified foreign cases and distinguish a reusable operation from a substantive rule transferable to Russia.

#### Scenario: A dispute reveals an application error only
- **WHEN** the evidence does not show that the harmful result follows from the contested rule or its binding meaning
- **THEN** the skill may conclude that a constitutional mechanism is not established and identify the missing link or ordinary remedy for verification

#### Scenario: The user requests a specific topic
- **WHEN** a topical comparison is explicitly requested
- **THEN** the relevant examples remain available within that request without becoming the default for other cases
