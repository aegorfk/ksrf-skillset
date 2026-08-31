## ADDED Requirements

### Requirement: Repairable evidence route
The triage skill MUST route a known, controllably repairable application-evidence gap to `FIX_FIRST` and MUST NOT describe it as an unavailable record.

#### Scenario: Truncated window in an identified full act
- **WHEN** the exact act and locator are known but the quote window, speaker role or causal context is incomplete
- **THEN** combined application remains `application_unclear`, filing readiness remains false, and the output returns one bounded `FIX_FIRST` task for that act and stage

#### Scenario: Party-only text in an available act
- **WHEN** an available full act contains only a located party submission and no verified court-authored treatment
- **THEN** norm use remains `party_only`, causation remains unclear, and `FIX_FIRST` seeks court-authored adoption, rejection or positive non-use evidence without inferring silence

### Requirement: Unavailable-record abstention
The triage skill MUST reserve `ABSTAIN_PENDING_RECORD` for a critical record whose unavailability is supported by a documented bounded official-source search.

#### Scenario: Official act unavailable after bounded search
- **WHEN** the search journal identifies the expected act, attempted official routes and an uncontrolled access gap without a reliable full-text substitute
- **THEN** the output may return `ABSTAIN_PENDING_RECORD` and MUST NOT convert failed access into absence or non-application

### Requirement: Per-stage application evidence record
The triage output MUST emit one `ApplicationEvidenceRecord` for every active `norm × stage` pair before it emits a combined application status.

#### Scenario: Incomplete application packet
- **WHEN** any required source identity/hash, court/stage/date, court-authored locator/window, speaker role, causal passage, independent-ground check or chain/preservation evidence is missing
- **THEN** the record names the missing fields, retains `application_unclear`, blocks the application gate and provides one bounded next task

### Requirement: Bidirectional quote verification
Repair of an incomplete citation MUST verify the claim against the source, the source against the claim and the quote against the exact page or paragraph on the same identified document version.

#### Scenario: Reacquired complete context
- **WHEN** the missing context is reacquired for the identified act
- **THEN** the repair task checks `claim→source`, `source→claim`, `quote→page`, speaker role, causal linkage and independent grounds before rerunning classification
