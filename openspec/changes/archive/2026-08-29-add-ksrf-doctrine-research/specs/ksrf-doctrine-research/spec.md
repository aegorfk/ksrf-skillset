## ADDED Requirements

### Requirement: Norm-first doctrine request
The skill MUST start from public descriptors of the disputed regulation, its judicial meaning when known, legal mechanism and consequence, and MUST NOT preseed a constitutional conclusion.

#### Scenario: Exploratory research without a case
- **WHEN** a researcher supplies a public norm profile without application evidence
- **THEN** the system labels the run `exploratory_norm` and emits only norm-scoped candidates

#### Scenario: Case-scoped research
- **WHEN** a researcher requests `case_scoped`
- **THEN** the system requires a valid norm version date, non-empty public judicial meaning, mechanism, consequence and references to separate application evidence

### Requirement: External query privacy
The system MUST send only typed, public, abstracted query fields to external providers and MUST fail before transport when the privacy contract or human approval gate is not satisfied.

#### Scenario: Nested or private query value
- **WHEN** a query-bearing norm, phrase, language, mechanism or consequence contains a non-string nested object or detected private identifier
- **THEN** validation fails and no external request is made

#### Scenario: Case-aware query plan review
- **WHEN** `case_scoped` or `hypothesis_verification` would use the network
- **THEN** the exact reviewed `query_plan_hash` is required and a mismatch blocks the run before new artifacts are written

### Requirement: Independent search lanes and adverse pass
The system MUST generate independent search intents for the norm, disputed elements, mechanisms, consequences, system links, procedure, remedy, history and adverse positions.

#### Scenario: Hypothesis verification without a disputed element
- **WHEN** a valid hypothesis-verification request omits disputed elements
- **THEN** the query plan still contains at least one explicit adverse lane derived from the norm and hypothesis

### Requirement: Provider capability routing
The system MUST use only explicitly selected providers with a documented enabled adapter and MUST report unavailable, manual, subscription and authentication routes as coverage gaps rather than absence.

#### Scenario: Missing OpenAlex key
- **WHEN** OpenAlex is selected for a network run without `OPENALEX_API_KEY`
- **THEN** preflight blocks the run before modifying the workspace

#### Scenario: Manual Russian database
- **WHEN** a database has no approved automated adapter
- **THEN** it is represented as a manual/access route and is not scraped

### Requirement: Response and run integrity
The system MUST validate provider response schemas and bind request, query plan, providers, bounds, selected query IDs and coverage to a single run configuration.

#### Scenario: Error payload with successful transport
- **WHEN** a provider returns HTTP success with an error or malformed response body
- **THEN** the query is logged as failed and bounded completion is false

#### Scenario: Stale workspace artifacts
- **WHEN** routing, run config and coverage describe different provider sets or hashes
- **THEN** workspace QA fails

### Requirement: Conservative source promotion
The system MUST keep metadata and abstract results as candidates, MUST use DOI/EDN/ISBN for confident automatic merging, and MUST require a full text with a locator before attributing a doctrinal proposition.

#### Scenario: Same title without a strong identifier
- **WHEN** two providers return the same title, author and year but no DOI, EDN or ISBN
- **THEN** the records remain separate pending manual family review

#### Scenario: Abstract-only source
- **WHEN** only metadata or an abstract is available
- **THEN** the source cannot produce a page-verified proposition or be promoted into complaint language

### Requirement: Doctrinal controversy and constitutional handoff
The system MUST preserve supporting and adverse propositions, locate the candidate defect, include a falsifier and mark constitutional hypotheses as conditional until official and case evidence gates are passed.

#### Scenario: Several supporting publications
- **WHEN** several publications criticize the same regulation
- **THEN** the output records their source families and limits and does not treat their count as proof of unconstitutionality

#### Scenario: Transfer to complaint cycle
- **WHEN** a doctrine hypothesis is handed to the KSRF complaint cycle
- **THEN** it declares that doctrine cannot satisfy official source, current norm version, application, stable judicial meaning, constitutional authority or case facts

### Requirement: Honest coverage
Federated doctrine discovery MUST retain `coverage_complete=false` unless every separately defined saturation gate is satisfied and MUST never infer corpus-wide absence from unavailable providers.

#### Scenario: Bounded API search succeeds
- **WHEN** all selected API queries complete successfully but Russian subscription or manual routes remain unchecked
- **THEN** `bounded_search_complete` may be true while `coverage_complete` and `absence_claim_permitted` remain false

### Requirement: Human-controlled acquisition and payment
The system MUST verify duplicates, open alternatives, vendor terms and relevance before proposing acquisition and MUST leave payment authorization false until a human approves the exact transaction.

#### Scenario: Candidate PDF link is unverified
- **WHEN** a metadata provider exposes a full-text-looking URL without verified access and license
- **THEN** the item remains in the acquisition review queue

#### Scenario: Paid source is required
- **WHEN** no lawful open or library copy is found for a material source
- **THEN** the system may prepare an acquisition request or invoice draft but does not debit funds or confirm banking

### Requirement: Fifteen-package publication
The public KSRF release MUST include `ksrf-doctrine-research` in the same manifest-covered, fail-closed file contract as the other canonical skills.

#### Scenario: Clean-room installation
- **WHEN** the published release is installed into an explicit empty target
- **THEN** exactly fifteen canonical KSRF skill trees are copied and runtime or secret files are excluded

#### Scenario: Live publication verification
- **WHEN** the release is declared complete
- **THEN** the atomic release HEAD equals the freshly observed live `main` SHA and the manifest base equals its first parent
