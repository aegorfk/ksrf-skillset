# Change: Replace the complaint-QA argument score with independent checks

## Why

The installed complaint-QA workflow still grades each argument on six 0–2 dimensions and totals the result into `10–12`, `7–9`, `4–6`, or `0–3`. A zero for the norm/application or constitutional-defect criterion can be compensated by unrelated points and still label an argument suitable as principal. That contradicts the owning skill, which forbids a scalar legal-readiness score and requires unresolved evidence or application to remain blocking.

## What changes

- Replace the six-criterion score rubric with six independent `подтверждено / предупреждение / недостаточно данных` checks.
- Preserve every substantive condition from the eighteen score cells and the four practical actions: principal use, repair/support, auxiliary/rework, or removal.
- Remove score totals and update the two related scalar cross-references elsewhere in the same guide; express the retained actions as non-compensating decisions tied to the affected criterion, canonical hard gates, and human selection.
- Add exact regression coverage for the full reference, table of contents, payload membership, backlink, status semantics, and absence of scalar vocabulary.
- Update public documentation with the user-facing effect of the change.

## Impact

- Frozen base: `b424e9c094e382fb230e9ce61e789883cfa19b73`.
- Target: `skills/ksrf-complaint-qa/references/workflow-reference.md`, 331 lines / 37,383 bytes / SHA-256 `55d9f0ece6cd2f230939a1fcb39dd3e35bd7a296dce7c6be1d4ecd5de2e1eb14`.
- Baseline package: 6 files / 105,466 bytes / tree SHA-256 `85db517fb3bd8914736f2cf6f24685e60a72c845a73472191d823a6eceac96b0`.
- Baseline runtime: 15 packages / 235 files / 8,063,765 bytes / tree SHA-256 `ceead1ed039f946776baac817fcf75d630174458f1d31a19834b36a019326bf4`.
- Release tools remain 9 files / 197,557 bytes / tree SHA-256 `ef4d7395c10f436b13f4cd09ed450a65519a5dce78cd7f8a346b363c9ff80ddd`.
- Final target: 344 lines / 43,067 bytes / SHA-256 `4968c07ce87f1cf833aad39a6ac3852146ae7c6f241e92fd5e79f7b707bf8296`.
- Preserved-content projection: 311 lines / 35,078 bytes / SHA-256 `6e48efe07a0cab58ac32b135ec5b9315ec7f282125ea229a35183c6f762f658d`.
- Final package: 6 files / 111,150 bytes / tree SHA-256 `78ab06b4ff2dcd199c2623c66e0f0706b1c8e9afc4a9e401a1f5526d045b9657`.
- Final runtime: 15 packages / 235 files / 8,069,449 bytes / tree SHA-256 `1c9252c0c9a82ab52fab0dc9e7d95f35bc585e8ccde4e82cbf1c81329af8b1d7`.
- Release tools remain 9 files / 197,557 bytes / tree SHA-256 `ef4d7395c10f436b13f4cd09ed450a65519a5dce78cd7f8a346b363c9ff80ddd`.

## Non-goals

- Do not alter the canonical `AdmissibilityMatrix`, `EvidenceGate`, `ReleaseGate`, verdicts, filing authority, or human approval rules.
- Do not remove any criterion, adverse condition, repair option, drafting guidance, or unrelated content from the workflow reference.
- Do not change scripts, schemas, evaluators, or executable behavior.
- Do not claim that six confirmed heuristic checks establish legal correctness, admissibility, filing readiness, principal selection, or expected outcome.
