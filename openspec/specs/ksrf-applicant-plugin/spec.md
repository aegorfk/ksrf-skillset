# ksrf-applicant-plugin Specification

## Purpose
TBD - created by archiving change package-ksrf-applicant-plugin. Update Purpose after archive.
## Requirements
### Requirement: Full portable distribution
The system SHALL build a plugin containing every runtime file selected by the canonical skillset contract and its comparative dependency, with a deterministic integrity inventory, license and source provenance.
#### Scenario: Clean user package
- **WHEN** a fresh user receives the plugin
- **THEN** all 16 skills and their executable runtime, references and schemas are available without the author's filesystem or credentials
#### Scenario: Unsafe source
- **WHEN** a source contains a symlink, secret or excluded private/runtime material
- **THEN** the build rejects unsafe inclusion and does not publish a misleading complete artifact

### Requirement: Applicant-first full journey
The assistant SHALL accept ordinary language and available files, choose specialist routes itself, preserve originals and explain findings, uncertainty, proposed text and next human action in plain Russian.
#### Scenario: Incomplete materials
- **WHEN** a user provides a story or an incomplete dossier
- **THEN** the assistant completes independent analysis and a clearly labelled working draft where useful, and asks only for missing facts or documents that affect the next decision
#### Scenario: Existing draft or court communication
- **WHEN** the input is a draft, Secretariat notice or KSRF decision
- **THEN** the assistant selects QA/correction/execution as appropriate and does not equate these distinct stages
#### Scenario: Complete scope
- **WHEN** the user's need spans admissibility, exhaustion, arguments, practice, doctrine, comparative research, drafting, review, court request or execution
- **THEN** the route catalog reaches all packaged specialist skills

### Requirement: Isolated executable environment
The plugin SHALL offer an external isolated Python environment, actual operation-specific diagnostics and a reproducible environment definition, delegating legal work to the existing runtime.
#### Scenario: Minimal host
- **WHEN** external services and optional system programs are absent
- **THEN** diagnostics name affected operations while basic source-grounded analysis remains available
#### Scenario: Dependency setup
- **WHEN** the user or authorized host prepares document dependencies
- **THEN** installation targets an isolated environment outside the plugin, does not overwrite dossiers or credentials, and reports failures truthfully

### Requirement: Honest browser and desktop support
The system SHALL provide web-compatible and desktop distribution paths with explicit capability and setup instructions.
#### Scenario: Browser without runtime
- **WHEN** ChatGPT cannot execute bundled files or access a local connector
- **THEN** the assistant uses available document and web tools, reports the concrete missing operation and does not claim local runtime or export execution
#### Scenario: Desktop environment
- **WHEN** a supported desktop host provides Python and configured document tools
- **THEN** the same package can execute diagnostics, dossier operations, extraction and working export

### Requirement: Human authority and private data
The plugin SHALL preserve provenance, unknown states, release checks and human-only legal approval, signature, payment and filing, and SHALL not include the author's private documents or service access.
#### Scenario: No trusted verifier
- **WHEN** a user requests a filing-ready result without verified human authority
- **THEN** analysis and a labelled working draft remain possible but no machine-generated approval or filing status is substituted
#### Scenario: External service
- **WHEN** an optional provider is used
- **THEN** access belongs to the current user and private transfer follows their concrete authorization

### Requirement: Verified release
The system SHALL validate packaged links, integrity and clean runtime behavior, publish the canonical scoped source and exact distribution artifacts, and distinguish tests, installation, hosting and catalog approval.
#### Scenario: Software checks pass
- **WHEN** synthetic installation and workflow checks pass
- **THEN** release reports only the demonstrated software scope and retains account/hosting/legal checks as separate states

