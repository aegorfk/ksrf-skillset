## ADDED Requirements

### Requirement: Native coding-audit preparation is actionable in Russian help

The clean-installed Russian help MUST expose `quality coding-audit-prepare` with required workspace, general-sample maximum, exclusion-sample maximum, and new output-directory options. It MUST explain that the command verifies the frozen plan, screening, approved primary coding, and stored full text; creates a new immutable audit-input bundle without network access; refuses an existing destination; and does not perform independent secondary review, adjudication, legal approval, or filing.

#### Scenario: User can prepare first-party audit inputs

- **WHEN** a user invokes `quality coding-audit-prepare --help`
- **THEN** help returns code `0` with empty stderr and describes every required option and all generated bundle files in plain Russian
- **AND** it directs the user from the generated pending templates to separately completed human secondary decisions and the existing coding-reliability consumer

#### Scenario: Help does not overstate automation

- **WHEN** help describes generated review queues and templates
- **THEN** it states that they are pending work aids rather than review evidence
- **AND** it does not claim corpus completeness, coding agreement, legal readiness, approval, or filing authority

#### Scenario: Existing manual producer route remains available

- **WHEN** an expert already has exact contract-specific screening and primary records
- **THEN** `quality coding-audit-plan` remains documented and executable with the same machine-facing options and behavior
