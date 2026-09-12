## ADDED Requirements

### Requirement: Comparative research is independently usable
The skill SHALL compare constitutional reasoning across jurisdictions without requiring a Russian dispute or a domestic anchor unless application in that target jurisdiction is requested.

#### Scenario: Pure comparison of salary protection
- **WHEN** the user asks how courts in Italy and Germany reason about salary adjustment
- **THEN** the skill compares the actual measures, rights, tests, conclusions and remedies with source locators
- **AND** it does not invent a Russian complaint or treat common vocabulary as an identical holding.

### Requirement: Methods remain bound to sources and speaker roles
The skill SHALL distinguish court reasoning, separate opinions, party submissions and editorial summaries and preserve exact source provenance for extracted methods.

#### Scenario: A candidate is a party submission
- **WHEN** a matching passage belongs to a party or has unknown attribution
- **THEN** the result remains a discovery candidate until the relevant court treatment is verified
- **AND** it does not become a judicial holding or a rule of the target jurisdiction.

### Requirement: Candidate extraction is resumable and does not promote legal claims
The extraction helper SHALL retain exact text offsets and hashes, isolate its output from input data and invalidate prior processing when the source or extractor changes.

#### Scenario: A decision changes between runs
- **WHEN** the same document identity has a different source or text hash
- **THEN** the updated version is processed and previous observations remain traceable
- **AND** neither version automatically changes deployed legal methodology.

### Requirement: Release includes the new independently discoverable package
The canonical installer and validators SHALL include the new skill while preserving existing packages and publication checks.

#### Scenario: Clean-room installation
- **WHEN** the reviewed manifest is installed into an empty target
- **THEN** all 16 skill entrypoints and their runtime references are installed and validated
- **AND** raw acts, developer evals, secrets and local runtime files are excluded.
