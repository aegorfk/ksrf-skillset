# ksrf-user-facing-cli Specification

## Purpose

Define stable Russian-language help for documented public KSRF runtime commands
without changing their executable, machine-facing, or non-help contracts.
## Requirements
### Requirement: Doctrine and authority runtime CLI help is Russian and actionable

The documented doctrine-research and authority-ledger KSRF runtime CLIs MUST render their root help, and every documented doctrine subcommand help route, in Russian. Help MUST retain executable command and option tokens, return exit code `0`, write no stderr, explain public arguments, and omit test-only or maintainer-only switches. Machine identifiers, JSON keys, provider names, and execution behavior MUST remain unchanged.

#### Scenario: Doctrine root help is Russian

- **WHEN** a user runs `doctrine_research.py --help` from a clean installed payload
- **THEN** stdout contains Russian usage, command, parameter, and built-in help descriptions; lists all five stable subcommand names; omits default English scaffolding and `--offline-fixtures`; stderr is empty; and exit code is `0`

#### Scenario: Doctrine subcommand help is Russian

- **WHEN** a user runs `route`, `plan`, `search`, `validate`, or `rerank` with `--help`
- **THEN** stdout explains the subcommand and each public option in Russian while preserving its exact command and option tokens, stderr is empty, and exit code is `0`

#### Scenario: Authority-ledger help is Russian

- **WHEN** a user runs `validate_authority_ledger.py --help` from a clean installed payload
- **THEN** stdout contains Russian usage, positional-path, parameter, public-URL, drafting-gate, and built-in help descriptions; omits default English scaffolding; stderr is empty; and exit code is `0`

#### Scenario: Hidden fixture route is preserved but unsupported publicly

- **WHEN** source QA inspects the doctrine parser after help suppression
- **THEN** `--offline-fixtures` remains a registered callable option for existing tests but does not appear in any public help output

#### Scenario: Machine contracts do not change

- **WHEN** the help-only release is compared with its base
- **THEN** subcommand names, public option strings, defaults, exit-code behavior, JSON fields, provider identifiers, and non-help execution paths remain unchanged

### Requirement: Remaining documented runtime CLI help uses Russian presentation

The installed KSRF user-facing CLI MUST preserve Russian help across
`judicial_meaning.py`, `ksrf.py`, `ksrf_setup_doctor.py`,
`ksrf_autocollect.py`, `ksrf_practice_analysis.py`, and
`validate_argument_research.py` runtime commands MUST render every reachable
public help route with Russian usage, section headings, built-in help text,
descriptions, and value placeholders. Help MUST preserve executable command,
alias, exact option, choice, and machine identifiers. Every `argparse` parser,
including nested subparsers, MUST reject abbreviated long options before
handler dispatch. Apart from that intentional rejection, non-help usage,
errors, defaults, exit codes, hidden options, JSON, and execution paths MUST
remain unchanged.

#### Scenario: Nested parser help is consistently Russian

- **WHEN** source QA recursively enumerates each nested parser route and invokes
  that route from a clean installed payload with `--help`
- **THEN** every invocation exits `0`, writes no stderr, contains Russian help
  scaffolding, and contains no default English `argparse` heading, built-in help
  sentence, or generated English value placeholder

#### Scenario: Wrapper and standalone help is consistently Russian

- **WHEN** a user invokes `ksrf_setup_doctor.py`, `ksrf_autocollect.py`, or
  `validate_argument_research.py` with `--help`
- **THEN** the command explains its purpose and public inputs in Russian while
  retaining its stable program label and exact option tokens

#### Scenario: Parser state is restored after help

- **WHEN** help is rendered from an in-process parser and the same parser is
  inspected or used afterward
- **THEN** action destinations, metavariables, choices, defaults, required
  flags, aliases, hidden-help state, exact-option policy, and parser behavior
  equal their pre-help values

#### Scenario: Non-help contracts remain exact except abbreviation diagnostics

- **WHEN** representative root, nested, missing-argument, invalid-choice, and
  standalone-validator failures are compared with the base release
- **THEN** stderr/stdout placement, exit codes, command names, and default
  metavariables remain byte-for-byte compatible for exact tokens, while every
  long-option prefix is rejected with code `2` before handler execution and its
  diagnostic MAY change from Python's former accepted or ambiguous-prefix text
  to unknown-argument text

#### Scenario: Hidden test routes remain hidden

- **WHEN** the judicial-meaning collection help is rendered
- **THEN** the existing fixture-directory option remains registered for source
  tests but is absent from public help and from the installed documentation

### Requirement: Practice-analysis arguments explain their user-visible behavior

Every public argument exposed by `ksrf_practice_analysis.py` MUST have a non-empty plain-Russian explanation across all reachable help routes. Help and route summaries MUST identify the role of file, folder, workspace, identifier, reviewer, date, selection, and export arguments; state meaningful defaults and omission behavior; describe attach, import, status, validation, and lint no more broadly than their handlers; preserve human-review, trusted-source, audit-only, and filing-readiness boundaries; preserve executable tokens; remain readable in terminals from 60 through 80 columns; and MUST NOT change parser or non-help behavior.

#### Scenario: Every installed argument has actionable Russian help

- **WHEN** source QA recursively inventories all 18 routes and invokes every
  route from a clean installed payload with `--help`
- **THEN** all 42 public argument actions across 11 leaf routes and 18 total
  help routes have non-empty Russian help, every invocation exits `0` without
  stderr, and no option is left as a bare token and metavar

#### Scenario: Paths and workspaces are distinguishable

- **WHEN** help displays a workspace, source workspace, input artifact, or
  output option
- **THEN** it explains what the path contains or where the result is stored,
  states that `--trusted-source-workspace` must match the previously attached
  cassation workspace, and does not imply trust or approval merely from
  supplying a path

#### Scenario: Omission behavior and defaults are visible

- **WHEN** `--claim-id`, `--argument-research`, `--skills-root`, `--output`,
  `--trusted-source-workspace`, `--corpus-cutoff`, or `--stage` is omitted
- **THEN** help states the resulting selection, discovery, storage, date, or
  default behavior that the runtime already implements

#### Scenario: Legal and evidence gates remain explicit

- **WHEN** help describes attaching, importing, reviewing, refreshing,
  validating practice material, `--official-check-ref`, or `--stage filing`
- **THEN** it distinguishes recorded data from a human-approved finding and does
  not claim filing readiness or trusted provenance without the existing gates;
  a supplied trusted-source path alone remains audit-only, an official-check
  reference records the reviewer's reference rather than proving an official
  source check, and the filing stage remains local validation rather than
  central host-attested filing authority

#### Scenario: Route summaries match handler scope

- **WHEN** help describes `run attach`, `result import`, or `lint`
- **THEN** attach is described as dispatching a request rather than attaching a
  result, import admits material stored only for audit rather than calling every
  result trusted, and lint promises only the structures, checksums, chains, and
  self-identifiers it actually checks

#### Scenario: Narrow terminal preserves atomic values

- **WHEN** every clean-installed help route is rendered at each width from
  `COLUMNS=60` through `COLUMNS=80`
- **THEN** every line fits the declared width and no path, option, identifier,
  date format, state, or other machine token is split at a hyphen

#### Scenario: Machine and non-help contracts remain exact

- **WHEN** the documented-help release is compared with its base
- **THEN** route count, commands, options, choices, defaults, destinations,
  handlers, program labels, usage, parser state, JSON, stdout/stderr, errors,
  exit codes, and non-help execution paths remain unchanged
