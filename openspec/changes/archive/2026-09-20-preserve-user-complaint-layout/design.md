## Context

Existing formatting guidance preserves substance and separates court-facing text from a review report. This change addresses a later user-edited document, where preserving earlier generated content would instead discard the user's current choices.

## Goals / Non-Goals

Goals: preserve user paragraph divisions and selected content; prevent restoration of deleted requests, citations or particulars; make request and signature layout stable; keep annex labels, numbers and files consistent.

Non-goals: infer a universal number of requests or source restriction from one complaint; add mandatory annexes for every precedent citation; automate signatures, human approval or legal completeness; implement a new renderer.

## Decisions

- The latest user-designated DOCX controls editorial revisions. Compare against the earlier version read-only and keep the user's deletion decisions. Missing legally required particulars remain visible in the separate review; do not silently restore them or mark readiness true.
- Preserve deliberate paragraph and section boundaries. Formatting-only edits retain wording and selected content. Explicit list-number repair may renumber the complaint's own items and internal references, but not case numbers, act numbers or source paragraph locators.
- The request marker is a separate bold centered paragraph with no first-line indent, linked to the following request. Preserve user capitalization. There is no prescribed count of requests.
- Keep the date left and the blank signature line with the confirmed signatory's name right on the same row. Use a right tab stop at usable width or a borderless two-cell table; never simulate alignment with repeated spaces or fabricate a handwritten signature or signing date.
- Reconcile mentions of specific case records, the annex list and actual files. Distinguish a cited legal authority from an annex; a citation alone does not require automatically adding a copy.
- Source restrictions govern the particular document, not every future case. Preserve substantive source/adverse analysis separately; restricted court-facing selection does not license a false statement about the law.
- State these as editorial and QA instructions. Existing generator output must be checked against them; this change does not claim automatic preservation of a user-edited DOCX.

## Validation

Use synthetic read-through scenarios: removed alternative request; deleted required particular; lowercase request marker; one-row signature with a long name; annex numbering gap; a source restriction limited to one case; cited precedent that is not an annex. Validate source structure, offline portability, manifest/privacy, clean-room installation and OpenSpec. Publish one atomic commit and verify live main before global installation.
