## Why

The installed skills consistently require an `AdmissibilityMatrix` before substantive issue research and a `KSRFRouteRecommendation` before drafting, but both artifacts are prose-only. Their twelve hard gates, five route decisions and `unknown` stop rule can therefore drift between triage, exploration, QA and the runtime CLI. A user can receive a polished recommendation without a machine-checkable record proving that every applicable gate was handled, that official-rule evidence is current, or that an unavailable record was not silently converted into `NO_GO_KSRF`.

## What Changes

- Add versioned JSON Schemas for `AdmissibilityMatrix` and `KSRFRouteRecommendation` with exactly twelve named hard gates, evidence bindings, official-check metadata, curability, record-availability states and evidence-bound route/remedy dispositions.
- Add a standard-library domain module that validates a matrix and deterministically derives only one of `GO_TO_KSRF`, `FIX_FIRST`, `COURT_REQUEST_ROUTE`, `NO_GO_KSRF` or `ABSTAIN_PENDING_RECORD`.
- Resolve official-rule evidence against the existing current source-authority repository before `GO_TO_KSRF` is possible; missing, stale or unverified authority fails closed to abstention.
- Add the installed runtime route `ksrf admissibility validate|derive|status`; persist inputs and outputs in the existing append-only matter workflow ledger and content-addressed store.
- Bind each recommendation to a computed canonical matrix revision and exact issue-option fingerprints, so a reused logical ID cannot hide changed gates or option content.
- Keep every derived recommendation at `human_decision=pending`, `legal_assessment_automated=false` and `filing_authority=false`.
- Link the executable contract from case triage, complaint cycle, argument exploration and complaint QA.
- Add RED/GREEN schema, domain, route, clean-install and cross-skill contract tests.

## Capabilities

### Added Capabilities

- `ksrf-admissibility-routing`: a versioned, evidence-bound and fail-closed admissibility-to-route contract for the installed KSRF workflow.

## Impact

- Frozen live base: `71b8a77bc61d2b18ae8840700e386055287f4ee6`.
- Runtime baseline: 15 packages / 234 files / 8,035,436 bytes / tree SHA-256 `5170d0355279f9e13ae3d04aa01dc40f2caf77c52777b0e94bf3ef537ec14856`.
- Release baseline: nine files / 193,585 bytes / tree SHA-256 `58063e5f8096842d433a895f874c6de6b124e52910609e0be34c1d5a4e0a35cd`.
- Contract baseline: the twelve gates and five route decisions exist in installed guidance, but no `admissibility` runtime route or corresponding JSON Schema exists.
- Existing workspaces remain readable: the new route reuses `workflow/events.jsonl` and the workflow content-addressed store instead of changing `matter.json` or its fixed artifact-path contract.
- No model selection, network retrieval, source promotion, legal conclusion, human approval, signature, payment, release or filing is automated.
