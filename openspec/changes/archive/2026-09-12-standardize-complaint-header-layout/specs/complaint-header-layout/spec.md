# Complaint header layout

## ADDED Requirements

### Requirement: Physical midpoint and left-aligned block
The complaint document methodology SHALL place the addressee, applicant and representative block near the physical page midpoint, with left-aligned lines inside the right half and zero first-line indentation, unless the user explicitly requests another layout.

#### Scenario: A4 with equal margins
- WHEN an A4 page is 21 cm wide and both side margins are 2.5 cm
- THEN the block starts approximately 10.5 cm from the sheet's left edge, using an 8 cm left paragraph indent and an 8 cm available block width.

#### Scenario: Unequal margins
- WHEN an A4 page has a 3 cm left margin and a 2 cm right margin
- THEN the block still starts at approximately 10.5 cm from the sheet's left edge, with a 7.5 cm left indent and an 8.5 cm available width; the text-area midpoint is not substituted.

### Requirement: Readable layout and scoped QA
The methodology SHALL position the block through paragraph layout rather than padding spaces, preserve the ordinary font size, and require visual confirmation after DOCX/PDF conversion. It SHALL identify this as a document convention rather than an independent legal admissibility requirement.

#### Scenario: Long details wrap
- WHEN an address or representative detail exceeds one line
- THEN the line wraps to the same left boundary without reducing the font size, and visual QA checks wrapping, clipping and the block geometry in the final artifact.

#### Scenario: Visual check unavailable
- WHEN final page images have not been inspected
- THEN the review records that visual verification remains incomplete instead of inferring it from paragraph settings or a successful export.
