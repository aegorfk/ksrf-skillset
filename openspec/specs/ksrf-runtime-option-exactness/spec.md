# ksrf-runtime-option-exactness Specification

## Purpose
TBD - created by archiving change reject-abbreviated-runtime-options. Update Purpose after archive.
## Requirements
### Requirement: Public runtime long options require exact spelling

Every public installed KSRF command backed by `argparse` MUST set
`allow_abbrev=False` on its root parser and every reachable nested parser. A
token that is only a prefix of a declared long option MUST be rejected by
argument parsing with code `2` before handler dispatch, filesystem mutation,
network access, or external process execution. Exact declared options, short
options, command aliases, positional values that are not proper prefixes of a
declared long option, choices, defaults, destinations, help, output schemas,
and handler behavior MUST remain unchanged. In the legacy single-path argument
validator, a proper prefix of its declared `--help` option MUST be rejected
before file access both as a bare token and in `--prefix=VALUE` option syntax;
every other dash-prefixed path, including `-`, `--`, `-case.json`,
`--case.json`, `--case=value.json`, `--helpful.json`, and
`--helpful=case.json`, MUST retain its prior positional-file behavior.
The rule applies to options parsed by the bundled KSRF runtime; it MUST NOT
rewrite or pre-parse opaque arguments delegated to a compatible configured
HUDOC engine.

#### Scenario: Abbreviated mutating options are rejected before matter creation

- **WHEN** a user invokes `ksrf.py matter init` with `--matter-i` and
  `--worksp` instead of the declared `--matter-id` and `--workspace`
- **THEN** parsing returns code `2`, produces no success output, and creates no
  workspace, manifest, evidence record, draft, audit event, or other file

#### Scenario: Exact mutating options remain valid

- **WHEN** the same command uses the exact declared `--matter-id` and
  `--workspace` options with otherwise valid input
- **THEN** the existing handler runs with unchanged output and artifact content

#### Scenario: Nested command parsers reject unique prefixes

- **WHEN** source QA recursively inspects every reachable public parser or a
  user supplies a unique long-option prefix to a nested route
- **THEN** every parser reports `allow_abbrev=False` and no nested route accepts
  the prefix as a documented option

#### Scenario: Clean-installed behavior matches source behavior

- **WHEN** the abbreviation regression is repeated against a clean runtime
  installation
- **THEN** the same token is rejected before side effects and every exact-token
  control retains its source behavior

#### Scenario: Manual single-path validator distinguishes a prefix from a path

- **WHEN** `validate_argument_research.py` receives `--he` or
  `--he=case.json`, using a proper prefix of its declared `--help` option
- **THEN** it returns code `2` and names the complete rejected token before
  reading a same-named file
- **AND WHEN** it receives another existing dash-prefixed path such as
  `-case.json`, `--case.json`, `--case=value.json`, `--helpful.json`,
  `--helpful=case.json`, `-`, or `--`
- **THEN** it validates that file with the unchanged positional-file behavior
