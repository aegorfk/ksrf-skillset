## ADDED Requirements

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
