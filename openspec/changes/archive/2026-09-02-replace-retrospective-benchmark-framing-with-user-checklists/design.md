## Context

The three example files ship in the user payload and are linked from `ksrf-explore-arguments/SKILL.md`. They contain valuable case-specific two-pass reasoning, but label it with internal evaluation concepts such as `Input-only`, `Outcome-blind`, `Held-out outcome`, `benchmark`, `forward-test`, `eval-контур`, `commit артефактов`, `fixtures`, and `replay`. The source-only `evals/evals.json` and `evals/trigger-evals.json` are the correct locations for development evaluation material and are already excluded from installation.

## Goals / Non-Goals

**Goals:**

- make all three installed examples readable as practical worked examples for a user;
- preserve the anti-hindsight separation between initial material, a frozen portfolio, and the later official act;
- state plainly that a retrospective card is neither a template nor a prediction;
- preserve every case-specific legal and source-integrity safeguard;
- replace maintainer regression rubrics with non-scoring checklists for a new case;
- separate topic-specific controls from transferable questions and require the new matter's own primary materials;
- require an official per-point locator or an explicit unverified/non-authority label in the later-act pass;
- make `README.md`, `docs/KSRF_SKILLS_METHODOLOGY.md`, and `docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md` describe the retrospective/eval boundary precisely;
- preserve the exact three paths, owner backlinks, runtime membership, and both source-only eval exclusions;
- prove the replacement with focused negative, structural, semantic, clean-room, and exact-digest tests.

**Non-Goals:**

- remove or weaken the two-pass anti-hindsight method;
- publish private complaints or their full-text derivatives;
- create a benchmark harness, forward evaluation, scoring system, or prediction claim;
- change case facts, hypotheses, norms, outcomes, official URLs, provenance hashes, or source roles;
- modify `evals/evals.json` or `evals/trigger-evals.json`, or include any `evals` directory in runtime;
- rewrite historical archived OpenSpec records.

## Decisions

1. **Rename the phases in plain Russian.** Initial evidence becomes `Что следует только из исходного материала`; frozen hypothesis work becomes `Портфель гипотез до сверки с последующим актом`; the later decision becomes `Что установил последующий акт КС РФ`.
2. **Keep the two-pass order explicit.** Each card instructs the reader to record initial facts, hypotheses, alternatives, falsifiers, gaps, and source limits before opening the later act. The comparison then explains convergence and divergence without implying prediction.
3. **Replace evaluation labels, not legal content.** `Research replay`, `Findings до открытия outcome`, `Adaptive replay`, and `Критерии регрессии` become user-facing search directions, pre-comparison findings, portfolio, and checklist headings. H/F identifiers and all substantive bullets remain.
4. **State retrospective limitations directly.** The card was prepared after the later act, so it can teach source separation but cannot demonstrate blind performance or predict a new case. The title itself reveals the later act.
5. **Keep development evaluation source-only.** `evals/evals.json` and `evals/trigger-evals.json` remain byte-identical and excluded by the runtime manifest; installed text contains no instructions to create fixtures, hash/private benchmark runs, or commit evaluation artifacts.
6. **Stable routes.** The owner keeps one link to each of the three files but calls them retrospective two-pass worked examples rather than replays.
7. **No invented second pass.** An active new case without a later KSRF act stops after the initial-material portfolio and proceeds through the ordinary legal gates and human choice. A historical second pass is allowed only against the official full text with exact locator, actor, context, and norm-version checks; an unavailable text or locator blocks the comparison.
8. **No aggregate score.** Every checklist question is decided independently as `подтверждено`, `пробел`, or `не применимо`; no total, pass threshold, or compensating score is calculated. Example-specific controls are labelled as such, and only the question structure is transferable to a new matter, which must be checked against its own primary documents.
9. **Per-point authority boundary.** Every substantive statement attributed to the later KSRF act includes the official structural locator, KSRF as actor, context, and applicable norm-version boundary. If any element cannot be verified, the statement is marked unverified and cannot be used as authority.
10. **Plain Russian action language.** Canonical English labels may appear only where they are necessary to name an existing contract, and each occurrence immediately explains in Russian what the user or validator actually does. The installed examples do not retain the evaluation labels `Input-only`, `Outcome-blind`, or `Held-out outcome`.
11. **Public documentation is part of the contract.** `README.md`, `docs/KSRF_SKILLS_METHODOLOGY.md`, and `docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md` state that the three cards are retrospective and not evidence of blind EVAL, source evals are validation-only and not installed, and a registered blind run requires a separate frozen input and concealed outcome.

## Risks / Trade-offs

- **Removing benchmark terms weakens anti-hindsight discipline** → require the exact two-pass sequence, “not a prediction,” and “do not fit to the later act” language in every example.
- **A retrospective match is read as validation** → state that the card was authored after the act and proves only the illustrated method in this example.
- **Case details drift during wording cleanup** → freeze act numbers, official URLs, provenance hashes, H/F identifiers, gates, result counts, transferable methods, and checklist lengths.
- **Development eval leaks back into runtime** → assert the exact SHA of both source-only eval files and clean-room absence of every `evals` directory.
- **Topic facts become universal expected answers** → label historical controls as example-specific, transfer only the question structure, and require the new matter's own primary documents.
- **A summarized holding is reused as authority** → require a per-point official locator or an explicit unverified/non-authority status.
- **Public prose overclaims blind validation** → pin truthful wording in all three named public-documentation files.

## Migration Plan

1. Freeze the four runtime files, three backlinks, both source-only eval files, headings, case-specific surface, public-documentation claims, and baseline manifest.
2. Add RED tests for forbidden maintainer vocabulary, two-pass language, legal/source preservation, per-point locators, non-scoring checklists, routes, public-documentation truthfulness, and both eval exclusions.
3. Rewrite only the evaluation framing and owner routing; update the three named public-documentation files.
4. Pin final digests, regenerate the manifest from live `main`, and run all suites, source/runtime strict validation, strict OpenSpec, exact manifest verification, and independent reviews.
5. Publish atomically, verify live SHA, install globally, archive this change, regenerate the manifest from the merge SHA, and publish the evidence commit.

Rollback is the exact prior `main` commit; no data or schema migration is involved.

## Open Questions

None. Runtime examples and source-only evals already have separate roles.
