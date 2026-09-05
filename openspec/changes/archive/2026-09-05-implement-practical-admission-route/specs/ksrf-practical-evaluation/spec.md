## ADDED Requirements

### Requirement: Separate research rejection from legal readiness
Evaluation SHALL report false rejection of researchable issues separately from false admission, technical completion and legal-review uncertainty.

#### Scenario: Missing optional infrastructure
- **WHEN** the record supports continued research but optional retrieval or host tools are unavailable
- **THEN** abandoning the issue solely for that reason counts as an avoidable research rejection, while withholding filing readiness does not.

### Requirement: Frozen and provenance-bound evaluation
Evaluation SHALL bind cases and assessment inputs to a frozen manifest and SHALL distinguish synthetic labels, automated judgments and actual human review.

#### Scenario: Missing human review or tracing
- **WHEN** an experiment lacks real human review or the required LLM trace/evaluation records
- **THEN** the report preserves that gap and does not claim promotion eligibility or a measured improvement in court acceptance.

### Requirement: Complete local rehearsal
The documented workflow SHALL support an installed-style CLI rehearsal from a local dossier to a provisional review package without test authority stubs.

#### Scenario: Real case still needs legal review
- **WHEN** local documents are used in a rehearsal and some legal criteria remain unresolved
- **THEN** the package records the source inventory, issue, application and deadline gaps, draft files and pending human decision without publishing private content.
