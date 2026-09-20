## MODIFIED Requirements

### Requirement: Provisional local draft
The runtime SHALL create a court-facing DOCX/PDF and separate Markdown review report without host release authority when the caller requests a working draft. The document SHALL NOT contain generated draft notices, readiness statuses, risk assessments or sentence review IDs. Missing data SHALL remain explicit and highlighted.

#### Scenario: Missing legal evidence or host integration
- **WHEN** structurally valid input contains unresolved evidence and no host verifier
- **THEN** the runtime preserves those uncertainties in source records and the separate report, highlights missing data in the complaint and retains false filing readiness and authority.

### Requirement: Separate artifact authority
The working draft SHALL use its own manifest with `filing_ready=false` and false filing/approval/release authority flags and SHALL NOT be accepted as a release manifest. The companion Markdown report SHALL be covered by artifact hashes.

#### Scenario: Court-facing document mistaken for approval
- **WHEN** the document has no workflow watermark or review annotations
- **THEN** its manifest still states false readiness and authority and strict release gates remain unchanged.

#### Scenario: Provisional manifest presented to release verification
- **WHEN** a caller supplies a working-draft manifest as a final release
- **THEN** verification rejects the artifact and no approval or filing event is created.
