# ksrf-working-draft Specification

## Purpose
TBD - created by archiving change implement-practical-admission-route. Update Purpose after archive.
## Requirements
### Requirement: Provisional local draft
The runtime SHALL create a visibly provisional DOCX/PDF and review-gap report without host release authority when the caller explicitly requests a working draft.

#### Scenario: Missing legal evidence or host integration
- **WHEN** structurally valid draft input contains unresolved evidence and no host verifier
- **THEN** the runtime preserves those uncertainties, creates a marked working draft and never claims filing readiness.

### Requirement: Separate artifact authority
The working draft SHALL use its own manifest and false filing/approval authority flags and SHALL NOT be accepted as a release manifest.

#### Scenario: Provisional manifest presented to release verification
- **WHEN** a caller supplies a working-draft manifest as a final release
- **THEN** verification rejects the artifact and no approval or filing event is created.

### Requirement: Accurate diagnostics and freshness
The runtime SHALL distinguish input, evidence/authority, conversion and QA failures and SHALL recheck draft artifact hashes before reporting current availability.

#### Scenario: Missing trusted index in strict render
- **WHEN** strict render cannot resolve a required host index
- **THEN** the diagnostic names the missing authority and does not recommend reinstalling a converter.

#### Scenario: Draft artifact modified
- **WHEN** a persisted working draft file changes or disappears
- **THEN** status reports that the saved draft is no longer verified against its manifest.

