# ksrf-archived-submission-methods Specification

## Purpose
Preserve the provenance and distinct roles of recovered submissions while transferring bounded, independently checkable source-comparison and proportionality methods into the canonical KSRF skills.
## Requirements
### Requirement: Preserve archived source provenance and versions
The skillset SHALL identify the original publisher separately from the archive, preserve the original URL and specific archived snapshot, and distinguish capture date from document date. A matching hash SHALL NOT establish authorship, filing, court reliance or substantive truth.

#### Scenario: Archived explanation is recovered
- **WHEN** an unavailable original is recovered through the Wayback Machine
- **THEN** public attribution names the original publisher and explicitly identifies the archived copy as the access route

#### Scenario: Publisher and Court copies differ
- **WHEN** two versions have similar content but different files or redactions
- **THEN** their versions and verified roles remain distinct and they are not counted as independent supporting sources

### Requirement: Compare competing submissions without importing their desired outcome
The skillset SHALL distinguish party submissions, institutional opinions, majority holdings and separate opinions, and compare the legal question, right holder, procedural standing, remedy recipient and implementation mechanism before transferring an argument.

#### Scenario: Argument relies on a predecessor or shareholder
- **WHEN** a submission connects a company, shareholder or successor to the same dispute
- **THEN** the analysis requires an independent legal basis for each transfer of rights, standing or relief

#### Scenario: Historical execution proposal is reused
- **WHEN** an expert proposes a way to execute an international judgment
- **THEN** the proposal is checked against the exact majority outcome and current applicable law rather than presented as an adopted or presently available procedure

#### Scenario: Court expressly leaves an issue unresolved
- **WHEN** the Court declines to examine an argument or considers a question unnecessary to resolve
- **THEN** the analysis records that question as unresolved, not as adopted or rejected merely because the overall outcome matches one expert's proposal

### Requirement: Transfer proportionality doctrine within its verified scope
The skillset SHALL label doctrinal propositions and distinguish the legitimate aim, suitability, necessity and balancing questions, including the difference between excessive interference and insufficient protection. It SHALL NOT invent numerical weights, legal burdens or mandatory Court procedures from a scholarly model.

#### Scenario: Alternative is less restrictive but serves a different goal
- **WHEN** a proposed alternative reduces harm by abandoning the protected goal
- **THEN** the comparison does not establish lack of necessity

#### Scenario: Social protection is alleged to be inadequate
- **WHEN** the complaint concerns a positive duty rather than an excessive restriction
- **THEN** the analysis identifies the legal duty, protection deficit and competent remedy instead of mechanically reversing the interference test

### Requirement: Maintain private-source-independent validation
Public methods SHALL contain no original documents or reconstructive extracts. New evaluation cases SHALL be synthetic and self-contained. Structural validation SHALL NOT be reported as an executed LLM calibration or improved success rate.

#### Scenario: User has no source PDFs
- **WHEN** a user applies the installed methods or a synthetic scenario
- **THEN** no private file, OCR or hidden reference answer is required
