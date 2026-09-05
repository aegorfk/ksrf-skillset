# Universal methods

## ADDED Requirements

### Requirement: Corpus-free hypothesis construction
The skill SHALL construct conditional constitutional issue candidates using
only the provided case and embedded methodology without requiring a source
corpus, vector index, court-result lookup or known target decision.

#### Scenario: No precedent database
- **WHEN** a new case is supplied without a corpus or network
- **THEN** the skill produces reasoned hypotheses and unknowns
- **AND** it does not request the training corpus as a prerequisite

### Requirement: Bidirectional transferable reasoning
Each method SHALL expose an inference, applicability conditions, a serious
counterargument, distinguishing evidence and a limit on the conclusion.

#### Scenario: Decisive fact changes
- **WHEN** a synthetic case changes a fact that supported the inference
- **THEN** the analysis narrows, rejects or reopens that inference
- **AND** it does not preserve the same conclusion through generic rhetoric

### Requirement: Evidence and temporal isolation
Runtime checks SHALL distinguish literal source support from semantic truth
and SHALL deny historical use of this evaluator-derived release.

#### Scenario: Later outcome supplied as evidence
- **WHEN** a document has a prohibited outcome role or a date beyond as-of
- **THEN** it cannot support the prediction candidate
- **AND** missing metadata remains an explicit uncertainty

### Requirement: Independent forward test
Complex skill changes SHALL receive corpus-free behavioral tests with only
new synthetic cases and the skill package, without the expected answer.

#### Scenario: Portable installation
- **WHEN** the package is copied to an isolated directory without corpus data
- **THEN** its method and validation workflows run using only local inputs
