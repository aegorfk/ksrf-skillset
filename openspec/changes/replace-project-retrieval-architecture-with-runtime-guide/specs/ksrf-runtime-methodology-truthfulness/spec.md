## ADDED Requirements

### Requirement: Installed position retrieval guidance is standalone and truthful

The installed argument-pattern skill MUST provide a bundled-first manual route for discovering, comparing, and verifying candidate Constitutional Court positions. It MUST NOT present an absent project, command, script, generated dataset, service, model, endpoint, collection, credential source, MCP operation, benchmark, or historical corpus counter as an installed capability. An optional external retrieval tool MAY be used only after its actual availability and callable interface are established in the current environment; its absence is a coverage limitation rather than permission to invent a result.

#### Scenario: User opens the installed guide

- **WHEN** the manifest installs `position-retrieval-architecture.md`
- **THEN** the guide can be followed with bundled references and official sources and contains no project-only setup or command path

#### Scenario: Optional retrieval capability is absent

- **WHEN** no external search backend or connector is available
- **THEN** the workflow continues through bundled maps and manual official-source search, records the coverage limit, and does not claim that automated retrieval ran

#### Scenario: Bounded search returns no close analogy

- **WHEN** the checked routes produce no close verified candidate
- **THEN** the result states that no close analogy was found in the checked scope and does not conclude that relevant practice does not exist or that the complaint is inadmissible

### Requirement: Manual position search preserves legal comparison and adverse review

The standalone guide MUST preserve a neutral query profile, juridical fragment roles, the norm-to-remedy graph, proportionality and balancing questions, exact and structural discovery routes, source-role separation, deduplication, at least one adverse or limiting search, and explicit transfer and non-transfer analysis. Similarity, rank, counts, and the number of matching attributes MUST remain diagnostic and MUST NOT establish legal authority, admissibility, readiness, outcome, or human approval.

#### Scenario: Candidate is discovered

- **WHEN** a bundled map, index, official search, or actually available external discovery route returns a candidate
- **THEN** the workflow identifies the speaker and fragment role and compares the norm edition, judicial meaning, mechanism, harm, right, test, outcome, remedy, institutional context, and transfer limits

#### Scenario: Strong analogy is evaluated

- **WHEN** a candidate appears to support the working hypothesis
- **THEN** the workflow searches for an adverse, limiting, distinguishable, or later position and an unexplained conflict prevents use as supporting authority

#### Scenario: Discovery material is not an official act

- **WHEN** a channel, media item, commentary, index, abstract, or rank points to a possible decision
- **THEN** it remains discovery material and does not become a legal position or gain authority without the official full text and exact locator

### Requirement: Retrieval output uses the canonical ResearchFinding contract

Each candidate handoff MUST use the existing `ResearchFinding` fields `source_anchor`, `locator`, `relation`, `verification_status`, and `limitations`. Relation MUST be one of `supports`, `weakens`, `distinguishes`, or `blocks`; verification status MUST be one of `candidate`, `verified`, `rejected`, or `superseded`. The output MUST also record query variants or routes, checked-at/as-of information, coverage limits or access errors, adverse result, what transfers, what does not transfer, and the next verification or human-review step.

#### Scenario: Official text or locator is missing

- **WHEN** the official full text, exact locator, context, or actor attribution has not been checked
- **THEN** the finding remains `verification_status=candidate` and cannot be represented as verified authority

#### Scenario: Source and locator are verified

- **WHEN** the official source, full context, actor, requisites, and exact locator have been checked
- **THEN** the finding MAY become `verification_status=verified`, which proves source verification only and does not establish legal correctness, transferability, filing readiness, or approval

#### Scenario: Candidate is handed to argument work

- **WHEN** retrieval review is complete for the checked scope
- **THEN** supporting and adverse findings, provenance, coverage, limitations, and unresolved tasks are passed to the argument ledger without converting a candidate into a ready complaint paragraph

### Requirement: Retrieval cleanup preserves installed routes and user output

Removing the dead project architecture MUST NOT remove the nine juridical fragment roles, nine-link norm graph, eight balancing checks, source hierarchy, manual lexical and structural search, adverse review, transfer limits, seven familiar user-answer fields, runtime payload membership, or the owning skill backlink. Every linked bundled route MUST exist and belong to the canonical runtime payload.

#### Scenario: Replacement guide is validated

- **WHEN** the focused artifact contract runs
- **THEN** it rejects frozen project-only tokens, resolves bundled routes, verifies the preserved method and output, checks clean-room equality and owner wording, and matches the reviewed final digests

#### Scenario: Cleanup regressions pass

- **WHEN** artifact, full-suite, source-profile, runtime-profile, manifest, and OpenSpec checks pass
- **THEN** the result proves standalone runtime truthfulness and preservation only, not exhaustive research, legal correctness, admissibility, filing readiness, publication authority, or outcome prediction
