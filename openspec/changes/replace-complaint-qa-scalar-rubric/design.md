# Design: Keep argument-quality decisions without compensating points

## Context

The owning QA skill already states that legal hard gates cannot be compensated and that argument comparison must not become an authorizing scalar score. Its detailed workflow reference nevertheless contains a six-criterion, three-level points table and a summed classification. The table is useful; its arithmetic is not.

## Decisions

1. Keep the familiar `Рубрика качества доводов` heading and its table-of-contents anchor; a rubric need not be numerical. Replace only its scalar mechanics.
2. Use the shared Russian status vocabulary:
   - `подтверждено` — the positive condition is supported by identified material;
   - `предупреждение` — a known adverse or incomplete condition is present;
   - `недостаточно данных` — the condition cannot be resolved from the available material and creates a blocking collection or verification task for that argument.
3. Treat these as heuristic results, not new hard-gate states or a legal verdict.
4. Preserve the six dimension names and all eighteen original cell meanings. Known zero/partial defects become warnings; genuinely unresolved source or draft availability becomes insufficient data.
5. Never total, average, weight, or compensate statuses. A confirmed dimension cannot cure another warning, insufficient data, or failed/unknown canonical gate.
6. Preserve the four practical actions without score ranges:
   - principal use only after every applicable check is confirmed, canonical gates separately pass, and a human selects the argument;
   - repair or support when a warning identifies a remediable weakness;
   - auxiliary/rework only by explicit human choice after the named weakness is addressed;
   - remove when a known adverse condition cannot be repaired and retaining the argument would harm the complaint.
7. Insufficient data blocks classification and principal/reserve selection for that argument until the task is resolved.
8. Every local result records a short reason and evidence identifiers or locators. Missing user-authored summary alone never creates `недостаточно данных`; the workflow first checks the dossier itself.
9. No known corpus pattern is not an adverse signal for a genuinely new line. The corpus warning applies only when the argument claims support that has not been established. When no corpus support is claimed and direct official anchors have been checked, record the criterion as confirmed without claiming a matching pattern.
10. Do not map these local statuses to the separate `strong / mixed / weak / unknown` portfolio-comparison vocabulary.

## Preservation contract

- The other seventeen H2 sections remain. Outside the target section, only the related `средний балл` hard-gate sentence and output-template row change; the table-of-contents link and all unrelated content remain byte-for-byte.
- The target section retains all six criterion names and the exact substance of all eighteen baseline cells.
- The workflow reference stays in the canonical runtime payload and `ksrf-complaint-qa/SKILL.md` keeps its exact backlink.
- All seventeen table-of-contents links, including the unchanged rubric anchor, continue to resolve.
- The full final reference is pinned by SHA-256 after the reviewed transformation.

## Verification

- RED proves the current 0–2 header, score ranges, and compensation language still exist.
- GREEN proves their absence; the three statuses, six dimensions, eighteen meanings, four actions, non-compensation, unresolved-task behavior, full-reference projection, TOC, payload, and backlink.
- Full test suites, source strict, clean-room runtime strict, strict OpenSpec, exact manifest verification, diff checks, and independent semantic/test/release reviews gate publication.

## Risks and controls

- **Partial evidence is mislabeled as a known defect or vice versa.** Controlled by criterion-specific warning and insufficient-data assertions.
- **Removing ranges also removes useful action guidance.** Controlled by exact assertions for all four actions.
- **The new statuses become another readiness score.** Controlled by explicit heuristic/non-authorizing and non-compensation text.
- **Unrelated workflow content is lost.** Controlled by a full-reference digest and TOC/structure checks.
