## MODIFIED Requirements

### Requirement: Argument-research validation is total for JSON artifacts

The installed `validate_argument_research.py` validator MUST return a
deterministic validation result for every root value produced by `json.loads`.
It MUST reject omissions and JSON type mismatches in the executable core
contract instead of treating them as valid defaults or allowing a Python
exception. It MUST NOT coerce malformed values into identifiers, MUST continue
validating independent fields, and MUST keep extension fields outside the core
open and opaque.

#### Scenario: Required root containers cannot disappear into defaults

- **WHEN** `case_id`, `findings`, `hypotheses`, or `portfolio` is absent
- **THEN** validation reports the absent or invalid required root field
- **AND** an explicitly present empty findings or hypotheses array remains
  valid

#### Scenario: Published finding and hypothesis fields have executable types

- **WHEN** a required finding or hypothesis field is absent or has the wrong
  JSON type
- **THEN** validation reports the exact object field or array entry
- **AND** identifiers and prose fields require non-empty strings, reference and
  prose-list fields require arrays of non-empty strings,
  `contains_sensitive_data` requires a boolean, and `locator` requires `null`
  or a non-empty string
- **AND** the existing relation, verification, confidence, hypothesis-status,
  case-isolation, and verified-locator rules remain enforced

#### Scenario: Core references resolve after identifier collection

- **WHEN** a hypothesis cites a finding or a finding cites a hypothesis
- **THEN** every valid reference string is checked against all declared IDs,
  including forward references
- **AND** unknown identifiers are reported in sorted deterministic diagnostics
- **AND** malformed values are neither coerced nor included in set operations

#### Scenario: Portable portfolio core is present and typed

- **WHEN** an artifact contains a portfolio
- **THEN** it contains `human_approval`, `principal_hypothesis_id`, and the
  reserve, experimental, and rejected hypothesis-ID arrays
- **AND** the approval uses the existing enum, the principal is `null` or a
  non-empty known hypothesis ID, and each role array contains only non-empty
  known hypothesis IDs
- **AND** unrecognized extension fields remain allowed and opaque

#### Scenario: Approval cannot be structurally empty

- **WHEN** `human_approval` is `approved`
- **THEN** a non-null known principal hypothesis and a non-empty string
  `approved_by` are required
- **AND WHEN** approval is pending, revise, rejected, or invalid
- **THEN** a non-null principal remains rejected

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

#### Scenario: Success states only the checked authority

- **WHEN** the executable core structure, types, and references pass
- **THEN** the CLI returns code `0` with a Russian success line that says legal
  readiness was not evaluated
- **AND** Russian text and Unicode identifiers remain encodable even when the
  process inherits an ASCII standard-stream encoding
- **AND** it does not claim validation of hard-gate internals, dimension
  semantics, critic findings, approval reasons, ECHR extensions, source truth,
  drafting readiness, or filing authority
- **AND WHEN** file reading, UTF-8 decoding, JSON syntax parsing, bounded
  nesting, or the interpreter's integer conversion limit fails
- **THEN** the existing code `2` stderr diagnostic contract is retained
