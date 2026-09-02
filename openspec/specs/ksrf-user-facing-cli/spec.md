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

The `judicial_meaning.py`, `ksrf.py`, `ksrf_setup_doctor.py`, `ksrf_autocollect.py`, `ksrf_practice_analysis.py`, and `validate_argument_research.py` runtime commands MUST render every reachable public help route with Russian usage, section headings, built-in help text, descriptions, and value placeholders. Help MUST preserve executable command, alias, option, choice, and machine identifiers. Non-help usage, errors, defaults, exit codes, hidden options, JSON, and execution paths MUST remain unchanged.

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
  retaining its stable program label and option tokens

#### Scenario: Parser state is restored after help

- **WHEN** help is rendered from an in-process parser and the same parser is
  inspected or used afterward
- **THEN** action destinations, metavariables, choices, defaults, required flags,
  aliases, hidden-help state, and parser behavior equal their pre-help values

#### Scenario: Non-help contracts remain exact

- **WHEN** representative root, nested, missing-argument, invalid-choice, and
  standalone-validator failures are compared with the base release
- **THEN** stderr/stdout placement, English machine-facing usage and error text,
  exit codes, command names, and default metavariables remain byte-for-byte
  compatible

#### Scenario: Hidden test routes remain hidden

- **WHEN** the judicial-meaning collection help is rendered
- **THEN** the existing fixture-directory option remains registered for source
  tests but is absent from public help and from the installed documentation
