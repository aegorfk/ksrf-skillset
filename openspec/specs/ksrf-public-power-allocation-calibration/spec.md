# ksrf-public-power-allocation-calibration Specification

## Purpose
TBD - created by archiving change integrate-33p-public-power-allocation-method. Update Purpose after archive.
## Requirements
### Requirement: Provided complaint remains outside the public skillset
The workflow MUST derive only a non-reconstructive method card from the provided complaint and MUST NOT add the original PDF, extracted full text, page images, attachments, or local source path to the public repository.

#### Scenario: Calibration from the Kaliningrad administration complaint
- **WHEN** the complaint is used to improve the KSRF skills
- **THEN** the public result contains only a provenance hash, bounded method findings, synthetic eval input, an official applicant link, and the official final act

### Requirement: Public task and legal duty are not conflated
The workflow MUST identify the public task, object owner or user, power holder, legal basis, funding source, implementation mechanism, and rights effect before concluding which level of public authority bears a duty.

#### Scenario: Environmental harm exists on a federal water object
- **WHEN** the need to remove waste is established
- **THEN** the workflow does not infer a permanent municipal duty solely from territorial location, environmental importance, or general municipal powers

### Requirement: Own, delegated, and emergency duties are tested separately
The workflow MUST classify the alleged duty as an own municipal power, a delegated state power supported by law and transferred resources, or urgent participation that may generate a later reimbursement claim.

#### Scenario: Regular cleaning is imposed on a municipality
- **WHEN** the water object is federally owned and not granted for municipal use
- **THEN** a regular cleaning duty requires a valid delegation route and the transfer of necessary material and financial resources

#### Scenario: Immediate pollution removal is necessary
- **WHEN** unidentified waste accumulated in or near a populated area creates a need for immediate removal
- **THEN** the workflow tests urgent municipal participation separately and preserves a reimbursement route against the regional budget

### Requirement: Reimbursement and contributory municipal fault remain separate
The workflow MUST record actual expenses, urgency, the competent reimbursement payer, and the extent to which non-performance of the municipality's own waste, благоустройство, or accumulated-harm duties contributed to the pollution.

#### Scenario: Municipality seeks reimbursement after urgent cleanup
- **WHEN** the municipality proves qualifying expenses
- **THEN** reimbursement is not treated as automatic or necessarily full, and any reduction requires a reasoned causal assessment

### Requirement: Challenged provisions are reconciled across the complaint
The workflow MUST compare the exact provisions stated in the heading, subject section, application analysis, and prayer for relief and MUST block drafting readiness when an unexplained extra or missing provision appears.

#### Scenario: Subject section contains an additional provision
- **WHEN** a provision appears in the subject description but not in the heading or prayer
- **THEN** the workflow marks a norm-roster mismatch and requires correction or a supported explanation before release

### Requirement: Applied and successor regulation are time-versioned
The workflow MUST preserve the provision applied in the concrete case and separately map any functionally analogous successor rule without using the later rule as proof of earlier application.

#### Scenario: A challenged local-government provision was replaced after the case
- **WHEN** a later statute contains an analogous rule
- **THEN** the workflow records both versions and their dates, uses the applied version for admissibility and causal analysis, and uses the successor only for current-law and remedy review

### Requirement: Public attribution links the institutional applicant
The public documentation MUST identify the Administration of the City District "City of Kaliningrad" as the applicant and provide an active link to its official website together with the official KSRF act.

#### Scenario: Individual complaint author is not publicly verified
- **WHEN** only document metadata names an individual but the complaint does not contain a verifiable signature or public authorship statement
- **THEN** the documentation credits the institutional applicant and does not infer individual authorship

### Requirement: Public regression does not depend on the complaint file
The public eval MUST use a synthetic self-contained prompt preserving the three duty routes, funding, urgency, reimbursement, contributory fault, norm-roster reconciliation, and successor-law distinction without reproducing the complaint.

#### Scenario: User installs only the public skillset
- **WHEN** the original complaint is unavailable
- **THEN** the eval still checks power allocation, resource coverage, emergency participation, reimbursement, exact norm scope, temporal authority, and separation of systemic and individual outcomes
