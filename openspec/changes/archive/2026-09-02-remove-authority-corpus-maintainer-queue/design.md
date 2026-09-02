## Context

The corpus builder is now root-only, but its prebuilt runtime outputs still contain maintainer state. Three source records disclose repository-local `ТЗ/...` paths. A separate top-level queue and Markdown table expose 31 future extraction targets whose focus strings are planning hypotheses, not verified scholarly propositions. A later manual addendum explains that this queue is already stale and points to two maintained card collections.

The external source inputs needed for a full rebuild are not shipped. This change therefore has to update the checked-in outputs exactly and update the root builder's future output contract without pretending to reproduce the corpus from unavailable inputs.

## Goals / Non-Goals

Goals:

- remove unusable local coordinates and stale maintainer queue data from runtime;
- preserve the entire searchable authority/work registry and provenance roles;
- retain a concise truthful route to reviewed method cards;
- make future builder output conform to the cleaned schema;
- publish and install one exact tested payload.

Non-goals:

- re-run extraction or rebuild the corpus;
- change any authority identity, work, status, route, method card, source count, or legal boundary;
- promote a research lead or infer an author's position from the removed planning text;
- remove maintainer OpenSpec, tests, or release tooling from the source repository.

## Decisions

1. **Schema version 2.0.** Removing two published JSON keys is a breaking schema change and is disclosed rather than hidden under version 1.0.
2. **Delete the queue, do not relabel it.** `target_methods` are maintainer hypotheses and can be mistaken for author holdings. The 31 authors and 276 work links remain discoverable in normal authority rows.
3. **Preserve provenance without local coordinates.** Each source keeps `kind`, `label`, `coverage`, and public `url` when one exists; each work keeps its source identity, bibliography and URL fields. Project-local file locations are neither provenance authority nor runtime capability.
4. **Replace stale framing with live routes.** Markdown removes the wave table and historical addendum, then adds a short snapshot disclosure with clickable links to `constitutional-methodology-verified-cards.md` and `constitutional-methodology-reference-only-corpus.md`.
5. **Patch outputs and builder together.** The checked-in JSON/Markdown are edited deterministically because the external inputs are absent. The root builder drops queue serialization/rendering and local hints so the cleanup survives any later authorized rebuild.
6. **Semantic preservation gate.** Tests and release review pin schema, absence of retired fields and paths, exact counts, source/status summaries, authority IDs, corpus routes, output hashes, manifest tree and clean-room runtime.
7. **Portable fail-closed validation.** Both validation profiles require and parse the exact corpus JSON; reject malformed structure, a schema other than 2.0, recursively nested retired keys and `ТЗ/` coordinates; pin the canonical warning, status/route legends, source kinds and complete semantic SHA; derive status and review flags from method cards, curated full-text and allowlisted source evidence; recompute every summary counter; require unique identities/routes, declared work sources and genuinely public HTTP(S) URLs. Runtime strict therefore proves this boundary after installation, and a coherent mutation cannot approve itself by updating derived fields together.

## Risks / Trade-offs

- **A user relied on the old JSON queue key** → bump the schema to 2.0 and preserve all real authority/work records; the retired key was undocumented maintainer state.
- **Useful research direction is lost** → only unverified planning phrases are removed; authors, works and routes remain, while reviewed method-card collections receive clearer links.
- **Provenance becomes weaker** → retain source identity/coverage and public URLs, plus every work-level source field; only unusable repository coordinates disappear.
- **A future rebuild restores the clutter** → update and test the root builder in the same atomic change.
- **Manual patch drifts from unavailable inputs** → compare the semantic projection and exact record counts before and after; do not touch authority rows.

## Migration Plan

1. Freeze live base, output hashes, semantic projection, queue membership and runtime manifest.
2. Record and strictly validate this OpenSpec change before implementation.
3. Add RED tests for schema 2.0, retired-key/path absence, registry preservation, maintained-card links and future builder output.
4. Update builder and exact JSON/Markdown outputs, then regenerate the manifest from live base.
5. Run focused/full tests, source strict, clean-room runtime strict, OpenSpec strict, manifest verification and independent reviews.
6. Commit on the isolated branch, merge atomically, publish `main`, confirm live SHA and install the exact payload.
7. Archive the change, regenerate the manifest from the merge SHA and publish the final evidence commit.

Rollback is a normal revert of the atomic release. No user data migration or destructive external action is involved.
