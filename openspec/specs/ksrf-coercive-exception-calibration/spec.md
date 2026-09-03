# ksrf-coercive-exception-calibration Specification

## Purpose
TBD - created by archiving change integrate-44p-coercive-exception-method. Update Purpose after archive.
## Requirements
### Requirement: Private complaint remains outside the public skillset
The workflow MUST derive only a non-reconstructive method card from the private complaint and MUST NOT add the original document, OCR, extracted full text, attachments, page images, or local source path to the public repository.

#### Scenario: Calibration from the Karimov complaint
- **WHEN** the private complaint is used to improve the KSRF skills
- **THEN** the public result contains only a provenance hash, bounded method findings, synthetic eval input, authorized professional attribution, and official outcome links

### Requirement: General proportionality rule and conduct-based exception are tested separately
The workflow MUST identify the ordinary relationship between the severity of a coercive measure and the possible punishment, then separately test whether the governing norm creates an exception with an independent procedural purpose, a verified conduct trigger, countervailing constitutional interests, and residual safeguards.

#### Scenario: Imprisonment is unavailable but the person allegedly absconded
- **WHEN** a complaint argues that pre-trial detention cannot exceed the custodial punishment legally available for the charged offence
- **THEN** the workflow tests both the ordinary punishment comparator and the competing hypothesis that intentional obstruction of justice supports a distinct necessary and temporary coercive response

### Requirement: Search status does not prove concealment or automatic detention
The workflow MUST distinguish an accusation or search entry from intentional active conduct making the person's location unknown and MUST separately test necessity, evidence, less restrictive measures, statutory blockers, and individualized judicial reasons.

#### Scenario: Only a search decision is shown
- **WHEN** the record establishes that the person was declared wanted but does not establish intentional active concealment
- **THEN** the exception hypothesis remains blocked and detention cannot be treated as automatic

#### Scenario: Concealment is established
- **WHEN** verified facts show intentional active concealment from the investigation or court
- **THEN** the workflow still requires an individualized necessity and proportionality analysis before treating detention as constitutionally permissible

### Requirement: Interpretive authority is time-versioned
The workflow MUST record the date and relevant version of statutory provisions, plenary resolutions, and other interpretive sources, and MUST NOT attribute a later clarification to an earlier court decision without an explicit temporal analysis.

#### Scenario: Plenary wording postdates the challenged decision
- **WHEN** a relied-on plenary formula was introduced after the lower-court act
- **THEN** it may be used to show later practice or present uncertainty but not as proof that the earlier court ignored an already existing formulation

### Requirement: Constitutional counterweights and individual outcome remain separate
The workflow MUST map the applicant's liberty interests against the rights of victims, access to justice, reasonable-time interests, and the public purpose of the proceedings, while separately recording admissibility, constitutional meaning, termination, review, set-off, and compensation outcomes.

#### Scenario: The Constitutional Court resolves uncertainty without ordering review
- **WHEN** a final act identifies a generally binding constitutional meaning but expressly denies review or compensation to the applicant
- **THEN** the method card records the systemic result and the individual result separately and does not label the complaint an individual victory

### Requirement: Public attribution follows the participants' requested wording
The public documentation MUST identify N.N. Karimov and state that Timur Chelokhsaev and Vitaly Katsko of the Krasnodar Region Law Office "Sila Slova" participated in work on the complaint and case, with active professional links and the official final act, while clearly marking the complaint source as private.

#### Scenario: Exact public complaint URL is unavailable
- **WHEN** participation is authorized for public credit but no public page containing the exact complaint text is verified
- **THEN** the documentation links the two lawyer profiles, the law office, and the official act, states that the source is private, and does not present any professional page as a complaint source

### Requirement: Public regression does not depend on the complaint file
The public eval MUST use a synthetic self-contained prompt preserving the punishment comparator, conduct-based exception, temporal-source conflict, countervailing rights, nonautomaticity, and remedy separation without reproducing the complaint or revealing the later outcome.

#### Scenario: User installs only the public skillset
- **WHEN** the original complaint is unavailable
- **THEN** the eval still checks alternative-hypothesis generation, temporal authority, trigger proof, proportionality safeguards, and separation of systemic from individual outcomes
