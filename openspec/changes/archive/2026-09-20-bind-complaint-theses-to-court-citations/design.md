## Context

The existing presentation reference separates court-facing legal prose from the companion Markdown review. The new rule concerns the quality and placement of legal citations within that prose, while full-text acquisition and source integrity remain governed by existing research requirements.

## Goals / Non-Goals

Goals: connect a material proposition, a verified court passage and its application to the challenged normative mechanism; give the reader precise conventional citations; maintain one coherent citation format.

Non-goals: prescribe a quota of citations, imply that every sentence needs authority, automate substantive verification, add precedent from an individual complaint, or expand filing authorization.

## Decisions

- Use the existing presentation reference as the single source for the citation style rule, with one QA entry linking to its exact section.
- State the authority and its factual/normative limits from a full-text source, never from discovery metadata alone. Keep direct quotation separate from paraphrase and applicant analogy.
- Specify date, decision number and paragraph; where the act lacks a numbered subdivision, use a precise page/paragraph locator without inventing numbering.
- Keep technical evidence IDs, hashes, acquisition logs, unresolved checks and risk assessments in the Markdown review. Court-facing citations use legal requisites and explanatory prose.
- Validate documentation structure, references, source/runtime separation, OpenSpec and the exact public release manifest. Runtime tests and renderer edits are unnecessary for this documentation-only change.

## Risks / Trade-offs

Excessive citation can hide reasoning. The rule explicitly prioritizes the proposition-to-application connection over citation volume. A correct citation can still be overextended; QA checks the scope and whether a claimed transfer is the applicant's argument. A missing source remains an unresolved issue in the separate report and is never silently upgraded.

## Validation

Review the diff against synthetic situations: direct holding with a numbered point; unnumbered passage; a case from another legal context; a party assertion quoted inside a decision; a Supreme Court proposition. Run strict source validation, offline self-containment, clean-room installation verification, OpenSpec validation and publication/privacy checks. Publish one atomic commit and verify live main before installing globally.
