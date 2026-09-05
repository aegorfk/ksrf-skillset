# ksrf-source-outcome-comparison Specification

## Purpose
Provide source-role-aware methods for comparing complaints and institutional opinions with independently verified court outcomes, while preserving uncertainty, private-source protection and self-contained evaluation.
## Requirements
### Requirement: Preserve source roles and relation uncertainty
The skillset SHALL distinguish complaints, supplements, intake reviews, institutional opinions, opposing responses, majority holdings and separate opinions; it SHALL NOT infer author, filing or case outcome from a filename, donation, redaction or topic match.

#### Scenario: Anonymous complaint has only a topical match
- **WHEN** a template omits applicant and signature and a similar decision is found
- **THEN** the relationship remains unverified and independent methodological review continues

#### Scenario: An institutional opinion conflicts with a judgment
- **WHEN** an expert proposes one interpretation and the Court resolves the case differently
- **THEN** the proposal and holding remain separate, with the latter's actual scope and locator

### Requirement: Compare obstacles rather than copy desired outcomes
The skillset SHALL compare each contested norm, affected interest, causal obstacle, counterargument and requested remedy before transferring a technique.

#### Scenario: Additional educational benefit is refused
- **WHEN** a claimant invokes equality without accounting for who funds the additional benefit
- **THEN** the analysis separates access to education from employer-funded guarantees and checks comparability and contractual protection

#### Scenario: Procedural exclusion is alleged
- **WHEN** a party treats silence about copying or lack of a hearing as a total denial of defence
- **THEN** the analysis checks the effective access, written response, relevant facts, actual normative prohibition and alternative explanation

#### Scenario: Legislative uncertainty spreads to a sanction
- **WHEN** a sanction refers to duties defined in several statutes
- **THEN** the analysis reconstructs the complete duty and limits the proposed remedy to the uncertainty actually affecting the case

### Requirement: Private-source-independent validation and publication
New evaluation scenarios SHALL be synthetic, self-contained and free of original documents, and publication SHALL contain only non-reconstructive methods, attribution and external source links.

#### Scenario: Installation without complaints
- **WHEN** the skillset is installed in an empty isolated directory
- **THEN** both methodological references are reachable without private files and evaluation scenarios require no files

#### Scenario: Structural tests pass
- **WHEN** the deterministic regression suite succeeds
- **THEN** the release reports structural validation without claiming improved admission rates or an executed LLM calibration
