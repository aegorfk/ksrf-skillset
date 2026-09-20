# ksrf-document-formatting Specification

## Purpose
TBD - created by archiving change unify-complaint-document-formatting. Update Purpose after archive.
## Requirements
### Requirement: Unified paragraph style standard
The renderer SHALL use A4, margins 25 mm left and 20 mm elsewhere, 9 mm header/footer distances, Times New Roman black ru-RU, and normalized complex-script font/size properties. It SHALL apply named styles: Normal 12 pt/1.15/after 6 pt/first indent 10 mm; Title 14 pt bold centered/single/before 12/after 6; Subtitle 12 centered/single/after 12; heading level 1 at 13 bold/1.1/before 12/after 6 and level 2 at 12 bold/1.1/before 10/after 6. Headers use 11.5 pt/single/after 4 and half the usable width; sources use 11 pt/single/after 4/left; footers use 11 pt/center.

#### Scenario: Numbered annex item
- **WHEN** an annex item starts with a literal number
- **THEN** its number is retained followed by a tab, with a 6.5 mm hanging indent and left alignment; automatic list numbering is not substituted.

### Requirement: Formatting preserves substance
A formatting-only operation SHALL preserve legal wording, numbering, fields, links, evidence status and yellow highlights. It MAY normalize the separator after № to NBSP and after a literal item number to a tab. It SHALL NOT introduce arbitrary page breaks that create a mostly empty tail page.

#### Scenario: Existing adverse wording and unresolved field
- **WHEN** substantive text contains an adverse court finding and an explicit placeholder
- **THEN** the finding remains intact and the placeholder stays yellow while formatting changes do not modify source sentences or readiness flags.

### Requirement: Annex copy labels
The drafting methodology SHALL label actual copies of judicial acts and complaints as «Копия…» in the annex list. It SHALL NOT label the complaint original, fee document or newly prepared legal extracts as copies merely because they are included in the package.

#### Scenario: Mixed annex package
- **WHEN** the package includes court-act copies, the complaint original and prepared statutory extracts
- **THEN** copy labels reflect each document’s actual status and no content rewrite occurs during a formatting-only request.

### Requirement: Request marker and signature row
The editorial formatting workflow SHALL place the request marker in a separate bold centered paragraph, preserve the user's capitalization and retain the selected request count. It SHALL place the date left and the blank signature line and confirmed signatory name right on one stable row using fixed tab stops or a borderless table. It SHALL NOT fabricate a handwritten signature or signing date. Final DOCX/PDF review SHALL verify the arrangement; automatic renderer support is not asserted by this methodology requirement.

#### Scenario: Lowercase marker and long signatory name
- **WHEN** the user's edited document contains a lowercase request marker and a long confirmed signatory name
- **THEN** the editor retains capitalization, centers and bolds the marker, and adjusts stable row geometry within usable page width without synthesizing a signature.

### Requirement: Authorized numbering and annex reconciliation
The editorial workflow SHALL reconcile cited case records, annex entries and actual files by their identity and document status. When list-number correction is authorized, it SHALL remove gaps and duplicates in the complaint's own lists and update affected internal references while preserving external document numbers and source locators. A cited authority SHALL NOT automatically become an annex; deleted or excluded attachments SHALL NOT be restored merely to fill a numbering gap.

#### Scenario: Annex deletion leaves a numbering gap
- **WHEN** an authorized revision removes an annex and asks to repair numbering
- **THEN** the remaining entries are numbered consecutively, their file mapping and internal references are checked, and the removed annex is not recreated.

#### Scenario: Cited precedent is not included as an annex
- **WHEN** a precedent is cited for legal reasoning but has not been selected or required as an annex
- **THEN** the editor verifies its citation separately without adding a fictitious annex entry or asserting that an absent file is attached.
