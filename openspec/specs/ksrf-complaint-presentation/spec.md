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

### Requirement: Substantive court-facing citations
Complaint drafting SHALL connect each material constitutional proposition supported by case law to an adjacent verified KSRF act and explain how that proposition applies to the challenged normative mechanism. The citation SHALL identify the act's date, number and precise numbered point or, where no numbering exists, a precise page and paragraph locator. The document SHALL follow one coherent convention for short exact quotations, parenthetical citations or footnotes. Citation volume SHALL NOT substitute for reasoning.

The attributed judicial holding SHALL be verified against the full text, source and exact locator. Party submissions, separate opinions and applicant analogies SHALL NOT be presented as the Court's holding. The substantive limits of a transferred proposition SHALL remain explicit in ordinary legal prose. Supreme Court positions SHALL be attributed separately. Internal evidence identifiers, verification logs and risk notes SHALL remain in the companion Markdown report, without changing unknown states or filing readiness.

#### Scenario: Direct KSRF authority supports a constitutional proposition
- **WHEN** a material proposition relies on a verified KSRF holding
- **THEN** the complaint places the precise citation beside that proposition and explains its relevance to the normative mechanism rather than listing decisions decoratively.

#### Scenario: Analogy from another legal context
- **WHEN** a verified act concerns a different legal context
- **THEN** the complaint accurately states the Court's limited proposition and presents its proposed transfer as the applicant's reasoning, without attributing the new conclusion to the Court.

#### Scenario: Unnumbered passage and quoted party submission
- **WHEN** the relevant text has no numbered point or records an argument made by a party
- **THEN** the citation uses an accurate alternative locator without invented numbering, and the text preserves the speaker rather than presenting the submission as a holding.

#### Scenario: Supreme Court source and internal review metadata
- **WHEN** the argument uses Supreme Court guidance and internal evidence records
- **THEN** the complaint separately names the Supreme Court and uses conventional legal citations while technical IDs, source checks and risks remain in the Markdown review.
