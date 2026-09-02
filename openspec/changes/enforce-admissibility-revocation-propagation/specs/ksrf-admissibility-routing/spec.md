## MODIFIED Requirements

### Requirement: Runtime route preserves human legal and filing control

The installed CLI MUST expose `ksrf admissibility validate|derive|status` in Russian, MUST perform no network or model call, and MUST persist through the existing content-addressed matter workflow ledger. Every derived `KSRFRouteRecommendation` MUST set `human_decision=pending`, `legal_assessment_automated=false`, `filing_authority=false` and `filing_performed=false`. Status MUST reload the previously persisted matrix, re-resolve official source identity and selected issue viability through their current native trusted-approval histories, and MUST NOT treat a cached recommendation or historical approval as current authority. Revocation of a required source-identity approval or selected issue approval after `GO_TO_KSRF` MUST produce a new blocked `ABSTAIN_PENDING_RECORD` status while preserving the exact bytes of every prior result object and workflow event.

#### Scenario: Recommendation is derived locally

- **WHEN** a user runs `ksrf admissibility derive --workspace ... --payload ...`
- **THEN** the command reads only local inputs, records exact hashes and returns a human-review planning artifact without external transmission or filing

#### Scenario: Status is requested

- **WHEN** a user runs `ksrf admissibility status` after a validation or derivation
- **THEN** the command reloads the latest persisted matrix, re-resolves current official authority, revalidates current issue approvals, re-derives the recommendation and appends a new status event without modifying the prior record

#### Scenario: Current source-identity approval is revoked after GO

- **WHEN** a prior recommendation was `GO_TO_KSRF` through real current official source evidence and the exact trusted approval supporting one required source identity is later revoked in the local approval ledger
- **THEN** the next status check reports `ABSTAIN_PENDING_RECORD`, identifies the affected official evidence and revoked current authority, exits blocked, preserves the prior result object and GO event byte-for-byte, and appends exactly one new status event

#### Scenario: Current issue-selection approval is revoked after GO

- **WHEN** a prior recommendation was `GO_TO_KSRF` through a persisted viable issue candidate and the exact trusted human-selection approval supporting that option is later revoked in the local approval ledger
- **THEN** the next status check reports `ABSTAIN_PENDING_RECORD`, identifies the affected option and current issue-binding blocker, exits blocked, preserves the prior result object and GO event byte-for-byte, and appends exactly one new status event

#### Scenario: Current authority is revoked after GO

- **WHEN** a prior recommendation was `GO_TO_KSRF` but a later status check cannot revalidate one of its official evidence IDs
- **THEN** status reports `ABSTAIN_PENDING_RECORD`, preserves the older event and exits as blocked

#### Scenario: Existing workspace is used

- **WHEN** the route runs in a workspace created before this capability existed
- **THEN** it works through the existing workflow event ledger and does not require rewriting `matter.json`

#### Scenario: Clean runtime is installed

- **WHEN** the source repository is installed through the runtime manifest
- **THEN** both schemas, the domain module, the CLI route and user guidance remain available without source-only `evals` or tests
