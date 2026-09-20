## ADDED Requirements

### Requirement: Agent-directed comparative retrieval
The skills SHALL guide an agent to use an available MCP corpus as a preferred structured retrieval route while independently adapting research questions and checking full source context. They SHALL preserve direct official-source and validated CLI/API alternatives.

#### Scenario: Relevant foreign collection is available
- **WHEN** an agent researches a constitutional issue from Russian case materials
- **THEN** it checks current tool capabilities and corpus scope, chooses appropriate query modes and original-language terms, reads the necessary continuation pages, and tests adverse explanations before forming a comparative conclusion.

#### Scenario: Missing corpus or incomplete search
- **WHEN** MCP is unavailable, results are bounded, semantic search is not ready, or the relevant period is outside coverage
- **THEN** the agent continues with available official texts or an addressed official search and records the remaining gap
- **AND** it does not infer the absence of case law, initiate mass ingestion, or require infrastructure installation to continue independent work.

### Requirement: Distinct source and authority boundaries
The workflow SHALL distinguish foreign, HUDOC and Russian source routes, retained statistics from current searchable coverage, and an author's assertion from the court's adopted reasoning.

#### Scenario: Public retrieval for a private matter
- **WHEN** a public MCP or search engine is used for a case
- **THEN** queries describe the legal mechanism without unnecessary personal or confidential case data, and source-linked findings retain their own legal weight and Russian anchor status.

#### Scenario: Same backend through a different transport
- **WHEN** the agent uses CLI/API instead of MCP
- **THEN** source-version, scope and citation checks remain the same, and direct filesystem/database access is not treated as a bypass of those boundaries.
