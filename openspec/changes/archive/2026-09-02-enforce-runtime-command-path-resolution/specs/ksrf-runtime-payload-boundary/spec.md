## ADDED Requirements

### Requirement: Installed command examples resolve the actual skill root

Every runtime Markdown and public README invocation of a bundled script MUST resolve through a quoted `KSRF_SKILLS_ROOT`. If the variable is unset, the documented resolution MUST use `CODEX_HOME/skills` when `CODEX_HOME` is set and otherwise `$HOME/.codex/skills`. User-facing commands MUST NOT contain `<skill-dir>`, `<skill-root>`, `/path/to/installed/skills` or a fixed `~/.codex/skills` program path. Installation MUST print a shell-safe export for the resolved target and MUST NOT edit a shell profile.

#### Scenario: Default installation command is copied

- **WHEN** a user copies a bundled command without defining any root variable
- **THEN** it resolves the program below `$HOME/.codex/skills`, quotes the program path, and preserves every documented subcommand and option

#### Scenario: Installed public wrapper starts

- **WHEN** the public `ksrf.py` command is invoked from a clean-room installation
- **THEN** it imports the bundled `lib/ksrf` implementation without requiring a repository checkout or a `src` package

#### Scenario: Installed command surface is smoke-tested

- **WHEN** each of the eight unique bundled CLIs named by user-facing documentation is invoked with `--help` from an unrelated working directory
- **THEN** every program loads only its installed dependencies, prints help and exits successfully without mutating user data

#### Scenario: Custom CODEX_HOME or explicit skill root is used

- **WHEN** `CODEX_HOME` or `KSRF_SKILLS_ROOT` points to a directory containing spaces
- **THEN** the same command resolves and executes the bundled program without word splitting, with explicit `KSRF_SKILLS_ROOT` taking precedence

#### Scenario: Custom-target installation completes

- **WHEN** `install.sh --target PATH` succeeds
- **THEN** it prints one POSIX-shell-safe `export KSRF_SKILLS_ROOT=PATH` for the resolved target and does not modify a shell profile

#### Scenario: An unresolved runtime command returns

- **WHEN** either validation profile or the offline verifier encounters an executable bundled-script path using a placeholder or fixed default root
- **THEN** it fails with a command-path resolution finding before the payload is treated as source- or runtime-clean

#### Scenario: Bundled companion reference is named

- **WHEN** a runtime skill links to a companion file in its own `references` directory
- **THEN** the exact relative target resolves inside the installed package and Markdown link validation fails if the target is missing

### Requirement: External HUDOC command resolution is explicit and deterministic

The installed HUDOC KB and vector launchers MUST execute only an exact CLI path configured by their command-specific override or a version-compatible CLI resolved below an explicit `HUDOC_KS_PARSER_REPO`. They MUST NOT derive a repository from HOME, the current working directory or another ambient filesystem location. Repository worktree lookup, interface-version checks, subprocess working directory and `PYTHONPATH` composition MUST remain supported. The installed guidance MUST state that the HUDOC engine is external and not bundled.

#### Scenario: Exact HUDOC CLI override is configured

- **WHEN** the command-specific CLI variable names an existing version-compatible executable
- **THEN** the launcher uses that exact file without searching HOME, cwd or a repository fallback

#### Scenario: Explicit HUDOC repository is configured

- **WHEN** `HUDOC_KS_PARSER_REPO` names a repository root or its main checkout has compatible Git worktrees
- **THEN** the launcher deterministically resolves a compatible CLI, preserves the selected repository as cwd and composes the required `PYTHONPATH`

#### Scenario: HUDOC integration is unconfigured

- **WHEN** neither the command-specific CLI variable nor `HUDOC_KS_PARSER_REPO` is set
- **THEN** the launcher fails closed with an actionable message naming the accepted variables, and the guidance treats this as an unconfigured capability rather than an absence finding

#### Scenario: Ambient repository exists

- **WHEN** a compatible `ks_parser` checkout exists below HOME or the current directory but no explicit HUDOC variable is set
- **THEN** the launcher ignores it and fails closed instead of executing ambient code

#### Scenario: Explicit target has an incompatible interface

- **WHEN** an exact CLI or configured repository exposes a pre-contract interface version
- **THEN** the existing version gate rejects it and no alternate ambient checkout is selected
