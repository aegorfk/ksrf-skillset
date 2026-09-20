# ksrf-complaint-presentation Specification

## Purpose
TBD - created by archiving change separate-complaint-presentation-from-review. Update Purpose after archive.
## Requirements
### Requirement: Court-facing macrostructure
Complaint generation SHALL use a formal header, the two-line title, factual circumstances with judicial stages, the applicant's constitutional reasoning, the request, enclosures and date/signature. Formal particulars SHALL be integrated into the header or introductory prose rather than exposed as twelve workflow headings. Legal analysis SHALL follow issue, rule, application and conclusion in substantive prose.

#### Scenario: Internal structured model has twelve sections
- **WHEN** the renderer receives the existing structured complaint model
- **THEN** it groups court-facing content into the complaint macrostructure and retains review-only content separately without discarding the source model.

### Requirement: Unknown data and representative choice
Missing data SHALL appear as explicit yellow-highlighted placeholders. Generation SHALL NOT fabricate missing facts, promote Unknown to a verified state, or invent a representative. A representative block SHALL be drafted only when the user expressly instructs representation.

#### Scenario: Unprovided address and no representative instruction
- **WHEN** the address is unknown and representation was not requested
- **THEN** the address placeholder is highlighted and no representative placeholder is introduced automatically.

### Requirement: Advocacy prose and separate review
The complaint SHALL state the applicant's position directly and positively, retain material adverse judicial findings accurately, and place workflow commentary, risk estimates and drafting self-analysis in the companion report. Canned disclaimers about what the applicant does not challenge or request SHALL NOT replace a concrete positive statement of the subject and requested remedy. Substantive negation of an unconstitutional legal meaning remains permitted.

#### Scenario: Adverse judicial finding and unresolved argument
- **WHEN** a court made an adverse finding and the draft's legal argument still requires review
- **THEN** the finding remains accurately stated in the complaint while the review status and risk remain in the separate report.

#### Scenario: Legacy section mixes judicial findings and workflow notes
- **WHEN** a substantive section contains a known workflow marker
- **THEN** export blocks with a separate diagnostic, preserving the complete source sentence for explicit editorial separation; it SHALL NOT silently delete adverse material or claim comprehensive semantic detection.

#### Scenario: Strict export carries explicit review notes
- **WHEN** a strict document export receives a review_notes section
- **THEN** it retains those notes in a separate Markdown artifact while the existing evidence, release and artifact-integrity gates continue to apply.
