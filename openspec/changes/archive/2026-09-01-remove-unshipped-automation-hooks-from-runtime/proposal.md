# Change: Remove unshipped automation hooks from user methodology

## Why

The installed argument-pattern package currently presents 58 `tool:*` graph nodes, 60 `supported_by` edges, and 21 sections labelled `Автоматизация`. None of those named tools is shipped or invoked by the runtime. This makes a planning vocabulary look like available product functionality and adds English implementation labels to a Russian user method.

## What changes

- Preserve the 58 hypothetical labels as maintainer metadata in the root-only generator and source-only `evidence_maps.json`, outside user installation.
- Stop projecting that metadata into the constitutional graph: remove `tool:*` nodes, `automation_hook` kinds, and `supported_by` edges.
- Remove the 21 generated `Автоматизация` blocks while preserving proof tasks, evidence, falsifiers, decision anchors, and every legal pattern.
- Update the graph guide so it describes only relations that actually remain in the runtime graph.
- Add fail-closed regression tests for the generator, generated artifacts, runtime payload, and preserved legal-methodology dimensions.

## Impact

- Frozen base: `82b7174adec78da51886112c8a941e47b9dc4b3a`.
- Before the change, `constitutional_graph.json` has 320 nodes / 549 edges / 119,693 bytes, including 58 hypothetical automation nodes and 60 hypothetical support edges.
- Before the change, `evidence-maps.md` has 21 `Автоматизация` blocks.
- Affected source and runtime: root-only enrichment generator, generated argument-pattern references, source tests, manifest, and public documentation. The source-only evidence-map JSON remains byte-identical at SHA-256 `54122e7543c72095497ecb4a8147afa62d8bcdbf19193ca09e1438db7d5fb4be`.
- Final graph: 262 nodes / 489 edges / 103,819 bytes; its non-automation projection SHA-256 is `9fd839ea969abaa233f06cd4fa628fa1a1ed270e4df0d7de785bdb7938db6325` and file SHA-256 is `fe5779f57478d79a3c3b6ecbed4405a9f1a8232858cac8d18197c51f265c7f23`.
- Final runtime: 15 packages / 235 files / 8,051,942 bytes, tree SHA-256 `773ec1292043405ddbb76a2d5c400dc5ba950bfe736fea846d2dd0120d901c5f`; net reduction from the frozen base is 13,618 bytes with no file loss. Release tree: 9 files / 197,557 bytes, SHA-256 `ef4d7395c10f436b13f4cd09ed450a65519a5dce78cd7f8a346b363c9ff80ddd`.

## Non-goals

- Do not implement or claim any new automation.
- Do not remove legal patterns, proof tasks, evidence, falsifiers, decision anchors, or human legal-review gates.
- Do not change the runtime payload boundary or exclude the constitutional graph itself.
- Do not clean up unrelated future-automation prose in this change; that remains a separate, reviewable topic.
