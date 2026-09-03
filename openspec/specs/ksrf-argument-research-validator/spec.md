# ksrf-argument-research-validator Specification

## Purpose
TBD - created by archiving change make-argument-validator-total. Update Purpose after archive.
## Requirements
### Requirement: Argument-research validation is total for JSON artifacts

The installed `validate_argument_research.py` validator MUST return a
deterministic validation result for every root value produced by `json.loads`.
Wrong JSON types MUST become addressed validation errors and MUST NOT escape as
`TypeError`, another Python exception, or a traceback. The validator MUST NOT
coerce malformed values into identifiers. It MUST continue validating
independent fields after a malformed value while preserving the existing
success output and read/JSON-syntax failure contract.

#### Scenario: Reference containers reject non-array JSON values

- **WHEN** a finding-reference or portfolio-reference field is present as
  `null`, a boolean, a number, a string, or an object instead of an array
- **THEN** validation reports that exact field as requiring an array
- **AND** no set operation, sorting failure, or traceback escapes

#### Scenario: Non-object root is a semantic validation failure

- **WHEN** a successfully decoded JSON root is `null`, a boolean, a number, a
  string, or an array instead of an object
- **THEN** validation returns the addressed `root must be an object` error
- **AND** the CLI returns code `1` through the normal `ERROR:` stdout channel
  with empty stderr and no traceback

#### Scenario: Reference entries reject malformed identifiers by index

- **WHEN** a reference array contains `null`, booleans, numbers, arrays,
  objects, empty strings, or a mixture of malformed and valid string entries
- **THEN** each malformed entry receives an indexed non-empty-string error
- **AND** valid string entries still participate in deterministic unknown-ID
  checks without coercing or sorting malformed values

#### Scenario: Enum and principal fields cannot trigger unhashable membership

- **WHEN** a relation, verification status, confidence, hypothesis status,
  human approval, or principal-hypothesis field contains any wrong JSON type
- **THEN** validation emits its field-specific invalid/type error and continues
- **AND** no unhashable membership exception or traceback escapes

#### Scenario: Semantic CLI failure is clean in source and installation

- **WHEN** a syntactically valid malformed artifact is validated from the
  source tree or a clean installed payload
- **THEN** the command returns code `1`, prints deterministic `ERROR:` lines to
  stdout, leaves stderr empty, emits no traceback, and does not alter the input

#### Scenario: Reflected identifiers are encoding-safe

- **WHEN** duplicate finding or hypothesis identifiers contain a lone
  surrogate, newline, quote, backslash, or control character decoded from JSON
- **THEN** the diagnostic renders an ASCII-safe, single-line escaped form
- **AND** comparison still uses the original unmodified identifier value
- **AND** output encoding cannot turn the validation result into a traceback

#### Scenario: Valid and syntax-error controls remain compatible

- **WHEN** the validator receives a valid artifact
- **THEN** it returns code `0` with the exact existing success line
- **AND WHEN** file reading, UTF-8 decoding, JSON syntax parsing, bounded
  nesting, or the interpreter's integer conversion limit fails
- **THEN** it retains the existing code `2` stderr diagnostic contract
