## ADDED Requirements

### Requirement: Preservation status vocabulary has one machine source of truth

The skillset MUST treat `application-evidence.schema.json` as the canonical vocabulary for `ApplicationEvidenceRecord.preservation_exhaustion` and MUST publish the same complete ordered values in the normative `implicit-application-gate.md` list.

#### Scenario: Canonical reference matches schema

- **WHEN** the validator compares the normative reference list with `properties.preservation_exhaustion.enum`
- **THEN** every value and its order match exactly and the contract check passes

#### Scenario: Reference contains an alias or drift

- **WHEN** the reference omits, adds, duplicates, renames, or reorders a preservation status
- **THEN** validation fails with `APPLICATION_EVIDENCE_ENUM_DRIFT` and reports expected and actual values

### Requirement: Contract checking is scoped and fail closed

The validator MUST enforce the application-evidence enum contract for the canonical `ksrf-complaint-cycle` package, MUST report an invalid or missing schema/reference contract as an error, and MUST NOT require unrelated or synthetic packages to carry this schema.

#### Scenario: Unrelated package is validated

- **WHEN** validation runs for a package other than `ksrf-complaint-cycle`
- **THEN** application-evidence contract checking is skipped without weakening that package's existing checks

#### Scenario: Canonical contract cannot be read

- **WHEN** the canonical schema, enum path, reference, or normative section is missing or invalid
- **THEN** validation fails closed with an actionable contract finding

### Requirement: Canonical alignment does not expand legal authority

Correcting or validating the enum MUST NOT convert an unresolved record into exhaustion, filing readiness, human approval, or publication authority.

#### Scenario: Enum contract passes

- **WHEN** schema and reference vocabulary match
- **THEN** the result proves only contract consistency and all legal, evidence, release, and human gates remain independent
