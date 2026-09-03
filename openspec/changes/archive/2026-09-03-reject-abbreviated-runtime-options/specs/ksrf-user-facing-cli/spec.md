## MODIFIED Requirements

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
