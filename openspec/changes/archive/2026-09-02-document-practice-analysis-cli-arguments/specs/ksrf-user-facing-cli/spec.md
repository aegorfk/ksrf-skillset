## ADDED Requirements

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
