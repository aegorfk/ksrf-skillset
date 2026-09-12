## ADDED Requirements
### Requirement: Directory-compatible skills-only package
The system SHALL validate the final applicant package against locally checkable
skills-only directory requirements and preserve its complete runtime contents.
#### Scenario: Listing and images
- **WHEN** a release is prepared for directory upload
- **THEN** display name and subtitle meet documented limits, packaged logo and composer icon resolve safely to square assets, and all 16 skills remain present
#### Scenario: Unsafe branding asset
- **WHEN** an icon contains scripts, external resource references or invalid geometry
- **THEN** packaging rejects it before creating a distribution
### Requirement: Reproducible reviewer materials
The system SHALL provide synthetic positive and negative scenarios that reviewers
can reproduce without private records and SHALL separate expectations from observed results.
#### Scenario: Legal document review
- **WHEN** a reviewer opens the test materials
- **THEN** they receive five positive and three negative scenarios, fixtures, expected output shape and truthful execution status
### Requirement: Accurate portal status
The submission workflow SHALL distinguish package preparation, identity access,
upload, review submission, approval and public publication.
#### Scenario: Unverified publisher
- **WHEN** the official portal requires verified identity before draft creation
- **THEN** independent package work continues, the publisher is asked to complete verification, and no draft or submission is claimed
