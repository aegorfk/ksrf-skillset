# Transferable argument methods

## ADDED Requirements

### Requirement: Evidence-bound transfer
The skill SHALL compare mechanisms, necessary conditions and defeating cases,
not infer transferability from lexical similarity or a matching legal topic.

#### Scenario: Missing premise
- **WHEN** a necessary condition has no evidence-bound value
- **THEN** the skill returns needs_evidence and the missing condition

### Requirement: No retrospective release
The skill SHALL preserve evaluator-derived lineage and deny historical EVAL use
of this release, including case-anonymized versions.

#### Scenario: Anonymized method
- **WHEN** a card no longer contains target identifiers
- **THEN** its evaluator-derived status still blocks historical use
