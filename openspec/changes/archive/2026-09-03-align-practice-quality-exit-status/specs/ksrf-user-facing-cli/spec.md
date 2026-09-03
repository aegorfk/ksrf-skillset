## ADDED Requirements

### Requirement: Practice quality help explains process outcomes

The clean-installed Russian help for `quality coding-reliability` and `quality prefiling-refresh` MUST explain that code `0` requires exact top-level Boolean `complete=true`, code `2` denotes invalid arguments/input/output I/O, and code `3` denotes a valid but incomplete or stale result. It MUST state that code `3` preserves full JSON on stdout and at an explicitly requested output path, and that code `0` does not approve or authorize filing.

#### Scenario: Automation contract is discoverable at both quality routes

- **WHEN** a user invokes either quality subcommand with `--help`
- **THEN** stdout contains the `0`/`2`/`3` guide in Russian
- **AND** help returns `0` with empty stderr
- **AND** the filing-authority boundary is explicit

### Requirement: Public-cache producer inputs are discoverable

The installed CLI MUST expose `cache refresh-plan --coverage-requirements`, `cache treatment quality-export --output`, provenance options for indexed treatment source text, and `cache treatment review --decision-reason`. Help MUST identify the non-empty coverage requirement shape, the complete content-bound purpose of quality-export, the RFC 3339 timestamp requirement, and the rejected-review reason requirement.

#### Scenario: User can find the complete prefiling producer path

- **WHEN** a user reads help for cache refresh planning, treatment quality export, ingest, or treatment review
- **THEN** the required options and Russian explanations identify how to create the official producer artifacts
- **AND** no help text suggests that a verified-only list or caller-authored treatment array is a valid prefiling input

### Requirement: Prefiling CLI requires exact filing-significant inputs

The installed `quality prefiling-refresh` parser MUST require refresh plan, treatment-quality-set, the existing public cache root, baseline/current corpus digests, subject evidence SHA, checked-through, filing cutoff, reviewer, reviewed-at, and one or more explicit claim IDs. Repeated claim IDs MUST express the complete claim population, while empty, duplicate, or noncanonical values fail as input errors. Help MUST explain that the cache is reopened read-only for live regeneration and that filing cutoff is a control point for the final preparation window, not a computed procedural deadline.

#### Scenario: Required claim identity is omitted

- **WHEN** a caller omits `--claim-id`
- **THEN** argument parsing returns code `2`
- **AND** no result artifact is created

#### Scenario: Bare treatment list is supplied

- **WHEN** `--treatments` points to a bare JSON array, partial object, or foreign failure envelope instead of the exact quality-export envelope
- **THEN** the CLI returns code `2` with a Russian diagnostic
- **AND** does not reinterpret the contents as an empty or complete treatment population

### Requirement: Source and clean-installed launchers agree

The source-tree and clean-installed public launchers MUST expose the same commands/options and MUST agree on process code, stdout/stderr, JSON result, explicit output artifact, and no-side-effect behavior for equivalent complete, incomplete, and invalid quality cases, apart from expected filesystem paths.

#### Scenario: End-to-end official treatment reaches prefiling

- **WHEN** both launchers register an official seed, ingest and index its full text with document/chain/query provenance, discover and content-bind a review, export the full treatment set, generate a coverage-bound refresh plan, and run prefiling
- **THEN** both launchers accept the same evidence contract and produce equivalent quality outcomes
