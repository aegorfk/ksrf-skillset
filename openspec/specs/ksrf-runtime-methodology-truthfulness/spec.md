# ksrf-runtime-methodology-truthfulness Specification

## Purpose
Define fail-closed truthfulness and preservation requirements for installed KSRF methodology, including the runtime graph, curated evidence guide, live argument guide, and shipped autocollect candidate contract.
## Requirements
### Requirement: Installed methodology does not present unshipped tools as capabilities

The installed KSRF argument-pattern methodology MUST describe only executable skill routes and explicit human or model analysis steps. Generated runtime references MUST NOT represent a proposed or nonexistent tool as an available capability through a `tool:*` node, `automation_hook` kind, `supported_by` relation, or an unlabeled `Автоматизация` section. Maintainer automation metadata MAY remain in source-only files excluded by the canonical payload contract. Removing runtime claims MUST NOT remove the underlying legal patterns, proof tasks, evidence, falsifiers, decision anchors, or human-review gates.

#### Scenario: Constitutional graph is generated

- **WHEN** the canonical root-only enrichment generator builds the runtime graph
- **THEN** the graph contains no `tool:*` ids, `automation_hook` node kinds, or `supported_by` edges and preserves every non-automation node and edge

#### Scenario: Curated evidence map is installed

- **WHEN** the manifest installs the curated runtime `evidence-maps.md`
- **THEN** every pattern retains non-empty proof tasks, evidence, falsifiers, and decision anchors and the guide contains no `Автоматизация` block

#### Scenario: User follows the installed graph route

- **WHEN** `ksrf-argument-patterns` routes a user to the constitutional graph
- **THEN** its guide describes the artifact as a legal-methodology navigation graph and lists only relation types present in the graph

#### Scenario: Runtime payload is validated

- **WHEN** the exact manifest payload is installed to a clean directory
- **THEN** no user-facing Markdown or JSON in the argument-pattern package contains the removed capability vocabulary, while excluded source-only metadata is not treated as a runtime violation

#### Scenario: Runtime graph is structurally malformed

- **WHEN** a graph has missing, blank, or non-string structural fields, duplicate node IDs, or an edge whose endpoint is absent
- **THEN** portable validation fails closed with an invalid-contract finding before treating it as a clean graph

### Requirement: Generated cleanup is provenance-preserving

The canonical source generator MUST remain the owner of the constitutional graph and source-only evidence metadata, but MUST NOT overwrite the curated runtime evidence guide. Regression validation MUST compare the pre-change graph after filtering only the automation dimension with the post-change graph and MUST fail if any unrelated node or edge disappears or changes. Source/release QA and publication authority remain independent of this content cleanup.

#### Scenario: Non-automation graph record changes

- **WHEN** a cleanup modifies or removes a node or edge outside the explicit automation dimension
- **THEN** regression validation blocks publication

#### Scenario: Source-only evidence metadata is refreshed

- **WHEN** the root generator writes `evidence_maps.json`
- **THEN** it preserves maintainer metadata outside installation and leaves `evidence-maps.md` byte-for-byte untouched

#### Scenario: Curated runtime guide is absent

- **WHEN** the root generator targets a skill directory without `evidence-maps.md`
- **THEN** it exits before reading corpus input or writing generated artifacts and does not report the absent guide as generated

#### Scenario: Cleanup tests pass

- **WHEN** generator and artifact tests report success
- **THEN** the result proves only structural truthfulness and preservation, not legal correctness, filing readiness, or publication authority

### Requirement: Installed collector guidance distinguishes candidates from capabilities

The installed KSRF methodology MUST distinguish shipped candidate extraction from verified legal analysis, explicit human or model steps, and unimplemented functions. Runtime references MUST NOT present a future product roadmap, proposed automatic function, or nonexistent tool as an available capability. A manual factual heuristic MUST be labelled as a check or signal rather than an automatic detector. Maintainer planning MAY remain only in source-only files excluded by the canonical payload contract. Removing runtime claims MUST NOT remove an executable collector, its output schema, underlying legal patterns, proof tasks, evidence, structural templates, downstream skill routes, or human-review gates.

#### Scenario: Offline collector output is documented

- **WHEN** the runtime includes `ksrf_autocollect.py`
- **THEN** `ksrf-tool-layer.md` names each shipped per-document and `summary.*` candidate path, states its exact boundary, and routes legislative-history and international/comparative work without claiming those packages are emitted

#### Scenario: Live argument guide is installed

- **WHEN** the manifest includes `ksrf-complaint-cycle/references/ksrf-live-argument-patterns.md`
- **THEN** the guide contains its corpus boundary, argument patterns, templates, a link to the shipped collector contract, and shipped-skill routes but no `Функциональность для максимальной автоматизации` section or TOC anchor

#### Scenario: Manual heuristic is described

- **WHEN** the guide identifies facts that should trigger closer analysis
- **THEN** it calls them a `Проверочный сигнал` and does not imply that an automatic detector runs

#### Scenario: Exact cleanup is reviewed

- **WHEN** the frozen guide is projected into the new runtime guide
- **THEN** only the exact TOC row, roadmap section, two labels, two dead routes, and collector-contract link change and the expected projection hash matches

#### Scenario: Existing skill follows the guide

- **WHEN** any routed skill opens the live argument guide
- **THEN** the guide still routes it to the shipped KSRF skills named under `Как использовать в скиллах`, without referring to a removed constructor or QA map

### Requirement: Live-guide cleanup is content-preserving

Regression validation MUST preserve exact user-operational content outside a removed planning dimension and MUST fail if an unrelated section or route disappears. Source/release QA and publication authority remain independent of this content cleanup.

#### Scenario: Unrelated guide content changes

- **WHEN** cleanup changes text outside the exact roadmap, TOC row, approved label substitutions, or two approved dead-route rewrites
- **THEN** the preservation-hash regression blocks publication

#### Scenario: Cleanup tests pass

- **WHEN** artifact and payload tests report success
- **THEN** the result proves only runtime truthfulness and preservation, not legal correctness, filing readiness, or publication authority

### Requirement: Hearing-derived checks do not confer scalar legal readiness

Installed hearing-derived methodology MUST preserve qualitative positive, adverse, and missing-evidence signals as independent checks. It MUST NOT total, average, weight, or otherwise convert them into admissibility, legal correctness, filing readiness, promotion authority, or an expected case outcome. A confirmed criterion MUST NOT compensate for a warning, insufficient data, or a failed or unknown canonical hard gate.

#### Scenario: Pattern or justification is checked

- **WHEN** a hearing-derived pattern is applied to case material
- **THEN** the result records `подтверждено`, `предупреждение`, or `недостаточно данных` for that criterion with its material, without a plus/minus or numeric score

#### Scenario: Multiple dimensions are reviewed

- **WHEN** the final pattern or justification dimensions have been assessed
- **THEN** every dimension remains independent and no sum range labels the complaint workable, incomplete, or an ordinary appeal

#### Scenario: Canonical hard gate is unresolved

- **WHEN** application, evidence, exhaustion, time limit, remedy, release, or another canonical gate is failed or unknown
- **THEN** positive hearing-guide signals do not cure that status or authorize promotion or filing

### Requirement: Scalar cleanup preserves hearing-derived methodology

Removing scalar-readiness language MUST NOT remove argument patterns, constitutional justifications, techniques, corpus boundaries, evidence questions, drafting formulas, source fragments, packages, payload membership, or consuming-skill routes.

#### Scenario: Hearing guides are projected

- **WHEN** scalar labels and aggregate rubrics are replaced
- **THEN** all 15 pattern checks, 14 justification checks, 11 technique checks, six pattern dimensions, five justification dimensions, and all approved surrounding content remain

#### Scenario: Ordinary automatic language is encountered

- **WHEN** a guide discusses norm-driven `автоматизм` or an `автоматический` legal effect
- **THEN** that substantive language remains because it is not a scalar-readiness claim

#### Scenario: Cleanup tests pass

- **WHEN** the artifact and payload regressions pass
- **THEN** the result proves only truthful presentation and preservation, not legal correctness, admissibility, filing readiness, publication authority, or outcome prediction

### Requirement: Complaint-QA argument quality remains non-compensating

Installed complaint-QA methodology MUST preserve its six argument-quality criteria and their positive, adverse, partial, and unresolved conditions as independent checks. It MUST NOT total, average, weight, or convert them into a principal/reserve selection, legal verdict, admissibility result, filing readiness, or expected outcome. A confirmed criterion MUST NOT compensate for a warning, insufficient data, or a failed or unknown canonical gate.

#### Scenario: Argument quality is checked

- **WHEN** the detailed QA workflow reviews an argument
- **THEN** each applicable criterion records `подтверждено`, `предупреждение`, or `недостаточно данных` with the supporting or missing material and without a numeric score

#### Scenario: A criterion is unresolved

- **WHEN** the available record cannot resolve a criterion
- **THEN** `недостаточно данных` creates a blocking collection or verification task for that argument and is not treated as partial credit, a warning, or a pass

#### Scenario: A genuinely new line has no claimed corpus pattern

- **WHEN** corpus support is not claimed and the direct official anchors have been checked
- **THEN** the corpus criterion records `подтверждено` without inventing a matching pattern or treating novelty as a defect

#### Scenario: Argument use is decided

- **WHEN** the workflow considers principal use, repair/support, auxiliary/rework, or removal
- **THEN** the decision follows the affected independent checks, separately passed canonical gates, and required human selection rather than a summed range

### Requirement: Complaint-QA scalar cleanup preserves substantive guidance

Removing the scalar rubric MUST NOT remove any of the six dimensions, eighteen baseline cell meanings, four practical actions, unrelated workflow guidance, table-of-contents route, payload membership, or consuming-skill backlink.

#### Scenario: Detailed workflow reference is projected

- **WHEN** the scalar section is replaced
- **THEN** the final reference preserves all approved content outside the target section and retains the full substance of the target criteria and actions

#### Scenario: Cleanup regressions pass

- **WHEN** full-reference, structure, payload, and backlink checks pass
- **THEN** the result proves only truthful non-scalar presentation and preservation, not legal correctness, admissibility, filing readiness, publication authority, or outcome prediction

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

### Requirement: Installed future-feature guidance resolves to executable routes

Installed KSRF methodology MUST NOT present an indexer, builder, constructor, recommender, selector, tracker, automatic clusterer, or other future product idea as an available runtime capability unless that component and its callable contract ship in the canonical payload. A user goal retained from a roadmap MUST instead point to an executable installed route, state its bounded output, and preserve its official-source, coverage, adverse, transfer, and human-choice limits.

#### Scenario: User opens a complaint-pattern guide

- **WHEN** an installed `complaint-patterns.md` describes how to pursue a useful goal
- **THEN** it names a real shipped skill or reference and a user-verifiable output rather than an unavailable product role

#### Scenario: Additional tooling is absent

- **WHEN** no optional connector or project infrastructure is available
- **THEN** the route remains usable through bundled methodology and official sources and records the narrower coverage

#### Scenario: A previously future workflow now ships

- **WHEN** installed methodology discusses the executable `PracticeAnalysisGate`
- **THEN** it points to the current runtime integration contract and does not continue to call the workflow future automation

### Requirement: Live routes preserve each roadmap goal without automated legal choice

The replacement routes MUST preserve similar-position search, practice mapping, remedy formulation, argument-material selection, and preservation review. Similar-position work MUST produce canonical candidate findings; practice mapping MUST expose the checked scope and legal distinctions; remedy and portfolio work MUST expose alternatives for a human decision; preservation review MUST bind the proposition to an exact lower-court document and locator. If the installed collector already emits relevant candidate artifacts, the route MUST name their exact keys and MUST preserve each candidate-only limitation. SКO material MAY support discovery or methodology but MUST NOT be attributed as an official KSRF holding without the official act.

#### Scenario: Remedy options are prepared

- **WHEN** the user needs a formulation of the requested relief
- **THEN** the route produces a primary and a narrower supported option and leaves selection to the user or lawyer

#### Scenario: Preservation is reviewed

- **WHEN** the workflow checks whether the constitutional issue was preserved below
- **THEN** it records the document, procedural stage, date, exact locator, norm, and proposition or reports the proof as missing

#### Scenario: Practice is mapped

- **WHEN** multiple lower-court acts are compared
- **THEN** the route distinguishes facts and judicial meaning, records inclusion/exclusion and adverse material, and does not infer stable or exhaustive practice from clustering alone

### Requirement: Replaced runtime blocks keep stable files and verifiable links

The three existing `complaint-patterns.md` paths, the judicial-meaning acquisition guide, and their owning backlinks MUST remain stable. Every new local Markdown route MUST resolve to a regular file included in the canonical runtime payload and in a clean-room installation. Content outside the three replaced blocks and the one corrected future-contract sentence MUST remain unchanged except for separately specified backlink and public-documentation edits.

#### Scenario: Runtime contract is validated

- **WHEN** the focused regression runs
- **THEN** it rejects the frozen roadmap labels and automated-choice implications, verifies exact outside-block preservation, resolves all local links in source and clean-room payloads, and matches reviewed target and owner digests

#### Scenario: Cleanup validation passes

- **WHEN** artifact, full-suite, source-profile, runtime-profile, manifest, and OpenSpec checks pass
- **THEN** the result proves truthful routing and preservation only, not tool availability, exhaustive research, legal correctness, filing readiness, publication authority, or outcome prediction

