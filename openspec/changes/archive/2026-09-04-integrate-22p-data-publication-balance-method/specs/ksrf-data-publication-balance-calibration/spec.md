## ADDED Requirements

### Requirement: Data-publication conflicts use a decomposed balance matrix

The skillset SHALL require a `DataPublicationBalanceMatrix` that separately records the publisher or platform status and legal basis, exact data categories, lawful source and disclosure basis, publication purpose, professional/private boundary, content type, moderation trigger, interim response, final response, systematic-abuse evidence, countervailing rights, and graduated remedy before treating a personal-data publication conflict as drafting-ready.

#### Scenario: Public professional data are reused

- **WHEN** professional data were lawfully published before the disputed publication
- **THEN** the skillset treats lawful origin as one factor and still requires exact categories, purpose, status, scope, currentness, content type and countervailing-rights analysis instead of inferring unrestricted reuse

#### Scenario: A negative review is challenged

- **WHEN** a person requests deletion of a profile or all reviews because one item is allegedly false, insulting or unrelated to professional activity
- **THEN** the skillset separates the disputed item, its content class, verification and moderation steps from any platform-wide remedy

### Requirement: Remedies are graduated and evidence-bound

The skillset SHALL distinguish interim restriction or dispute marking, verification, correction, deletion of a specific item, rebuttal, and complete profile or review removal. The broadest remedy SHALL require evidence of systematic abuse or systematic moderation failure and a reason why lesser measures cannot protect the affected rights.

#### Scenario: Blanket removal is requested immediately

- **WHEN** the draft jumps from a disputed item directly to deletion of the entire profile and all reviews
- **THEN** QA blocks the request until narrower measures, systematic-abuse evidence, proportionality and both sides' rights are analyzed

### Requirement: Retrospective calibration remains source-separated

The installed skillset SHALL include a public-safe two-pass retrospective card for Constitutional Court Judgment No. 22-P/2021 and SHALL exclude the private complaint, full-text derivatives, scans, page images and local paths. The card SHALL identify public sources by role and SHALL NOT infer individual complaint authorship from a signature or document metadata alone.

#### Scenario: User has no private complaint source

- **WHEN** a user installs the public skillset without the historical complaint
- **THEN** the matrix, checklist and synthetic scenarios remain usable for a new matter while the historical source hash serves only as provenance for the published method card

### Requirement: Secondary professional materials remain non-authoritative

A practical guide or professional channel MAY contribute research questions and transfer cautions, but SHALL NOT establish current law, an official holding or complaint authorship without a separate primary source.

#### Scenario: Later case is described only in a practical guide

- **WHEN** the guide discusses a later determination whose official full text has not been verified
- **THEN** the item remains a research lead and does not enter the skillset as an authoritative substantive rule
