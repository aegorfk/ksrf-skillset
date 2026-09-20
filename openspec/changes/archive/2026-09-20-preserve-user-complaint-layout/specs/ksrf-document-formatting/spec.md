## ADDED Requirements

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
