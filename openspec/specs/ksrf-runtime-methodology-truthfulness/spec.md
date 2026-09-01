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

