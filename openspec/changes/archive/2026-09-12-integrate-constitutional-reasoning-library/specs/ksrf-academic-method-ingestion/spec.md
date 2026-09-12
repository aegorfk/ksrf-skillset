## ADDED Requirements

### Requirement: Complete provenance-bound source inventory
The skillset update SHALL inventory every supported source in the supplied inbox by exact file hash, page count, bibliographic identity, extraction status and duplicate relationship before using it as a methodological source.

#### Scenario: Duplicate edition or alternate export
- **WHEN** two supplied PDFs contain the same work or one is a layout/export variant of another
- **THEN** the source ledger records one intellectual source family and each distinct file hash
- **AND** the files are not counted as independent support for a method.

#### Scenario: Bibliographic metadata conflicts with title pages
- **WHEN** filename or PDF metadata conflicts with the title page, colophon or stable publication identifier
- **THEN** public attribution follows the verified publication evidence and records the conflict instead of guessing.

### Requirement: Operational extraction with overlap control
Every promoted source-derived method SHALL add a self-contained reproducible decision or verification operation and SHALL include a trigger, required inputs, falsifier or adverse branch and bounded output. Exact source locators and overlap disposition SHALL be retained in separate provenance documentation and SHALL NOT be runtime prerequisites.

#### Scenario: Source restates an existing method
- **WHEN** a source uses different terminology for an operation already present in the skillset
- **THEN** the existing reference may receive a source-backed clarification but no duplicate mandatory workflow is created.

#### Scenario: Competing theories of constitutional rights
- **WHEN** sources imply materially different rights models or judicial roles
- **THEN** the skill preserves parallel branches and a `model_conflict` or human-selection point
- **AND** does not select a theory by counting authors or publications.

### Requirement: Norm fact procedure and causation separation
The complaint route SHALL separately identify adjudicative facts, the explicit or implicit normative premise, procedural safeguards, causal dependence of the outcome and any independent sufficient ground before locating a constitutional defect.

#### Scenario: Court could reach the same result on an independent ground
- **WHEN** removing the challenged norm or interpretation does not change the result because another sufficient ground remains
- **THEN** norm causation remains unproven and proportionality rhetoric does not cure the gap.

#### Scenario: Procedure obscures the factual basis
- **WHEN** the record does not reveal which facts or evidentiary assumptions made the legal condition decisive
- **THEN** the route identifies a reviewability or procedural-information gap and does not invent the missing factual finding.

### Requirement: Fact-work phase and review-role separation
When an act is challenged as factually wrong, incomplete or unsupported, the route SHALL distinguish fact acquisition or assembly, deployment of the resulting fact in a legal criterion, and any legally authorized independent fact-finding by the reviewing body before classifying the defect.

#### Scenario: Applicant disputes the weight assigned to a proved fact
- **WHEN** the full record shows a lawful collection process and the complaint only asks to prefer another permissible evidentiary weight
- **THEN** the route identifies an ordinary fact dispute and does not relabel it as a constitutional defect.

#### Scenario: Review body is asked to establish the fact itself
- **WHEN** a proposed route assumes that the reviewing court will receive evidence and make its own factual determination
- **THEN** the route requires a current official Russian authority for that role, procedure and standard
- **AND** otherwise records `reviewer_own_assembly_authority_unknown`.

### Requirement: Systemic-data acquisition gap is bounded
The route SHALL treat the absence of policy-, equality- or impact-level data as an `acquisition_gap_candidate`, `refuted` or `unknown` research result and SHALL NOT infer the underlying discrimination, disproportionality or norm defect from missing data alone.

#### Scenario: Public body did not collect potentially useful data
- **WHEN** the applicant alleges that an effect cannot be tested because a public body did not acquire systemic data
- **THEN** the route identifies the exact decision and material variable, data controller, feasible collection method and burden, privacy or other countervailing limits, current official acquisition duty, causal relevance and available substitute data
- **AND** returns `unknown` if the duty, feasibility or materiality is not established.

### Requirement: Historical claim role and factual precedent are revalidated
When a historical proposition affects interpretation, proof, an institutional premise or a later case through an earlier judgment, the route SHALL classify the proposition's role, separate legal holding from factual narrative and revalidate any borrowed narrative against the primary record and current case context.

#### Scenario: Earlier judgment recites historical facts
- **WHEN** a party relies on an earlier judgment's historical narrative as if it were an authoritative legal holding
- **THEN** the route records the exact proposition, role, prior locator and context, proof route, primary materials, expert scope, competing account and opportunity to respond
- **AND** does not make the line complaint-ready without a current Russian relevance anchor, cross-case comparability, materiality and an independent-ground pass.

### Requirement: Proportionality is evidence and stage sensitive
The skillset SHALL test purpose, suitability, necessity and balancing against the facts and evidence relevant to each stage, while keeping the existence and scope of the protected right as a separate branch when sources contest it.

#### Scenario: Alternative is asserted without an evidentiary basis
- **WHEN** a less restrictive alternative is not shown to be legally available and comparably effective on the verified record
- **THEN** it remains a research question rather than proof of disproportionality.

#### Scenario: Rights scope is disputed
- **WHEN** the alleged interest may fall outside the protected scope under a competing rights model
- **THEN** the route tests both the scope branch and the justified-limitation branch and exposes the premise driving the conclusion.

### Requirement: Function-first comparative procedural transfer
Foreign constitutional procedures and institutional models SHALL be used only to identify functions, failure modes and research questions; a Russian conclusion SHALL require separate current official authority, competence and case-application evidence.

#### Scenario: Foreign guide supplies a filing rule
- **WHEN** a practical QPC or constitutional-review guide states a jurisdiction-specific filing condition
- **THEN** the condition is documented as comparative context and is not presented as a current KSRF requirement.

#### Scenario: Responsive remedy appears attractive
- **WHEN** a foreign model recommends dialogue, suspension, remand or another institutional response
- **THEN** the skill first identifies the protected function and then verifies whether a lawful effective Russian remedy exists.

### Requirement: Function and effect control labels
The complaint route SHALL classify a procedural communication, evaluative judicial term, automated output or specially named legal regime by its verified function, predicates and operative legal effect rather than its title alone.

#### Scenario: Court or staff communication affects a procedural route
- **WHEN** a letter, notice or other communication is invoked as a refusal, final act or exhaustion event
- **THEN** the route records issuer and status, resolved request, reasoning, operative consequence and available review
- **AND** does not promote the communication to a judicial act or exhaustion event without current legal authority and the full document.

#### Scenario: Higher-court term is repeated without its predicates
- **WHEN** a lower act repeats an evaluative term or label from a higher court
- **THEN** the route reconstructs the term's definition, factual predicates, scope and operative role
- **AND** treats a label-only match as insufficient to establish the same legal meaning.

#### Scenario: Automated output contributes to an adverse decision
- **WHEN** a digital system, registry match or automated criterion may have affected an adverse legal result
- **THEN** the route seeks the normative authorization and version, input sources and conflicts, criteria, notice and response, real human review, audit trace, reliance, remedy and causal bridge
- **AND** returns an explicit normative or evidence gap instead of treating technical error as a constitutional defect.

### Requirement: Prior constitutional decision and related-norm continuity
When a prior constitutional decision is invoked against a later, reproducing, derivative or allegedly analogous norm, the route SHALL compare the exact normative function and effect and SHALL verify the later norm's independent application to the applicant.

#### Scenario: Later norm reproduces the same burden through another provision
- **WHEN** the challenged text differs but the applicant alleges that the same trigger, addressee, condition, exception and consequence were recreated
- **THEN** the route records the relationship as direct reproduction, derivative implementation, functional analogy or no established continuity
- **AND** does not infer invalidity or admissibility merely from textual similarity or the earlier decision.

#### Scenario: Absence of citation is described as non-application
- **WHEN** an act does not cite a constitutional or statutory provision
- **THEN** the route distinguishes authoritative inapplicability, ordinary-court non-use, incidental omission and unproven status
- **AND** preserves the separate implicit-application gate when the provision's normative logic may nevertheless have determined the outcome.

### Requirement: Special-regime externality and burden review
When a measure is described as special, temporary, experimental, emergency or digital, the rights route SHALL test its real public- and private-law effects, affected third parties, concentration of burdens, duration, exit, review, alternatives and compensation without assigning weight to the label itself.

#### Scenario: Public-law measure shifts costs into private relations
- **WHEN** a regime regulates one public objective but predictably changes contracts, property, work or access for a narrower group
- **THEN** the proportionality record identifies each downstream effect, burden bearer and legal bridge
- **AND** the existence of a special regime does not create a presumption of constitutionality or judicial deference.

### Requirement: Concise discoverable skill architecture
Operational detail SHALL reside in descriptively named, directly linked reference files, while each affected `SKILL.md` remains a concise router with specific user-facing triggers. Runtime references SHALL remain usable without the books, local source archive or external retrieval.

#### Scenario: New material is relevant only after a matched trigger
- **WHEN** a matter does not raise fact classification, proportionality, procedural review, institutional transfer or the other named trigger
- **THEN** the agent is not instructed to load the corresponding book-derived reference.

### Requirement: Exact public authorship and source presentation
Public documentation SHALL name verified authors, editors and institutional issuers in their correct roles and provide the work title, year and stable public identifier or source link when available.

#### Scenario: Only the local full text is available
- **WHEN** no lawful stable public full-text link is verified
- **THEN** the documentation may identify the publication from verified bibliographic evidence without publishing the file or implying open access.

### Requirement: Bounded evaluation and sixteen-package release
The update SHALL include realistic trigger, near-miss, adverse and changed-premise tests and SHALL preserve all sixteen packages in the current manifest-covered release.

#### Scenario: Structural and synthetic checks pass
- **WHEN** references, navigation, source bindings and synthetic scenarios pass
- **THEN** the release may claim those bounded properties only
- **AND** does not claim improved acceptance rates, correct real-case legal outcomes or filing authority.
