# Design: Keep the live guide methodological, not aspirational

## Context

The installed guide has two distinct roles: it preserves argument techniques derived from public materials, and it routes users to executable KSRF skills. The section `Функциональность для максимальной автоматизации` adds a third, confused role: eight blocks loosely correspond to real or partial `ksrf_autocollect.py` outputs, while legislative-history collection and an international/comparative packet are not emitted by the collector. The prose does not use the actual CaseFile keys and frequently presents candidates as completed legal analysis.

## Decision

1. First add a compact operational table to `ksrf-tool-layer.md` for the exact emitted paths: `summary.document_passports`, `summary.application_bridge_candidates`, `summary.constitutional_test_suggestions`, `summary.request_formula_candidates`, `summary.practice_matrix_candidates`, `summary.repeatability_review_items`, `documents[].qa_matrix` / `summary.qa_review_items`, and `summary.ksrf_execution_packets`, alongside their per-document sources.
2. State the narrow boundary of every output and say explicitly that the offline collector does not create legislative-history or international/comparative packages.
3. Apply one exact text projection to the frozen argument guide: delete the exact automation TOC row and all text from the roadmap heading up to, but not including, `## Как использовать в скиллах`.
4. Replace exactly two `Автоматический индикатор:` labels with `Проверочный сигнал:`. Their factual criteria remain unchanged.
5. Rewrite exactly two downstream bullets that would otherwise retain dead references: route `ksrf-complaint-facts-demands` to its factual-hook and KSRF-powers checks, and route `ksrf-complaint-qa` to its independent mandatory checks without a scalar score.
6. Add one sentence linking the argument guide to `ksrf-tool-layer.md`, then preserve byte order and content everywhere else. The post-change SHA is a regression invariant, not a general formatter output.
7. Do not change the collector or replace its output schema. Existing skills remain the legal-analysis owners beyond candidate extraction.

## Ownership map

| Former roadmap block | Shipped collector status | Legal-analysis owner |
|---|---|
| Document passport extraction | Shipped candidate output `document_passports` | `ksrf-case-triage`; `ksrf-complaint-facts-demands` |
| Norm-application linkage | Shipped candidate output `application_bridge_candidates` | `ksrf-complaint-facts-demands`; `ksrf-complaint-cycle` |
| Constitutional test matrix | Shipped lexical suggestions | `ksrf-argument-patterns`; `ksrf-rights-argument-builder` |
| `в той мере, в какой` request constructor | Partial: individual complaint and conditional court-request drafts | `ksrf-complaint-facts-demands`; `ksrf-rights-argument-builder` |
| Practice map | Partial: rows from local input only | `ksrf-practice-authority-builder`; `ksrf-cassation-judicial-meaning` |
| Legislative-history analysis | Not emitted | `ksrf-doctrine-research`; source/proof/impact references |
| International and comparative package | Not emitted | `ksrf-echr-argumentation`; `ksrf-rights-argument-builder` |
| Repeat/new-argument detector | Partial: KSRF references already present in input | `ksrf-case-triage`; `ksrf-argument-patterns` |
| Complaint QA map | Partial: extraction and primary content signals | `ksrf-complaint-qa`; `ksrf-formal-filing-check` |
| Post-KSRF review package | Partial: operative and route candidates | `ksrf-decision-execution` |

This map preserves both the existing executable collector and the legal work route; it does not upgrade candidate output into a verified legal conclusion.

## Verification

- RED must prove that the tool-layer guide does not yet disclose the exact shipped output contract, while the roadmap and two soon-to-be-dead route phrases remain on the frozen base.
- GREEN must prove the collector still emits the documented keys, every key has a candidate boundary, and the two absent packages are explicitly routed rather than promised.
- GREEN must also prove exact final argument-guide SHA/line/byte counts and that `## Как использовать в скиллах` plus every downstream skill route and both replacement checks remain.
- The manifest payload must still include the guide at the same package-qualified path.
- Clean-room runtime search must find none of the exact removed heading, anchor, or automatic-label vocabulary.
- Source strict, clean-room runtime strict, OpenSpec strict, full relevant tests, diff check, and independent review remain publication gates.

## Risks and controls

- **A shipped collector capability is erased or hidden.** Controlled by executable output-schema tests and the new exact tool-layer table before roadmap removal.
- **A unique legal method is lost.** Controlled by the ten-item ownership map and exact preservation hash outside the removed projection.
- **The entire useful guide is excluded.** Controlled by payload-presence and downstream-route tests.
- **Manual criteria are accidentally weakened.** Controlled by exact two-label substitution, two shipped-check route rewrites, and full-file projection SHA.
- **Documentation overclaims implementation equivalence.** Controlled by describing existing owners as work routes, not replacement services.
