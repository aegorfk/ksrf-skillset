# ksrf-academic-method-ingestion Specification

## Purpose
Define how the existing sixteen-package KSRF skillset may absorb reusable methods from scholarship and practice materials while keeping books, bibliographic locators, private originals and source archives outside runtime. The specification binds source inventory, overlap control, operationalization, adverse checks, current official Russian anchors and bounded release evidence.
## Requirements
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

### Requirement: Constitutional fact proof routes preserve source dependence
The complaint route SHALL distinguish a fact's descriptive or inferential mode, each concrete channel instance, its canonical dependency-DAG evidence, origin and dependency group, adversarial test availability and maximum supported inference before treating multiple documents as corroboration. Dependency status SHALL remain separate from support quality.

#### Scenario: One report appears through three actors
- **WHEN** a party files a report, an expert cites it and a court reproduces the same report
- **THEN** the three channels remain one underlying dependency group
- **AND** each channel has its own stable route/channel-instance identifier
- **AND** dependency and support statuses are not collapsed into one label
- **AND** repetition through different actors is not counted as independent proof of an individual fact.

### Requirement: Question substitution is tested before constitutional framing
The autonomous reasoning route SHALL freeze the material legal question only before exposure to a salient analogy or known outcome, identify an easier substituted question and repeat the inference under a changed exposure order only through fresh isolated reviewers bound to the same input when order may have affected framing. A reviewer already exposed to the item SHALL use a marked post-exposure reconstruction and SHALL NOT claim an independent or outcome-blind baseline.

#### Scenario: Famous favorable case was visible before any baseline
- **WHEN** the known outcome was already exposed and encourages the analyst to ask whether the result is unfair or similar instead of which normative criterion caused the harm
- **THEN** the route records a post-exposure reconstruction, the easy proxy and a result-changing rival hypothesis without inventing a frozen baseline
- **AND** the result is marked context-contaminated and is not described as independent or outcome-blind
- **AND** missing direct or implicit application evidence remains a gap rather than being supplied by analogy.

#### Scenario: Same record in reverse order through fresh reviewers
- **WHEN** two fresh isolated reviewers receive byte-identical underlying records and the salient authority is withheld until different predeclared stages
- **THEN** each reviewer has its own pre-exposure baseline and recorded context boundary
- **AND** the issue statement and missing-evidence list remain materially stable or the change is disclosed as exposure sensitivity
- **AND** a replay by an already exposed reviewer is marked non-independent or unavailable rather than a blind order test.

### Requirement: Advisory material is classified by function, type, mode and effect
The route SHALL classify constitutional advice, consultation, expert input or institutional opinion by advisor, advisee, mandate, independence, timing, function, content type, formal mode, publicity, response, uptake and causal role, without deriving legal authority from the document's title or practical influence. It SHALL distinguish full-text/source evidence, actual delivery, publication and decision lock-in, reuse the canonical uptake ledger, and report record sufficiency separately from permitted legal use.

#### Scenario: Advice is published late but delivery is unknown
- **WHEN** an opinion is published after the operative choice was fixed but no evidence establishes when it was delivered to the advisee
- **THEN** the route records `timing_unclear` rather than a late-window candidate
- **AND** reports the record as limited or insufficient and legal use as research-only
- **AND** does not treat publication or later terminological similarity as adoption, application or a constitutional defect.

#### Scenario: Delivery after decision lock-in is proven
- **WHEN** full-text and delivery records prove that an opinion reached the advisee after the operative choice had already been fixed and no response record is available
- **THEN** the route records a late-window candidate, unknown uptake and unknown or temporal-only causation
- **AND** the late-window finding alone remains research-only without a Russian anchor, proven application and individual harm.

#### Scenario: Formally nonbinding advice is usually followed
- **WHEN** evidence suggests that an institution routinely follows formally nonbinding advice
- **THEN** de facto influence is investigated separately from legal bindingness, competence and the individual causal bridge
- **AND** habitual compliance does not by itself create a Russian legal duty or filing-ready proposition.

### Requirement: Quantified risk is separated from legal classification
The route SHALL, when an act relies on a probability, score, percentile, ratio or qualitative risk category, separately record the predicted event, time horizon, reference population, instrument and version, estimate and uncertainty, presentation format, threshold owner, error trade-off, legal criterion, actual reliance and independent grounds. It SHALL keep measurement, representation, legal-threshold, norm-application and outcome-causation statuses independent and reuse canonical indicator, application and automated-decision records when they exist.

#### Scenario: High-risk label without scale or population
- **WHEN** an adverse act uses a high-risk label but omits the event, horizon, reference group, estimate range and cutoff source
- **THEN** the label remains `risk_representation_unknown`
- **AND** the route does not infer an individual probability, a legal threshold or a constitutional defect from the category alone.

#### Scenario: Complete estimate but independent ground controls
- **WHEN** the quantitative estimate is fully documented but the same result follows from an independent sufficient ground
- **THEN** the communication audit may pass while norm causation remains unproven
- **AND** any proven court-authored norm use remains recorded on its own axis
- **AND** no complaint-ready claim is produced from numerical completeness alone.

### Requirement: Independent grounds do not erase proven implicit norm use
The application route SHALL preserve `norm_use_status=reasoning_linked_implicit` when a complete verified court-authored record proves use of the norm's precise logic, even if `outcome_causation=independent_sufficient_ground` blocks the causal-harm gate. In that combination the route SHALL NOT return `not_applied`. The classifier reason `implicit_norm_use_preserved` SHALL require non-contradicted issue and operative-logic premise records, quoted full-act spans, a court-authored operative-logic span and a diagnostic named-review marker; that raw marker SHALL NOT be represented as approval of fingerprinted content or as a substitute for the separate trusted approval ledger. An asserted but pending, incomplete, rejected or contradicted implicit-use record SHALL remain `application_unclear` and SHALL NOT be described as proven or converted to positive non-application.

#### Scenario: Implicit use and an independent sufficient ground coexist
- **WHEN** a record has a diagnostic named-review marker and non-contradicted premises supporting court-authored use of the norm's precise logic but another sufficient ground independently sustains the same result
- **THEN** implicit norm use and the independent-ground causation status are both preserved
- **AND** the admissibility-facing application status remains `application_unclear`
- **AND** trusted approval of the fingerprinted record remains independently required
- **AND** the route does not relabel the norm as not applied or produce a complaint-ready causal claim.

#### Scenario: Supporting premise is contradicted
- **WHEN** the record asserts reasoning-linked implicit norm use but either the issue premise or operative-logic premise has `inference_status=contradicted`
- **THEN** the route returns `application_unclear` with an implicit-use verification gap
- **AND** does not emit `implicit_norm_use_preserved`, `implicitly_applied_proven` or a complaint-ready causal claim.

#### Scenario: Premise name is duplicated
- **WHEN** an implicit-use record supplies the same required premise more than once, including conflicting versions in either order
- **THEN** the record is rejected as non-canonical
- **AND** ordering cannot hide a contradicted premise or produce a positive application classification.

#### Scenario: Named-review marker is absent
- **WHEN** court-authored issue and operative-logic spans are present but the record has no complete diagnostic named-review marker
- **THEN** the route returns `application_unclear` with an implicit-use verification gap
- **AND** keeps the independent sufficient ground on the causation axis without returning `not_applied`.

#### Scenario: Review timestamp is malformed
- **WHEN** an approved diagnostic marker has a nonblank reviewer but `reviewed_at` is not a parseable timezone-aware RFC 3339 timestamp
- **THEN** runtime treats the marker as incomplete and does not emit `implicit_norm_use_preserved` or `implicitly_applied_proven`
- **AND** the standalone schema rejects a syntactically malformed shape and declares the `date-time` format, while runtime additionally validates calendar/time semantics.

#### Scenario: No implicit-use candidate exists
- **WHEN** a complete independent ground is proved and the record neither asserts nor proves direct or implicit norm use
- **THEN** the existing positive non-application route may return `not_applied`
- **AND** the correction does not infer implicit use from the independent ground itself.

#### Scenario: Only a party asserts the independent ground
- **WHEN** an affirmative non-application record cites an independent-ground span attributed only to a party
- **THEN** the route does not treat that assertion as court-proven non-application
- **AND** the result remains `application_unclear` unless court or disposition evidence supplies the ground.

#### Scenario: Independent-ground assertion contradicts the causation axis
- **WHEN** an affirmative complete-independent-ground record retains any outcome-causation status other than `independent_sufficient_ground`
- **THEN** the record is rejected as internally inconsistent
- **AND** the assertion cannot overwrite the canonical causation axis.

#### Scenario: Court ground evidence contradicts the causation axis
- **WHEN** a usable court- or disposition-authored `independent_ground` span appears in a record whose outcome-causation status is not `independent_sufficient_ground`
- **THEN** both the standalone schema and runtime reject the record as internally inconsistent
- **AND** the ordinary implicit branch cannot ignore the ground and emit `implicitly_applied_proven`.

#### Scenario: Standalone schema receives duplicate premises
- **WHEN** a schema-only consumer validates two implicit premise records with the same premise name
- **THEN** Draft 2020-12 validation rejects the artifact before runtime deserialization
- **AND** schema order cannot produce a different result from runtime order.

#### Scenario: Valid ground is accompanied by an invalid extra span
- **WHEN** one court-authored independent-ground span is valid but an additional cited span is contradicted, unlocated, blank or party-authored
- **THEN** only the valid span appears in the classification evidence identifiers
- **AND** the invalid extra span cannot borrow the valid span's proof status.

#### Scenario: Cross-instance proof has no quoted content
- **WHEN** an incorporation or later independent-ground span has a locator but its quote is empty or whitespace-only
- **THEN** chain assessment and evidence binding do not treat it as positive proof of survival, incorporation or supersession
- **AND** no release receipt is emitted from that span.

#### Scenario: Intermediate review is not release approval
- **WHEN** all four implicit premises and a complete diagnostic named-review marker support the intermediate classifier
- **THEN** the classifier may return `implicitly_applied_proven`
- **AND** admissibility and release remain blocked until the separate trusted ledger approves the exact content fingerprint.

### Requirement: Wave-eight source presentation remains self-contained and role-accurate
Public documentation SHALL record all four received file-level records, exact hashes, bibliographic identities, page locators, duplicate relationships, chapter authors and overlap dispositions while separately reporting the number of independent intellectual source families. Runtime references SHALL remain usable without the files, authors, titles, identifiers or network access.

#### Scenario: Edited volume supplies only selected chapters
- **WHEN** a method comes from a chapter in an edited handbook or yearbook
- **THEN** the chapter authors receive the methodological attribution and the volume editors remain identified as editors
- **AND** unrelated chapters do not inherit the promoted-method status.

#### Scenario: Exact binary was already processed
- **WHEN** a received PDF has the same SHA-256 as an archived source already represented in the method
- **THEN** both file events remain separately auditable file-level records but are recorded as one intellectual source family
- **AND** the duplicate may increase the file-record count but does not increase `independent_source_family_count`, create a second method or provide independent support.

### Requirement: Machine-readable SHALL bodies remain complete
Every changed OpenSpec requirement body SHALL keep its complete normative sentence on one physical line so `openspec show --json --deltas-only` exposes every continuation clause to machine consumers.

#### Scenario: Strict validation accepts a wrapped requirement
- **WHEN** strict validation passes but JSON projection would stop at the first physical line
- **THEN** release verification fails until the body is unwrapped and sentinel continuation clauses are visible in the JSON requirement text.

#### Scenario: Active correction is projected before archive
- **WHEN** the corrective change still exists under `openspec/changes`
- **THEN** the regression invokes `openspec show harden-implicit-application-proof-state --json --deltas-only`
- **AND** verifies the continuation clauses of both corrective deltas before capability sync and archive.
