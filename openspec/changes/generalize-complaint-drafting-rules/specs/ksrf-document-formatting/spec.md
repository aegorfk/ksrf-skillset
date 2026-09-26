## ADDED Requirements

### Requirement: Matter-independent drafting rules
Drafting skills SHALL express reusable methods without dependence on a named person, private example, case identifier or predetermined case outcome. Matter facts, challenged provisions, authorities and requests SHALL be established for the current matter. Verified public citations MAY retain necessary attribution in their source role without becoming behavioral defaults.

#### Scenario: Reusing a complaint as a style reference
- **WHEN** a supplied complaint informs a reusable style rule
- **THEN** only the general method or formatting rule is retained and no personal data, case facts, copied substantive conclusions or required exemplar dependency enter the skill

### Requirement: Variable request set
Drafting instructions SHALL use consecutive literal numbering for the selected requests without imposing a fixed count. Reopening SHALL be included only when selected and legally applicable. Authority paragraphs SHALL match the body typography under the chosen formatting standard.

#### Scenario: Complaint has no reopening request
- **WHEN** the supported selected request set contains one or three requests without reopening
- **THEN** drafting and rendering preserve that set without inventing a second request or removing an existing request

### Requirement: Individual and collective prayer markers
The renderer SHALL recognize standalone «ПРОШУ» and «ПРОСИМ» case-insensitively with an optional colon, preserve the authored marker and avoid a duplicate default marker. It SHALL NOT infer applicant count or recognize a marker word embedded in substantive prose as a standalone marker.

#### Scenario: Collective complaint supplies its marker
- **WHEN** the authored request section begins with «ПРОСИМ:»
- **THEN** it is centered using the prayer style and no «ПРОШУ:» is inserted

#### Scenario: Marker word is part of a sentence
- **WHEN** a substantive request contains «просим» within the sentence
- **THEN** its original content and role are preserved and it is not treated as the standalone marker
