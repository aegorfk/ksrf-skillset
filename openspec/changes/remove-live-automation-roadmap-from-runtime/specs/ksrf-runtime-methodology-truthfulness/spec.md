## ADDED Requirements

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
