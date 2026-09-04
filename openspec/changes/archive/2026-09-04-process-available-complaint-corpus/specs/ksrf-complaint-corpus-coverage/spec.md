## ADDED Requirements

### Requirement: Available complaint coverage preserves source roles

The processing workflow MUST inventory available complaint files and distinguish full actual complaints, fragments, educational pleadings, supplements, other-forum applications and byte-identical duplicates. A filename or previous mention alone MUST NOT establish completed analysis. Unreadable pages and unverified outcomes MUST remain explicit gaps.

#### Scenario: Fragment or moot complaint is encountered
- **WHEN** an uploaded document is an extract or an educational pleading
- **THEN** the method records the actual scope and does not invent a complete complaint or a real court outcome

#### Scenario: Duplicate and revision are encountered
- **WHEN** files have matching hashes or distinct versions of a common matter
- **THEN** identical content reuses its verified analysis while differing content receives a separate delta check

### Requirement: Complaint-derived methods are source-bound and non-predictive

Each added method MUST distinguish initial allegations, application evidence, constitutional mechanism, alternative explanations, requested remedy and the exact later holding when verified. Joined applicants MUST retain independent facts. Public source, donor and act links MUST keep their distinct roles and representative attribution MUST be supported.

#### Scenario: Official text cannot be verified
- **WHEN** only a donor account, mirror or search hit is available
- **THEN** the outcome remains qualified and is not promoted into an official authority finding

#### Scenario: Retrospective analysis is added
- **WHEN** the outcome was known during analysis
- **THEN** the result is not presented as blind evaluation, predictive accuracy or filing authority

### Requirement: Public derivatives and eval do not expose originals

Public payloads MUST exclude originals, images, full OCR, local source paths and reconstructive derivatives. Synthetic source-only eval cases MUST be self-contained without historical source documents and excluded from runtime installation. Methods MUST still require the new matter's own primary evidence and human choice.

#### Scenario: New user lacks the old complaint
- **WHEN** the installed method is applied to a new matter
- **THEN** historical private files are unnecessary but the new matter's evidence and ordinary gates remain mandatory
