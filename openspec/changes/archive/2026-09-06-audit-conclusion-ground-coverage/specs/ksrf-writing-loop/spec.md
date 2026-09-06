## ADDED Requirements

### Requirement: Review conclusion coverage backward from exact targets
The methodology SHALL reconstruct support from material conclusions and each distinct requested result back to intermediate propositions, evidence and applicable legal anchors. It SHALL record the reviewed and pending scope, distinguish the speaker and role of each proposition, and keep unknown links explicit. Missing runtime dependencies SHALL NOT constitute verified independence or a complete review.

#### Scenario: Unlinked requested result
- **WHEN** a requested result has no declared dependency or argument card
- **THEN** the drafter checks its actual necessary support or records the unanswered question without inventing an edge or declaring the result defective solely for missing metadata

#### Scenario: Procedural request under a condition
- **WHEN** a document contains a procedural request conditional on a later stage
- **THEN** the review keeps its condition, recipient and procedural effect separate from the substantive requested result

### Requirement: Reconstruct surviving support without changing the record
After a material premise change, the methodology SHALL temporarily withhold that premise from the reasoning and examine remaining source-bound chains. It SHALL distinguish cumulative support, alternative sufficient grounds, conditional reasoning and rebuttal of an opponent. It SHALL check shared prerequisites and the exact scope of the conclusion and requested result. This review SHALL NOT establish the negation of a withheld proposition, silently change a selected demand or automatically close an objection.

#### Scenario: Remaining path depends on the same premise
- **WHEN** a proposed substitute ground depends on the withheld premise through another intermediate proposition
- **THEN** the review identifies the hidden shared prerequisite and does not declare independent support

#### Scenario: Separate conditional fallback
- **WHEN** the source supports a fallback only under an explicit assumption
- **THEN** the drafter preserves that conditional form and verifies its limited consequence without asserting contradictory facts simultaneously

#### Scenario: Opponent argument defeated
- **WHEN** the applicant refutes one opponent reason
- **THEN** the applicant's own positive support and requested result are reviewed separately rather than inferred from the refutation

### Requirement: Separate methodological review from runtime and legal authority
The instructions SHALL explain that an impact report lists affected paths rather than all surviving grounds, and that the methodological worksheet is not a new executable packet schema. They SHALL reuse current writing review bindings and preserve existing legal, privacy and human-approval boundaries. Publication evidence SHALL distinguish source review and technical checks from comparative legal-quality measurement.

#### Scenario: Impact context omits an unchanged supporting ground
- **WHEN** an impact report includes the changed path but omits a second supporting path
- **THEN** the reviewer returns to the full draft and source-bound cards before deciding what remains supported
