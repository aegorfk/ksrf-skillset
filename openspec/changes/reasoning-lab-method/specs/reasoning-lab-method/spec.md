# Reasoning lab method

## ADDED Requirements

### Requirement: Autonomous substantive reasoning review
The skill SHALL support targeted questions, contrastive conditions, reasoned
formulation comparison and source-bound trajectories without the research corpus.

#### Scenario: Decisive fact is missing
- WHEN two conditional branches depend on an unknown fact
- THEN the skill asks for the relevant evidence and preserves both branches.

#### Scenario: A material condition changes
- WHEN the adverse condition is established instead of the supporting condition
- THEN the skill explains the resulting narrowing or withdrawal of the hypothesis.

### Requirement: Preserve epistemic and temporal boundaries
The skill SHALL distinguish source support, attribution and version availability,
and SHALL NOT turn studied families into independent historical evaluation.

#### Scenario: An earlier event is described by a later decision
- WHEN the source became available only after the cutoff
- THEN the event date does not make the later description an eligible earlier input.

### Requirement: Proportionate output and no promotion by checklists
The skill SHALL prioritize substantive decision criteria over fixed counts,
and SHALL distinguish agent preference from human review and training approval.

#### Scenario: Complete schema contains an overbroad remedy
- WHEN the requested consequence exceeds the grounded premise
- THEN the critic identifies the excess despite structural completeness.
