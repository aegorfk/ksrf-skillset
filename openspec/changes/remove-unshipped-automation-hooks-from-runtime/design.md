# Design: Truthful runtime argument graph

## Context

`tools/enrich_ksrf_argument_patterns.py` stores three English `automation_hooks` per pattern, emits them as `tool:*` / `automation_hook` nodes in `constitutional_graph.json`, connects patterns to them with `supported_by`, and repeats them under `Автоматизация` in `evidence-maps.md` and `evidence_maps.json`. Repository search finds no consumer that implements or invokes these names. The graph is explicitly routed from the installed `ksrf-argument-patterns/SKILL.md`, so users can reasonably read the nodes as shipped capabilities.

## Decision

1. Preserve the unshipped automation dimension only as maintainer metadata: the dataclass field, 58 labels, and source-only `evidence_maps.json` remain unchanged.
2. Stop projecting the metadata into user runtime: no automation Markdown sections, graph nodes, or graph edges.
3. Update the runtime graph JSON by a lossless projection of the frozen artifact and update the canonical root-only generator to emit the same graph schema. Do not rerun a corpus extraction whose historical analysis input is not versioned.
4. Remove only the `Автоматизация` blocks from the curated Markdown evidence map. Its separately added admissibility overlay, contents, source-proof warning, and all pattern sections remain byte-preserved outside the removed blocks.
5. End the generator's ownership of curated `evidence-maps.md`: `write_evidence_maps()` may refresh only source-only `evidence_maps.json` and MUST leave the Markdown guide untouched. The CLI fails before reading corpus input or writing artifacts when the curated guide is absent, so its completion summary cannot claim a nonexistent reference.
6. Keep every user-operational dimension: pattern identity/title, constitutional articles, norm and harm types, primary applicability rule, proof tasks, evidence, falsifiers, pattern relations, remedies, decision anchors, and demand formulas.
7. Make the graph guide self-describing: it is a legal-methodology navigation graph and its usage section lists only relation types present in the JSON.

## Verification

- RED tests must fail on the frozen base because generator source, Markdown, JSON nodes, and edges still contain the unshipped automation dimension.
- Generated graph must contain exactly 0 `automation_hook` nodes, 0 `tool:*` ids, and 0 `supported_by` edges.
- Portable validation must reject malformed graph objects, non-string or blank structural fields, duplicate node IDs, and dangling edge endpoints before semantic capability checks.
- The source-only JSON evidence map must remain byte-identical and retain exactly 20 pattern entries with maintainer `automation_hooks`; the runtime Markdown map must preserve all user-operational sections with no `Автоматизация` heading.
- Graph must preserve every non-automation node and edge from the frozen artifact byte-for-byte as unordered JSON records; only the 58 nodes and 60 edges in the removed dimension may disappear.
- Source strict, clean-room runtime strict, OpenSpec strict, package tests, publication verification, exact global install, and independent review remain required.

## Risks and controls

- **Useful methodology is accidentally removed.** Compare old and new graph records after filtering the automation dimension and assert all evidence-map operational fields remain populated.
- **Generated artifacts drift from the generator.** Unit-test the canonical graph builder and source-only metadata writer directly, validate committed output invariants and the frozen non-automation projection hash, and prove the metadata writer cannot mutate the curated runtime guide.
- **A hidden consumer relies on the old labels.** Repository-wide reference audit and tests establish that no runtime script consumes the graph relation; maintainer metadata remains available in source-only JSON.
- **A malformed graph bypasses the automation check.** Structural fail-closed validation requires exact node/edge fields, unique IDs, and referential integrity without whitelisting future valid kinds or relation types.
- **Cleanup is mistaken for implemented automation.** Documentation explicitly says no new automation is introduced.
