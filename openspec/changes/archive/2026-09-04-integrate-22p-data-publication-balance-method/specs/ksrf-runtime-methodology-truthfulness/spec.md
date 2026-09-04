## MODIFIED Requirements

### Requirement: Installed retrospective examples use user-facing two-pass language

The six installed KSRF worked examples MUST describe their method in language a user can follow without an evaluation harness. They MUST distinguish the initial material, a portfolio frozen before comparison, and the later official act. They MUST NOT instruct the user to run an unavailable benchmark, forward test, eval contour, replay, fixture, blind firewall, hash/private evaluation run, or artifact commit. The installed examples MUST NOT retain the evaluation labels `Input-only`, `Outcome-blind`, or `Held-out outcome`. A canonical English contract label MAY appear elsewhere only when it is needed to identify an existing interface and the same sentence explains the concrete action in plain Russian.

#### Scenario: User opens a retrospective example

- **WHEN** any of the six worked examples was prepared after the later KSRF act became known
- **THEN** it says that it is neither a complaint template nor a prediction and instructs the reader to freeze initial findings and gaps before comparing with the act

#### Scenario: Later act is opened

- **WHEN** the initial-material analysis and hypothesis portfolio have been recorded
- **THEN** the reader opens the official full text, verifies the exact locator, KSRF as actor, context, and applicable norm version for every substantive later-act point, and records convergence, divergence, falsifiers, source limits, and lessons without treating the match as predictive validation

#### Scenario: One later-act point lacks official support

- **WHEN** an exact official locator, actor, context, or applicable norm version cannot be established for a substantive point
- **THEN** that point is explicitly marked unverified and is not usable as authority, even if a summary or known outcome appears consistent with it

#### Scenario: Active new case has no later act

- **WHEN** the two-pass checklist is applied to an active case for which no later KSRF act exists
- **THEN** the reader stops after the initial-material portfolio, proceeds through the ordinary legal gates and human choice, and does not simulate a second pass

#### Scenario: Official comparison source is unavailable

- **WHEN** the official full text or an exact locator for a retrospective conclusion cannot be verified
- **THEN** the second pass stops and the conclusion remains unverified rather than being inferred from a summary, mirror, or known outcome

### Requirement: Public documentation distinguishes retrospective examples from blind evaluation

`README.md`, `docs/KSRF_SKILLS_METHODOLOGY.md`, and `docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md` MUST state that the six installed cards are retrospective and were prepared after the later acts became known, so they are not evidence of blind evaluation or predictive accuracy. The same files MUST state that development evals are source-only and excluded from user installation. If a registered blind workflow is named, the documentation MUST explain in plain Russian that it requires a separate frozen input without the known outcome and cannot be inferred from the six cards.

#### Scenario: User reads public methodology documentation

- **WHEN** a reader compares the six retrospective cards with the described expert evaluation workflow
- **THEN** the documentation presents them as separate artifacts with separate evidence and makes no capability or validation claim based on the cards

#### Scenario: Public documentation explains the two routes

- **WHEN** the reader has an active matter without a later KSRF act
- **THEN** the documentation stops after the first-pass portfolio and directs the reader through ordinary legal gates, while a historical second pass requires the official full text and exact per-point support

### Requirement: Development eval remains source-only

The current `ksrf-explore-arguments/evals/evals.json` (SHA-256 `908064c36f2861daee3c8c4d3f63ff0984d5f43ba194649efd6cbd7868d78ab8`), `ksrf-explore-arguments/evals/trigger-evals.json` (SHA-256 `07e060025b7e8a94439c89f2afc4354e5ca4d70f419094aad5d8b69eb5ee81d4`), and `ksrf-complaint-qa/evals/evals.json` (SHA-256 `b8b7220f54d9ff1a54c1e67300be8735f38914c22188c67b05cec750931e43b4`) MUST remain byte-identical after review, validated by the source profile, and excluded from the runtime payload. The six example filenames and owning-skill backlinks MUST remain stable, and clean-room installation MUST contain the examples but no `evals` directory.

#### Scenario: Source release QA runs

- **WHEN** the source profile validates the package
- **THEN** it validates all digest-bound eval artifacts separately from the user-facing examples

#### Scenario: Clean-room install is created

- **WHEN** the exact manifest payload is installed to an empty directory
- **THEN** all six retrospective cards are present, the private complaints remain absent, and no `evals` directory is installed
