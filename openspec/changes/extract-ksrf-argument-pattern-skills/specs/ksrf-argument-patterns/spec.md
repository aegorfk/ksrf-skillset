# ksrf-argument-patterns Specification

## ADDED Requirements

### Requirement: Corpus-Grounded Argument Pattern Registry

The system SHALL maintain a reusable registry of constitutional-law argument patterns extracted from the local KSRF Постановления corpus.

#### Scenario: Pattern references include decisions

- **WHEN** an agent uses an argument pattern
- **THEN** the skill references SHALL show KSRF Постановления where that pattern appears in the corpus
- **AND** the agent SHALL treat those decisions as retrieval anchors requiring quote-level review before final legal use.

#### Scenario: New case diagnosis

- **WHEN** a user asks to analyze a new case for a constitutional complaint or court request
- **THEN** the agent SHALL select all plausible patterns, not only the strongest pattern
- **AND** for each selected pattern state what facts, documents, lower-court practice, or procedural acts are needed.

### Requirement: Automation Backlog Per Pattern

The system SHALL keep automation ideas tied to specific argument patterns.

#### Scenario: User asks what tools to build

- **WHEN** the user asks how to implement a pattern for new cases
- **THEN** the agent SHALL consult the automation backlog reference
- **AND** propose tool ideas scoped to the selected pattern.

### Requirement: Local Corpus Artifacts

The system SHALL preserve corpus pass artifacts for review and iteration.

#### Scenario: Rebuilding the registry

- **WHEN** the ruling corpus changes or the taxonomy is updated
- **THEN** `scripts/extract_ksrf_argument_patterns.py` SHALL be runnable locally
- **AND** produce summary, corpus index, pattern hits, failures, and pattern summary artifacts.

### Requirement: Argument Package Builder

The system SHALL describe constitutional-law argument as a package of primary, reinforcing, saving, and remedial patterns rather than a single isolated pattern.

#### Scenario: Drafting a new complaint argument

- **WHEN** an agent selects a constitutional-law pattern for a new case
- **THEN** the skill references SHALL require the agent to identify the primary pattern
- **AND** identify plausible reinforcing, saving, and remedial patterns
- **AND** state how the patterns interact without overclaiming the case.

### Requirement: Secretariat Counterargument Playbook

The system SHALL preserve a reusable counterargument checklist for common admissibility and Secretariat objections.

#### Scenario: Checking a draft argument

- **WHEN** an agent reviews or drafts a KSRF complaint argument
- **THEN** it SHALL check whether the project answers ordinary-court-error, fact-reassessment, abstract-review, already-resolved, and no-normative-defect objections
- **AND** produce a safer fallback framing when an objection is strong.

### Requirement: Evidence Maps Per Pattern

The system SHALL maintain evidence maps that convert each argument pattern into documents, facts, court-act checks, and lower-court practice searches.

#### Scenario: Preparing materials for a pattern

- **WHEN** an agent proposes a pattern for a new case
- **THEN** it SHALL list the evidence needed to prove that pattern
- **AND** list materials that would weaken or falsify the pattern
- **AND** identify automation hooks where lower-court practice or court-act parsing can support the argument.

### Requirement: KSRF Language Formula Bank

The system SHALL extract and preserve reusable KSRF-style language formulas from the local ruling corpus.

#### Scenario: Drafting the requested constitutional meaning

- **WHEN** an agent drafts the question, demand, or constitutional-law meaning
- **THEN** it SHALL consult the language formula bank
- **AND** adapt formulas such as `в той мере, в какой`, `по смыслу, придаваемому практикой`, `не предполагает`, `не исключает`, and legislature-duty formulas to the concrete norm.

### Requirement: Constitutional Argument Graph

The system SHALL maintain a portable constitutional argument graph linking patterns, constitutional articles, norm types, harm types, KSRF decision anchors, evidence maps, automation hooks, and demand formulas.

#### Scenario: Navigating from case facts to argument structure

- **WHEN** a new case is analyzed
- **THEN** the agent SHALL use the graph to connect facts and norm defects to candidate patterns
- **AND** use graph edges to identify articles of the Constitution, proof tasks, decision anchors, and output formulas.
