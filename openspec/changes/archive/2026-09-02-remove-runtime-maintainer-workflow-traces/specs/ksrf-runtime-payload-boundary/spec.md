## ADDED Requirements

### Requirement: Runtime payload omits maintainer change-management traces

Every runtime-eligible text file and its logical runtime path MUST be understandable without access to repository change-management workflow names or numbered maintainer task coordinates. Substantive artifact, negative/conflict-case, held-out evaluation, leakage, observability, provenance, and human-approval gates MUST remain expressed in plain user-facing language. The runtime validator MUST inspect every runtime-eligible logical path plus every normalized or strictly decoded text payload after the same source-only exclusions used by installation, MUST fail closed with stable code `RUNTIME_MAINTAINER_WORKFLOW_REFERENCE` when a maintainer workflow marker is present, and MUST expose only bounded marker classes, the affected runtime path, and no matched file content or source excerpt. Source-only specs, tests, evals, and exact paths classified source-only by the canonical installation contract MAY retain maintainer workflow coordinates because they MUST remain outside the installed payload.

#### Scenario: Exact installed payload contains no maintainer traces

- **WHEN** the canonical release payload is enumerated through the installation file contract
- **THEN** neither a logical runtime path nor its normalized or strictly decoded text contains a repository change-workflow name or numbered internal task coordinate

#### Scenario: Safety gates remain useful after wording cleanup

- **WHEN** a cleaned runtime guide describes a future implementation or evaluation
- **THEN** it still requires the applicable artifact contract, negative/conflict examples, held-out and leakage checks, reproducible tracing, and explicit human approval in language that does not require repository access

#### Scenario: Runtime workflow reference fails closed

- **WHEN** a runtime-eligible text file contains a maintainer change-workflow name, a dotted task coordinate with explicit `internal`/`maintainer`/`repository` context, or a `tasks.md` coordinate
- **THEN** validation fails with `RUNTIME_MAINTAINER_WORKFLOW_REFERENCE`, reports only bounded marker classes and the runtime path, and does not expose matched file content or a source excerpt

#### Scenario: External checkout name is not a runtime marker

- **WHEN** the physical checkout or installation root contains a maintainer marker but all logical runtime paths and content are clean
- **THEN** validation does not report a maintainer-workflow or local-coordinate finding for that external root

#### Scenario: Logical path is scanned before content decoding

- **WHEN** a logical runtime filename contains a maintainer marker, including when the file has a binary suffix or cannot be decoded as UTF-8
- **THEN** validation fails with `RUNTIME_MAINTAINER_WORKFLOW_REFERENCE` and reports that logical runtime path without exposing file content

#### Scenario: Ordinary user tasks and legal numbering are not maintainer traces

- **WHEN** a runtime file contains a bare user-facing `Task 5.1: ...`, statutory provisions, decimal values, numbered headings, dates, or dotted legal references without explicit maintainer context
- **THEN** the maintainer-workflow check does not reject that content

#### Scenario: Source-only evidence may retain maintainer coordinates

- **WHEN** an exact source-only spec, test, eval, or provenance file contains maintainer workflow coordinates
- **THEN** source validation may inspect that material under its existing contracts, while runtime validation and installation exclude it from the user payload

#### Scenario: Runtime provenance receives no blanket exemption

- **WHEN** a manifest-covered runtime guide or data file explains provenance and remains eligible for installation
- **THEN** its logical path and content receive the same maintainer-trace scan as every other runtime file
