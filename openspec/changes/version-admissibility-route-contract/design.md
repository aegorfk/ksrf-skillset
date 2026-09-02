## Context

Four installed skills already share the same methodology: assess twelve admissibility gates, distinguish a remediable gap from an unavailable record, prefer a court-request route when an active proceeding supports it, and allow `GO_TO_KSRF` only after viable issue and remedy research. The runtime filing router already provides versioned local payload validation, content-addressed inputs/results and append-only events, but it has no admissibility route.

## Assumptions

- A researcher or lawyer supplies gate statuses, rationales and evidence references; the runtime never decides whether a legal proposition is true.
- The route performs no network or model call. Current official authority is resolved only from the existing local source-evidence repository.
- `status` reports the latest persisted admissibility operation in the matter workspace.
- A derived recommendation is a planning artifact for human review, not filing or publication authority.

## Goals / Non-Goals

Goals:

- make the twelve-gate matrix structurally complete and versioned;
- make route precedence deterministic and fail closed;
- prevent `unknown`, unavailable records and stale official anchors from becoming `GO_TO_KSRF` or false `NO_GO_KSRF`;
- expose `validate`, `derive` and `status` through the installed Russian-language CLI;
- preserve an auditable input/result chain inside one matter workspace.

Non-goals:

- infer gate statuses from case documents;
- fetch or promote official sources;
- calculate the one-year deadline or choose the final relevant act;
- score legal merit or acceptance probability;
- approve a principal issue, sign, pay, release or file anything;
- migrate or rewrite existing matter manifests.

## Project Structure

- `skills/ksrf-complaint-cycle/schemas/ksrf_filing/` — the two Draft 2020-12 artifact schemas.
- `skills/ksrf-complaint-cycle/lib/ksrf/filing/admissibility.py` — dependency-free normalization, validation and route derivation.
- `skills/ksrf-complaint-cycle/lib/ksrf/filing/workflow.py` and `cli.py` — installed route integration.
- `skills/ksrf-complaint-cycle/tests/test_admissibility_routing.py` — schema, domain and workflow tests.
- `tests/test_admissibility_runtime_contract.py` — cross-skill and clean-install contract tests.
- `skills/*/SKILL.md` and the shared artifact reference — user-facing routing to the executable contract.

## Commands

- Focused tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider skills/ksrf-complaint-cycle/tests/test_admissibility_routing.py tests/test_admissibility_runtime_contract.py`
- Full root tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests`
- Full skill tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider skills/*/tests`
- Source validation: `PYTHONDONTWRITEBYTECODE=1 python3 skills/ksrf-complaint-cycle/scripts/validate_ksrf_skillset.py --skills-root skills --profile source --strict`
- OpenSpec: `PATH="$HOME/.local/bin:$PATH" openspec validate version-admissibility-route-contract --strict`

## Decisions

1. **Exactly twelve gates.** The matrix contains each canonical gate exactly once: `competence_and_route`, `applicant_and_subjective_interest`, `case_status`, `challenged_norm_version`, `application_or_meaning`, `causation_and_rights_harm`, `exhaustion_and_preservation`, `one_year_deadline`, `continuing_legal_effect`, `anti_appeal_boundary`, `prior_ksrf_authority_delta`, and `permissible_remedy`. The first, third and last gates carry respectively the evidence-bound route, proceeding and remedy disposition; other rows carry no disposition. `court_request` requires an active proceeding, while `individual_complaint` requires a completed proceeding, so a live case cannot silently receive the individual-complaint GO route.
2. **Evidence-bearing rows.** Every row carries `status`, `rationale`, `applicability_reason`, material `evidence_ids`, official-rule evidence IDs, `official_checked_at`, `curability`, `record_availability`, `next_action` and a gate-specific disposition. Every status, including `unknown` and `not_applicable`, requires evidence; an exhausted search is a SourceObservation/acquisition-attempt fact rather than a self-asserted absence. `not_applicable` also requires a reviewable reason and current official-rule support.
3. **Explicit official snapshot.** The matrix declares `verified_current`, `missing`, `stale` or `unavailable_after_search`, a parseable non-future checked time and its evidence IDs. `official_checked_at` is audit metadata, not proof of temporal freshness and not a hard-coded max-age policy. A claimed current snapshot is effective only when every ID resolves through `SourceEvidenceRepository.current_filing_authority()` at derivation or status time; an explicit `stale` state abstains.
4. **Deterministic precedence.** Structural invalidity raises an input error and emits no recommendation. Otherwise: ineffective official authority or stale issue binding gives `ABSTAIN_PENDING_RECORD`; an unavailable or residual critical unknown gives `ABSTAIN_PENDING_RECORD`; a controlled unknown gives `FIX_FIRST`; only when no unknown remains, an incurable fail, including an evidence-bound non-viable remedy, gives `NO_GO_KSRF`, while a curable fail gives `FIX_FIRST`; evidence-bound `case_status=active` plus `competence_and_route=court_request` gives `COURT_REQUEST_ROUTE`; incomplete issue research or no currently viable bound option gives `FIX_FIRST`, not an absence finding; all applicable gates passed plus a completed viable fingerprinted issue option and `permissible_remedy=viable` gives `GO_TO_KSRF`; any residual uncertainty abstains.
5. **Revision and option binding.** `matrix_id` is only a logical handle. The recommendation also contains a computed `matrix_revision_id` over the canonical normalized matrix and exact `{option_id, content_fingerprint, readiness, evidence_ids}` bindings. The fingerprint uses the native `issue-candidate-content:sha256:<64 lowercase hex>` identifier and the workflow reopens the latest persisted issue candidates in the same matter, recomputes their fingerprints and checks `claim_id`; a caller-supplied syntactically valid digest is insufficient. Changing any gate, rationale, evidence or option fingerprint changes the recommendation identity.
6. **No scalar readiness.** The output records decisive gates and blockers, never a probability, score or automatic legal confidence.
7. **Human boundary in the schema.** Derivation always sets `human_decision` to `pending`, `legal_assessment_automated` to `false`, `filing_authority` to `false`, and `filing_performed` to `false`.
8. **Existing ledger, no workspace migration.** The normal router persistence stores canonical input and result bytes and appends an event. `status` reconstructs the latest matrix, re-resolves current official authority and re-derives the recommendation, so revoked authority can downgrade an earlier GO. No new required `matter.json` field or mutable singleton file is introduced.
9. **Workflow exit contract.** The uppercase route decision lives inside `result.recommendation`. Only `GO_TO_KSRF` uses an outer expert-review state with exit zero; `FIX_FIRST`, `COURT_REQUEST_ROUTE`, `NO_GO_KSRF` and `ABSTAIN_PENDING_RECORD` use outer `blocked`, preserving CLI exit code 3.
10. **Version and canonical output.** Inputs use schema version `1.0.0`; IDs and JSON output are deterministic for the same substantive payload, while event observation time remains ledger metadata.

## Code Style

Domain decisions use named enums/constants and explicit branches rather than numeric scoring, for example:

```python
if unresolved_official_authority or unavailable_record:
    return "ABSTAIN_PENDING_RECORD"
if incurable_failures:
    return "NO_GO_KSRF"
```

Validation errors name the exact field or gate in Russian. Public output is Russian; stable machine values remain the documented uppercase route enums.

## Testing Strategy

- Draft 2020-12 schema acceptance/rejection tests for exact fields, uniqueness and conditionals.
- Pure domain unit tests for every precedence branch and stable output.
- Workflow/CLI tests for `validate`, `derive`, `status`, append-only persistence and zero network/model activity.
- Adversarial tests: `unknown` never GO/NO_GO; unavailable source never NO_GO; false `not_applicable`; missing/stale checked time; unverified official evidence; active proceeding; incomplete issue/remedy research.
- Cross-skill and clean-install tests proving the route, schemas and documentation survive runtime packaging without `evals` or test dependencies.

## Boundaries

- Always: validate all twelve gates, preserve evidence references, resolve claimed current official authority locally, persist append-only provenance, run focused/full/source/runtime/OpenSpec checks.
- Ask first: changing the canonical gate set, route decision enum, matter workspace schema or human-only release/filing controls.
- Never: infer a pass from missing data, turn source unavailability into absence, emit GO from `unknown`, change `human_decision` from pending, make a network/model call, or perform filing.

## Risks / Trade-offs

- **A complete matrix is verbose** → provide one minimal fixture and clear Russian validation errors, while retaining all evidence-bearing fields.
- **A user can self-assert an official source ID** → the workflow recomputes current authority from the local repository before GO; stored flags alone are insufficient.
- **Route precedence can hide multiple blockers** → output all blockers and decisive gate IDs even though it emits one route.
- **Existing workspaces have fixed manifests** → reuse the workflow ledger instead of adding required paths.
- **Research completion is not legal success** → issue bindings retain exact fingerprints/evidence, remedy is an independent hard gate, absence of a currently viable theory is not itself `NO_GO`, and every output awaits human decision.

## Migration and Rollback

1. Freeze live SHA and runtime manifest.
2. Strictly validate this OpenSpec change.
3. Add RED schema/domain/route/clean-install tests.
4. Add schemas and the pure domain module.
5. Integrate the CLI/workflow route and user guidance.
6. Regenerate the manifest and run full verification plus independent review.
7. Publish atomically, install the exact payload, archive OpenSpec and publish final evidence.

Rollback is a normal revert of the atomic release. Existing matter workspaces and prior workflow events remain readable because their manifest contract is unchanged.
