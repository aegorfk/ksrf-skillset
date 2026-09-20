# complaint-header-layout Specification

## Purpose

Define a readable complaint header whose left boundary follows the usable text-area midpoint, with explicit visual QA and a clear distinction between document conventions and legal admissibility.
## Requirements
### Requirement: Readable layout and scoped QA
The methodology SHALL use the named KSRF Complaint Header paragraph style, Times New Roman 11.5 pt and single line spacing, and SHALL require visual confirmation after DOCX/PDF conversion. This is a document convention rather than an independent legal admissibility requirement.

#### Scenario: Long details wrap
- **WHEN** a header detail exceeds one line
- **THEN** the line wraps to the same left boundary without further reducing the header font size, and visual QA checks wrapping, clipping and geometry.

#### Scenario: Visual check unavailable
- **WHEN** final page images have not been inspected
- **THEN** the separate review records that visual verification remains incomplete instead of inferring it from paragraph settings or a successful export.

### Requirement: Text-area midpoint and left-aligned block
The complaint methodology SHALL place the header in the right half of the usable text width with left-aligned lines and zero first-line indentation. A representative SHALL appear only upon the user’s express instruction. An expressly requested alternative layout takes precedence.

#### Scenario: A4 with the unified margins
- **WHEN** an A4 page is 21 cm wide with a 2.5 cm left margin and a 2 cm right margin
- **THEN** the header left indent is 8.25 cm relative to the left margin, half the 16.5 cm usable width; its physical start is 10.75 cm from the sheet’s left edge.
