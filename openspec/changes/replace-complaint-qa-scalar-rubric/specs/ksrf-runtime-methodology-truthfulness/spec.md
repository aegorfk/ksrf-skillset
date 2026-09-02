## ADDED Requirements

### Requirement: Complaint-QA argument quality remains non-compensating

Installed complaint-QA methodology MUST preserve its six argument-quality criteria and their positive, adverse, partial, and unresolved conditions as independent checks. It MUST NOT total, average, weight, or convert them into a principal/reserve selection, legal verdict, admissibility result, filing readiness, or expected outcome. A confirmed criterion MUST NOT compensate for a warning, insufficient data, or a failed or unknown canonical gate.

#### Scenario: Argument quality is checked

- **WHEN** the detailed QA workflow reviews an argument
- **THEN** each applicable criterion records `подтверждено`, `предупреждение`, or `недостаточно данных` with the supporting or missing material and without a numeric score

#### Scenario: A criterion is unresolved

- **WHEN** the available record cannot resolve a criterion
- **THEN** `недостаточно данных` creates a blocking collection or verification task for that argument and is not treated as partial credit, a warning, or a pass

#### Scenario: A genuinely new line has no claimed corpus pattern

- **WHEN** corpus support is not claimed and the direct official anchors have been checked
- **THEN** the corpus criterion records `подтверждено` without inventing a matching pattern or treating novelty as a defect

#### Scenario: Argument use is decided

- **WHEN** the workflow considers principal use, repair/support, auxiliary/rework, or removal
- **THEN** the decision follows the affected independent checks, separately passed canonical gates, and required human selection rather than a summed range

### Requirement: Complaint-QA scalar cleanup preserves substantive guidance

Removing the scalar rubric MUST NOT remove any of the six dimensions, eighteen baseline cell meanings, four practical actions, unrelated workflow guidance, table-of-contents route, payload membership, or consuming-skill backlink.

#### Scenario: Detailed workflow reference is projected

- **WHEN** the scalar section is replaced
- **THEN** the final reference preserves all approved content outside the target section and retains the full substance of the target criteria and actions

#### Scenario: Cleanup regressions pass

- **WHEN** full-reference, structure, payload, and backlink checks pass
- **THEN** the result proves only truthful non-scalar presentation and preservation, not legal correctness, admissibility, filing readiness, publication authority, or outcome prediction
