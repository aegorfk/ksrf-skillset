# ksrf-hudoc-resolver-bootstrap-help Specification

## Purpose
TBD - created by archiving change add-hudoc-resolver-bootstrap-help. Update Purpose after archive.
## Requirements
### Requirement: Fully unconfigured HUDOC resolvers provide local setup help

Each bundled HUDOC resolver MUST recognize exactly `-h` or `--help` locally
when both its direct-CLI configuration key and `HUDOC_KS_PARSER_REPO` are absent
from the environment. It MUST print resolver-specific Russian setup guidance to
stdout and exit `0` with empty stderr before candidate discovery, path or
version-file inspection, Git worktree enumeration, or process execution. The
guidance MUST identify the direct CLI path option, repository-root option,
required interface versions, disabled implicit search, and the need to repeat
help after setup for authoritative engine arguments. It MUST state that showing
bootstrap help does not confirm engine availability, corpus coverage, or legal
authority.

#### Scenario: Knowledge resolver long help before setup

- **WHEN** neither `HUDOC_KB_CLI` nor `HUDOC_KS_PARSER_REPO` exists and argv is
  exactly `--help`
- **THEN** the knowledge wrapper prints only its local Russian setup help with
  code `0` and performs no discovery or delegation

#### Scenario: Vector resolver short help before setup

- **WHEN** neither `HUDOC_VECTOR_CLI` nor `HUDOC_KS_PARSER_REPO` exists and argv
  is exactly `-h`
- **THEN** the vector wrapper prints only its local Russian setup help with code
  `0` and performs no discovery or delegation

### Requirement: Explicit HUDOC configuration remains fail closed

The presence of either relevant configuration key MUST disable local bootstrap
help regardless of whether its value is empty, whitespace, missing, invalid, or
incompatible. Such invocations MUST follow the existing exclusive candidate and
version-check path and MUST NOT fall back to local help, HOME, cwd, another
resolver, or an unconfigured search. An exact help flag combined with another
token MUST NOT qualify as bootstrap help.

#### Scenario: Direct variable is present but blank

- **WHEN** a resolver's direct CLI variable exists with a blank value and argv
  is `--help`
- **THEN** the existing explicit blank-configuration error is returned instead
  of bootstrap help

#### Scenario: Repository variable points to an incompatible engine

- **WHEN** `HUDOC_KS_PARSER_REPO` is present but no compatible candidate exists
  and argv is `--help`
- **THEN** the existing version/interface failure is returned instead of local
  help or implicit fallback

#### Scenario: Help is combined with another token before setup

- **WHEN** both relevant configuration keys are absent but argv contains a help
  flag plus any additional token
- **THEN** the resolver retains its ordinary unconfigured failure and does not
  present setup help as a successful command

### Requirement: Configured HUDOC delegation remains exact

When a compatible configured engine exists, each resolver MUST preserve its
direct-path precedence, repository/worktree candidate order, expected version
gates, cwd and PYTHONPATH construction, and exact argv forwarding. In
particular, configured `-h` or `--help` MUST be delegated to the compatible
engine rather than replaced with bootstrap help. A successful local bootstrap
help response MUST NOT be treated as evidence of corpus readiness, source
coverage, promotion eligibility, or complaint filing readiness.

#### Scenario: Compatible engine receives help

- **WHEN** a compatible engine is configured and the resolver receives exactly
  `--help`
- **THEN** the wrapper executes that engine and forwards `--help` unchanged

#### Scenario: Compatible engine receives non-help arguments

- **WHEN** a compatible engine is configured and the resolver receives search
  or status arguments
- **THEN** the wrapper forwards every argument unchanged under the existing
  checked environment and working directory
