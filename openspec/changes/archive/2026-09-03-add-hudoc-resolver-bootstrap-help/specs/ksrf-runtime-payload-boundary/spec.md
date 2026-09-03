## MODIFIED Requirements

### Requirement: External HUDOC command resolution is explicit and deterministic

The installed HUDOC KB and vector launchers MUST execute only an exact CLI path
configured by their command-specific override or a version-compatible CLI
resolved below an explicit `HUDOC_KS_PARSER_REPO`. They MUST NOT derive a
repository from HOME, the current working directory or another ambient
filesystem location. Repository worktree lookup, interface-version checks,
subprocess working directory and `PYTHONPATH` composition MUST remain supported.
The installed guidance MUST state that the HUDOC engine is external and not
bundled. When and only when both relevant configuration keys are absent, an
exact lone `-h` or `--help` MAY return local resolver-setup guidance without
candidate discovery or execution; every other unconfigured invocation MUST fail
closed as before, and every present configuration MUST retain the existing
exclusive resolution and version gates.

#### Scenario: Exact HUDOC CLI override is configured

- **WHEN** the command-specific CLI variable names an existing
  version-compatible executable
- **THEN** the launcher uses that exact file without searching HOME, cwd or a
  repository fallback

#### Scenario: Explicit HUDOC repository is configured

- **WHEN** `HUDOC_KS_PARSER_REPO` names a repository root or its main checkout
  has compatible Git worktrees
- **THEN** the launcher deterministically resolves a compatible CLI, preserves
  the selected repository as cwd and composes the required `PYTHONPATH`

#### Scenario: HUDOC integration is unconfigured for an operational command

- **WHEN** neither the command-specific CLI variable nor
  `HUDOC_KS_PARSER_REPO` is set and argv is not exactly one help flag
- **THEN** the launcher fails closed with an actionable message naming the
  accepted variables, and the guidance treats this as an unconfigured
  capability rather than an absence finding

#### Scenario: HUDOC integration is unconfigured for exact help

- **WHEN** neither relevant variable is present and argv is exactly `-h` or
  `--help`
- **THEN** the launcher prints local setup guidance without searching for or
  executing an external engine

#### Scenario: Ambient repository exists

- **WHEN** a compatible `ks_parser` checkout exists below HOME or the current
  directory but no explicit HUDOC variable is set
- **THEN** the launcher ignores it and fails closed instead of executing ambient
  code, except that exact local help may describe explicit setup without search

#### Scenario: Explicit target has an incompatible interface

- **WHEN** an exact CLI or configured repository exposes a pre-contract
  interface version
- **THEN** the existing version gate rejects it and no alternate ambient
  checkout or local bootstrap success is selected
