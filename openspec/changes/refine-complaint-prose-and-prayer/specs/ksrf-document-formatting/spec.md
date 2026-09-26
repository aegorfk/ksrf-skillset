## MODIFIED Requirements

### Requirement: Unified paragraph style standard
The complaint renderer and drafting instructions SHALL use A4 pages, 25 mm left and 20 mm other margins, 9 mm header/footer distances, Times New Roman in black with ru-RU language, and named paragraph styles. Normal SHALL use 12 pt, 1.15 line spacing, 6 pt after, a 10 mm first-line indent and justified alignment. Sources SHALL use the same typography as Normal while retaining their named style and source role. Title SHALL use 14 pt bold centered, single spacing, 12 pt before and 6 pt after; Subtitle 12 pt centered, single spacing and 12 pt after; level-one headings 13 pt bold, 1.1 spacing, 12 pt before and 6 pt after; level-two headings 12 pt bold, 1.1 spacing, 10 pt before and 6 pt after; complaint header 11.5 pt, single spacing and 4 pt after inside the right half of the usable width; footers 11 pt centered.

#### Scenario: Authority prose is part of the argument
- **WHEN** an authority paragraph is rendered
- **THEN** its typography matches the body paragraph and it retains its text, source block identity, sentence role and evidence bindings

### Requirement: Request marker and signature row
The drafting workflow SHALL place the author's verified legal basis for the requested exercise of Constitutional Court powers in section III before a separate bold centered prayer marker. The renderer SHALL place an optional author-supplied `request_basis` before the marker, preserve an existing standalone marker's capitalization, and supply `ПРОШУ:` only when none exists. It SHALL preserve the selected requests, their wording, literal numbering and order, followed by annexes. It SHALL NOT invent legal grounds, choose requests or rewrite legal meaning. The drafting workflow SHALL use a stable date/signature row with date left and an unfilled signature place plus the confirmed signer's name right; it SHALL NOT invent a date or signature.

#### Scenario: Authored basis precedes selected requests
- **WHEN** a complaint supplies a legal basis and two numbered requests
- **THEN** section III contains the exact basis, a separate centered prayer marker, requests 1 and 2 in their original order, and then annexes

#### Scenario: Existing user choices survive presentation
- **WHEN** the user supplies a standalone lowercase prayer marker or a different number of requests
- **THEN** the renderer preserves that marker and request set without duplication, adding grounds or creating a missing request

## ADDED Requirements

### Requirement: Affirmative applicant position
The drafting workflow SHALL express section II's applicant arguments as affirmative propositions connecting the normative mechanism, verified constitutional rule, application and conclusion. Research questions SHALL remain in internal analysis. The renderer SHALL NOT rewrite questions into assertions or alter quoted judicial language automatically.

#### Scenario: Research question becomes an authored proposition
- **WHEN** an internal research question is developed into a court-facing argument
- **THEN** the author states the supported proposition affirmatively, verifies its scope and sources, and keeps unresolved research questions outside the complaint
