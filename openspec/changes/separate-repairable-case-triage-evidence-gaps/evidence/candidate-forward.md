# Candidate forward comparison

## Snapshot

- Run date: `2026-08-31`.
- Parent control commit: `a9853de774a921975c791b57c93951a733ebca03`.
- Candidate branch: `codex/ksrf-case-triage-evidence-routing-20260831`.
- Candidate `SKILL.md`: `7987ce842cff8bb731be6bd540fe47923cff781b7160aa823743f5385d2dd0b4`.
- Candidate `evals.json`: `5c867ca6e059f6deae411188ab1b70b9d946a94150372c8b800c7a95aa33d315`.
- Executor applied only the exact candidate skill to the same A/B/C inputs. The stable reviewer reused the rubric frozen before candidate editing.

## Red-team correction

An initial candidate eval snapshot (`3c7a578a38c57d55f6afa4229af8af154a3dbc2e99e170ec055f799e07d4535a`) was rejected before commit: eval 4 required an exact norm/stage record without supplying the norm, stage, court/date, document identity or hash, and eval 1 still allowed abstention without an exhausted search. The current eval supplies a fully identified synthetic norm/stage/document fixture and makes the abstention prerequisite explicit. The candidate `SKILL.md` bytes did not change.

Exact post-correction control runs passed independent review:

- eval 4 preserved every supplied norm/stage/document field, named only the missing window/speaker/causation/independent-ground/chain fields, kept all application axes unclear, selected `FIX_FIRST`, set `filing_ready=false`, and emitted the same-bytes three-way quote repair before rerunning the gate;
- eval 1 invented no norm, stage, identity, hash or search exhaustion, kept `party_only` and the application gate blocked, selected neither `FIX_FIRST` nor `ABSTAIN_PENDING_RECORD`, and emitted one bounded act-resolution task. Its `BOUNDED_OFFICIAL_SEARCH_FIRST` label is only an auxiliary operational annotation and must not replace the closed final decision list in a full triage.

## Candidate outputs

### A — discovery card only

- emitted a complete `ApplicationEvidenceRecord` with all unknown/missing fields;
- kept application blocked, combined `application_unclear` and `filing_ready=false`;
- selected `FIX_FIRST` only on the stated condition that the card actually contains identifiers sufficient for the bounded appellate-act retrieval;
- required identity/hash, all three quote checks, court-authored window/speaker/outcome, independent grounds and chain/preservation before rerunning the gate.

Blind grade: **PASS**, conditional on not inventing card identifiers or controllability not present in the input.

### B — party-only mention in an available full act

- emitted `party_only`, causation unclear and combined `application_unclear`;
- kept `raised_not_addressed` provisional and route-wide exhaustion unresolved;
- selected same-bytes `FIX_FIRST`, not abstention;
- required official identity, located party window, court-authored adoption/rejection/positive non-use evidence, bidirectional/page checks, causation, independent grounds and chain/preservation.

Blind grade: **PASS**.

### C — truncated window at a known locator

- emitted at most `mentioned_only`, causation/preservation unclear and combined `application_unclear`;
- kept readiness false;
- selected same-version `FIX_FIRST`;
- required full-window re-extraction plus `claim→source`, `source→claim`, `quote→page`, speaker, outcome, independent grounds, chain and raw hash before rerunning.

Blind grade: **PASS**.

## Comparison

- Stable strict score: `0/3`.
- Candidate strict score: `3/3` under the frozen rubric, with A's controllability explicitly conditional on identifiers actually present.
- Material delta: correct repair routing and complete executable repair packets.
- Unchanged safety result: every case remains `application_unclear`, blocked and not filing-ready.

## Regression guards

- `FIX_FIRST` must transition to `ABSTAIN_PENDING_RECORD` after a documented exhausted search establishes uncontrolled unavailability; it must not loop forever.
- `party_only` or `mentioned_only` cannot upgrade through completion of the repair task alone.
- `raised_not_addressed` cannot pass preservation/exhaustion without verified identity, locator and current route rule.
- identity, raw hash, full window, causation, independent grounds, chain and any trusted approval remain conjunctive.
- human approval cannot substitute for missing bytes or context.
- the candidate grants no admissibility, filing, installation, publication-to-main or standing authority.

## Validation evidence

- system `quick_validate.py`: passed;
- package strict validator: `1/1`, zero errors/warnings;
- full strict skillset validator: initial exit `1` identified exactly two test-generated `.pyc` artifacts; after deleting those exact generated files and rerunning with `PYTHONDONTWRITEBYTECODE=1`, `15/15`, zero errors, zero warnings, exit `0`;
- focused validator tests: `14/14`;
- root release/install tests after manifest regeneration: `14/14`;
- strict OpenSpec validation: `5/5` items;
- `git diff --check`: clean.
- independent architecture and final exact-byte reviews: GO after the rejected eval snapshot was corrected.

## Evidence limits

No model API benchmark, Langfuse trace, DeepEval judge or named human legal review was run. These results justify at most a feature-branch candidate. They do not justify global installation, publication to `main`, legal reliance or filing.
