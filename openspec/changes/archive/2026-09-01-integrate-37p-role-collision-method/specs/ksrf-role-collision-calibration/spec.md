## ADDED Requirements

### Requirement: Private complaint source remains outside the public skillset
The workflow MUST derive only a non-reconstructive method card from the private complaint source and MUST NOT add the original document, OCR, extracted full text, page images, attachments, or local source path to the public repository.

#### Scenario: Calibration from a local complaint
- **WHEN** a private complaint is used to improve the KSRF skills
- **THEN** the public result contains only a provenance hash, bounded method findings, synthetic eval input, public professional attribution when authorized, and official outcome links

### Requirement: Sequential role collision is tested as a normative mechanism
The workflow MUST separately identify the earlier and later procedural roles, the statutory reference chain permitting or excluding the transition, the structural risk created by the combination, the evidence obtained in the later role, and the lower-court meaning that made the evidence usable.

#### Scenario: Witness later participates as specialist
- **WHEN** the same person was questioned as a factual witness and later supplies special-knowledge evidence in the same case
- **THEN** the workflow tests the exact recusal provisions and their incorporated norms, records the evidence and judicial response, and does not reduce the issue to credibility or weight of one witness

#### Scenario: No normative carrier is established
- **WHEN** the complaint shows only that a court trusted an allegedly biased participant but does not establish the governing norm or judicial meaning
- **THEN** the constitutional role-collision hypothesis remains blocked as ordinary appellate evidence criticism

### Requirement: Scope and remedy are narrower than the initial grievance when required
The workflow MUST decompose the challenged article into the applied provision and incorporated rules, distinguish procedure from grounds, and maintain a principal and a reserve remedy without assuming that invalidation of the entire article is necessary.

#### Scenario: Only one part governs the disputed transition
- **WHEN** one part of the article sets procedure and another part incorporates the grounds relevant to the role transition
- **THEN** the issue option narrows the subject to the applied part and treats the remaining text only according to its verified function

#### Scenario: Saving interpretation can remove the defect
- **WHEN** the statutory text can be read systemically to prohibit the incompatible role transition and exclude evidence obtained in breach of that rule
- **THEN** the portfolio presents that constitutional meaning as a distinct reserve remedy and keeps individual rehearing as a separate legal consequence

### Requirement: Outcome-blind regression does not depend on the complaint file
The public eval MUST use a synthetic self-contained prompt that preserves the role sequence, reference-chain ambiguity, lower-court meaning and remedy problem without reproducing the real complaint or revealing the later constitutional outcome.

#### Scenario: User installs only the public skillset
- **WHEN** the original complaint is unavailable
- **THEN** the eval still checks norm decomposition, role-collision framing, evidence consequence, anti-appeal discipline and principal/reserve remedy generation

### Requirement: Public attribution is explicit about missing complaint link
The public documentation MUST link the verified professional site of the credited author and the official final act, MUST state that the private source is not published, and MUST NOT present the professional site as a public copy of the complaint.

#### Scenario: Exact public complaint URL is unavailable
- **WHEN** authorship is explicitly authorized for public credit but no public page with the exact complaint text is verified
- **THEN** the documentation names the author with the professional link, marks the source as a private local original, links the official act, and does not claim that the complaint text is publicly accessible
