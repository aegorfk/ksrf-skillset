## Context

`position-retrieval-architecture.md` is installed as one of 33 runtime files in `ksrf-argument-patterns`. It is introduced by the owning skill as an autonomous candidate map, but the document instead binds itself to a missing project OpenSpec change and instructs the user to run a missing Docker file, nine missing Python/MCP paths, absent generated datasets, unverified localhost services, non-callable conceptual operation IDs, and stale corpus counters. The useful legal method—query construction, source-role separation, structural comparison, adverse search, and transfer review—does not depend on that infrastructure.

## Goals / Non-Goals

**Goals:**

- make the installed guide usable from the skillset alone;
- preserve the legal search and transfer method without pretending that a retrieval backend ships;
- use the existing `ResearchFinding` contract and its statuses instead of inventing another result schema;
- make official full text, exact locator, actor attribution, adverse review, provenance, and transfer limits explicit gates;
- keep the filename and exact runtime backlink stable;
- prove removal and preservation with focused RED/GREEN tests and an exact final digest.

**Non-Goals:**

- ship, configure, or benchmark Qdrant, Neo4j, Ollama, Langfuse, an MCP server, an embedding model, or a reranker;
- restore the missing `ks_parser_lower_court_marker` pipeline or its datasets;
- promise exhaustive discovery, legal correctness, admissibility, filing readiness, or a case outcome;
- treat similarity, rank, citation count, or a verified locator as human approval or legal authority;
- rewrite historical archived OpenSpec records.

## Decisions

1. **Rewrite in place.** Keep `references/position-retrieval-architecture.md` so saved links and the owning skill remain stable, but retitle it `Поиск и проверка похожих позиций КС РФ`. Renaming the file would add migration cost without user benefit.
2. **Bundled-first and capability-neutral.** The ordinary route uses real installed references and official full texts. An external search tool may be used only after it is actually discovered in the current environment; the guide does not prescribe names, endpoints, credentials, models, collections, or commands.
3. **Remove the whole false architecture, not only command snippets.** Delete the project/OpenSpec binding, stack and service defaults, local implementation, MCP section, maintainer evaluation framing, enrichment commands and artifacts, generated-path claims, and fixed corpus counters. Disclaimers would still leave a runnable-looking unavailable product surface.
4. **Preserve the legal method explicitly.** The replacement retains all nine juridical fragment roles, the norm-to-remedy chain, all eight balancing questions, neutral query-profile fields, exact and structural search, at least one adverse or limiting route, source-role separation, deduplication, transfer/non-transfer analysis, and the seven familiar user-answer fields.
5. **Use the canonical artifact contract.** A result records `source_anchor`, `locator`, `relation`, `verification_status`, and `limitations`, with exact relations `supports | weakens | distinguishes | blocks` and statuses `candidate | verified | rejected | superseded`. The prose phrase “только кандидат” maps to `verification_status=candidate`; `candidate_only` and `quote_locator` are not introduced as schema fields.
6. **Fail closed without overclaiming absence.** Missing official full text, locator/context/actor, norm edition, outcome/remedy, later-law check, or unresolved adverse conflict prevents `verified` or use as an authority. Timeout, access block, missing connector, or a bounded search with no hit is a coverage limitation, never proof that practice does not exist.
7. **Update the owning skill.** Its workflow and reference list describe the file as a manual search/comparison/verification route. Its tools section no longer claims Qdrant, Neo4j, shipped retrieval scripts, golden datasets, or hard-negative harnesses. Its output includes official anchor, locator, canonical status/relation, provenance/coverage, adverse result, and transfer limit.
8. **Regression shape.** Replace the existing three-assertion test with a dedicated contract that denies every frozen project-only token, verifies the preserved method and canonical schema, resolves bundled Markdown routes inside the runtime payload, copies the guide to a clean room, checks the owner backlink, and pins final file digests after review.

## Risks / Trade-offs

- **Useful method is lost with the dead stack** → preserve enumerated roles, graph links, balancing checks, search modes, source gates, output fields, and handoff semantics in tests.
- **Generic optional-tool wording recreates an implied capability** → allow optional tools only after current-environment capability discovery and forbid named services/defaults in this guide.
- **`verified` is mistaken for legal approval** → define it only as source/locator verification and keep legal review, argument selection, filing, and release separate.
- **No-hit language becomes a false negative** → require the searched routes, date, limits, and the phrase that no close analogy was found in the checked scope.
- **External users rely on the filename** → preserve the path and exact backlink while changing the title and description.

## Migration Plan

1. Freeze the live source, payload membership, consumers, missing-artifact inventory, and baseline digests.
2. Add RED contract tests against the frozen guide and owner skill.
3. Rewrite the guide and the three owning-skill references, then add user-facing documentation.
4. Pin final hashes, regenerate the manifest from live `main`, and run all suites, source strict, clean-room runtime strict, strict OpenSpec, and independent review.
5. Publish one atomic change, verify live SHA, install it globally, archive OpenSpec, regenerate the manifest from the merge SHA, and publish the evidence commit.

Rollback is the exact prior `main` commit; no data or schema migration is involved.

## Open Questions

None. The runtime boundary and canonical artifact contract already determine the safe replacement.
