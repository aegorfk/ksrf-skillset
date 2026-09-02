## ADDED Requirements

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
