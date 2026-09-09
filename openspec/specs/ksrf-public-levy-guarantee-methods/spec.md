# ksrf-public-levy-guarantee-methods Specification

## Purpose
TBD - created by archiving change add-public-levy-guarantee-methods. Update Purpose after archive.
## Requirements
### Requirement: Independent guarantee analysis
The methodology MUST separate the classification and purpose of a public levy from each required safeguard and MUST NOT infer exclusion of a safeguard solely from statutory silence or a disputed label.

#### Scenario: Compensatory label does not resolve safeguards
- **WHEN** a levy is described as compensatory rather than administrative
- **THEN** the workflow separately checks guilt, burden of proof, individual amount, time limits and the applicable legal basis without automatically importing the whole administrative code

#### Scenario: Different stages have different time limits
- **WHEN** experts propose time limits for imposing, challenging or enforcing a measure
- **THEN** the workflow preserves the event, actor, procedural action and authority of each proposal and requires current-law verification

### Requirement: Actor-separated source comparison
The methodology MUST distinguish the donor, complaint author, representative, signatory, expert author, approving official and forwarding person, and MUST compare expert positions by issue rather than count documents as votes.

#### Scenario: An institutional cover does not identify the author
- **WHEN** an opinion is approved by one official and signed by another author
- **THEN** both roles remain distinct and the cover signature does not overwrite authorship

#### Scenario: Experts disagree with the Court
- **WHEN** an expert rejects guilt or proposes joint liability while the Court requires individual safeguards
- **THEN** the expert view is preserved as a competing position and is not promoted to the Court holding

### Requirement: Two-pass transfer and conditional review
The skillset MUST provide an independent first pass and a separate retrospective pass and MUST distinguish an authoritative interpretation from the concrete ground, procedure and result of reopening.

#### Scenario: A request for clarification disguises an appeal
- **WHEN** the disposition is clear but the applicant contests an ordinary court's refusal to reopen
- **THEN** the workflow identifies the precise alleged interpretive divergence and does not promise that clarification will reverse the refusal

### Requirement: Private originals and portable validation
The release MUST exclude originals, OCR and reconstructive derivatives while preserving public attribution links and self-contained synthetic tests.

#### Scenario: User has no source complaints
- **WHEN** a user runs the supplied scenarios without private documents
- **THEN** the prompts contain the necessary fictional facts and do not require access to the originals or claim independent outcome-blind validation
