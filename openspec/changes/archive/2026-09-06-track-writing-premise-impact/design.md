## Context

At base ddd4d7417e83ebc4d59a417086f83e2a99c5ef38, WritingWorkflow._revise invalidates objections only by edited sentence_id. A technical three-sentence probe reproduces retention of addressed statuses elsewhere. This is not evidence that those other conclusions are legally wrong.

The first real-document review is a negative/limitation case: refuting an opponent's premise does not establish withdrawal of the applicant's premise. A known historical dossier is retrospective material, not a fresh blind evaluation. No model-quality comparison or independent human legal assessment is claimed in this change.

## Goals / Non-Goals

Goals: retain declared reasons for dependencies; follow transitive consequences; keep review prompts current; cover unmapped requested-remedy sentences; preserve independent and conditional branches; show coverage limits.

Non-goals: automatic semantic extraction or validation of dependency links; predicting admission; replacing a lawyer; automatic rewriting of dependent paragraphs; new trusted approvals; new LLM evaluation pipeline.

## Decisions

1. Compose and revise accept optional `dependencies`: records with `dependency_id`, `premise_sentence_id`, `dependent_sentence_id`, `reason`. Endpoints must be distinct, known sentence IDs, including sentences without argument cards. IDs and their meanings are immutable; duplicate IDs, reused IDs with changed content, malformed values and unknown endpoints fail before saving. Cycles between different sentences may be recorded but do not establish valid reasoning; traversal uses a visited set.
2. Omission preserves existing links. Revise optionally accepts `dependency_removals`: `dependency_id` and nonempty `reason`. Retirement is explicit and retained in history; retired IDs cannot be reused. Unknown or repeated removals and ambiguous add/remove combinations fail. No automatic removal of user text occurs.
3. Apply all text edits before computing impact. Traverse the union of previous and next active links, starting at edited sentences and targets of added/retired links. This prevents a simultaneous retirement from silently bypassing a needed review. Each affected finding is invalidated once per revision, independently of edit order.
4. Each dependency-affected sentence receives a dedicated stable impact-review objection, even without a previous objection or argument card. Preserve its history and exact current review context; ordinary review still binds the whole draft and exact sentence wording. Review cannot silently remove stored impact context. Addressed remains an editorial declaration only.
   Independent implementation review found a sequential-revision risk: replacing current context could hide an earlier unresolved cause or leave an unreviewed retired-link anchor stale. Merge unresolved causes until review and refresh their anchors through later revisions, retaining history. Do not reopen already addressed retired influences merely because a former premise changes.
5. Save readable `dependency-impact.md` with the declared links, retirement reasons and affected sentence IDs/reasons. Reports always say that graph completeness and legal validity are unverified; an absent edge never proves independence. Existing original, proposed draft, diff and approval boundaries remain intact.
6. Explain the legal operation in the existing writing reference, not a new general framework: identify whose premise changed; distinguish fact, proof status, normative meaning and scope; trace necessity rather than shared vocabulary; preserve alternative conditional reasoning; reconsider remedy scope separately.

## Risks / Trade-offs

- Missing or erroneous declarations: visible incomplete coverage and mandatory substantive review, never inferred independence or automatic deletion.
- Cycles and multiple changed roots: visited-set traversal and deduplicated invalidation.
- Over-alerting after a cautious link: explicit reasoned retirement, preserved history, no text change.
- Apparent legal success from passing tests: technical tests and retrospective source review are reported separately. The comparative legal-quality hypothesis remains unmeasured until a separately traceable, held-out evaluation with independent legal review.

## Verification and Release

Run a pre-change technical regression and post-change direct/transitive/unmapped/independent/multi-edit/history/invalid-input/legacy tests. Review the real-document limitation without fabricating historical revisions or exporting sources. Then run targeted and full source tests, strict runtime/source validation, clean-room installation, OpenSpec validation/archive, privacy/publication guard, atomic push and exact live-SHA verification before canonical installation.
