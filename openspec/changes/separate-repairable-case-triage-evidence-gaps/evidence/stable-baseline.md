# Frozen stable baseline

## Snapshot

- Run date: `2026-08-31`.
- Published control commit: `a9853de774a921975c791b57c93951a733ebca03` (`origin/main` at clone time).
- `skills/ksrf-case-triage/SKILL.md`: `b8694efb53ca664d2ba6eca980a9a213f59b8dd9211830e4849265244d309499`.
- `skills/ksrf-case-triage/evals/evals.json`: `d7ee277c5d83ee3b26718ca05349b41a1c2880dd49ec1a88045f29affa961415`.
- `skills/ksrf-case-triage/evals/trigger-evals.json`: `c852859321886c52891f56707b2f9afce7aca5d9c5d436e570c4265a3dcf92da`.
- No repository edits, network retrieval, paid call, Langfuse trace or DeepEval run occurred during the stable execution.

## Outcome-blind protocol

One executor applied only the frozen stable `SKILL.md` and its two mandatory application/source references to three synthetic inputs. A separate reviewer froze the observable rubric before receiving the outputs. The reviewer then graded the outputs without seeing candidate edits.

Common hard requirements were: combined status `application_unclear`; application gate unknown/blocked; `filing_ready=false`; exact known/missing evidence; one bounded next task. `FIX_FIRST` was reserved for a demonstrably controllable record/context repair. `ABSTAIN_PENDING_RECORD` required a documented exhausted bounded search and uncontrolled unavailability. Summary, party text, silence or a truncated window could not prove application, non-application or causation.

## Frozen inputs and stable outputs

### A — discovery card only

Input: a search card says that the appellate court applied a norm; no full act, raw hash, court-authored locator or quote window is supplied.

Stable output:

- source `discovery_only`;
- `norm_use_status=unclear`, `outcome_causation=unclear`, `preservation_exhaustion=record_missing`;
- combined `application_unclear`, not ready;
- `ABSTAIN_PENDING_RECORD` only after an official-search journal;
- next task requested the full act, official anchor, raw SHA-256, identity, locator, speaker role and quote window.

Blind grade: **FAIL**. The task omitted an express court-authored outcome/causation span, independent-ground check and chain/preservation evidence. The routing result remains conditional on whether the card actually supplies enough identifiers for a controlled retrieval; no identifier may be inferred.

### B — party-only mention in an available full act

Input: the full act and SHA exist, but the norm appears only in a party submission and there is no located court-authored treatment.

Stable output:

- `norm_use_status=party_only`, causation unclear;
- provisional `raised_not_addressed`, route-wide exhaustion unknown;
- combined `application_unclear`, expressly not `not_applied`, not ready;
- next task sought court-authored treatment, an independent-ground check and official identity.

Blind grade: **FAIL**. The bytes were already available and the remaining work was controllable, so the operational route had to be `FIX_FIRST`, not generic abstention. `raised_not_addressed` also had to remain provisional until its locator and official identity were verified.

### C — truncated window at a known locator

Input: a full act and locator exist, but the saved window contains only a heading; raw hash, speaker and causal context are missing.

Stable output:

- at most `mentioned_only`;
- causation and preservation unclear;
- combined `application_unclear`, not ready;
- next task requested the full window, speaker, causal link, independent ground, hash and source.

Blind grade: **FAIL**. This was a controllable same-document repair and therefore required `FIX_FIRST`, not abstention. The task also omitted explicit `claim→source`, `source→claim` and `quote→page` checks.

## Failure ledger and bounded hypothesis

Strict baseline score: `0/3`. The core safety invariant already passed in every case: stable never promoted application or filing readiness. The RED hypothesis is therefore narrower: stable does not reliably distinguish controllable evidence repair from an unavailable record and does not always emit a complete executable repair packet. A candidate that merely repeats “a truncated window cannot prove application” is redundant and must be rejected as plateau.

## Evidence limits

This is a three-case agent forward-test, not a production model benchmark, legal validation, DeepEval result or human promotion approval. It can support only a candidate-branch decision for this narrow output contract.
