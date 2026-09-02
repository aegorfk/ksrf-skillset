## Context

`admissibility derive` can emit `GO_TO_KSRF` only after resolving official evidence through `SourceEvidenceRepository.current_filing_authority()` and recomputing each selected issue candidate through the native issue-gate evaluator. `admissibility status` reloads the previously persisted matrix, repeats those checks, derives a new recommendation, and appends a new workflow event. The current tests simulate post-GO drift by patching the two resolver methods. They therefore do not cross the actual approval-event boundary: approval issuance, native evidence or candidate persistence, revocation, current validation, persisted payload reload, route derivation, content-addressed result storage, and append-only status event.

This change closes that regression gap without broadening runtime behavior. The two tests use deterministic local clocks and local temporary matter workspaces. They make no network or model calls and do not depend on the source repository checkout, `evals`, or a new validation profile.

## Goals

- Prove that revoking the exact trusted approval supporting an official source identity makes the same persisted official evidence non-current during the next status check.
- Prove that revoking the exact trusted human selection supporting the persisted issue option makes that binding non-viable during the next status check.
- Prove in both cases that a previous `GO_TO_KSRF` becomes `ABSTAIN_PENDING_RECORD`, the workflow exits blocked, and a specific current blocker identifies the revoked trust link.
- Prove byte-for-byte immutability of the prior result object and the complete prior event record while allowing exactly one new status event to be appended.
- Preserve all human legal-review and filing-control boundaries.

## Non-Goals

- Add a runtime/source verifier mode, validation profile, command, CLI flag, schema version, or installer rule.
- Add network retrieval, model calls, remote fixtures, or time-dependent external state.
- Replace the source-identity, issue-gate, trusted-approval, content-addressed-store, or event-ledger implementations with test doubles.
- Change route precedence, infer admissibility, recreate a revoked approval, or turn status into legal or filing authority.
- Expand the public skill guidance or introduce a new runtime dependency.

## Decisions

### 1. Revocation tests cross the native trust boundary

Each regression SHALL instantiate a real temporary matter workspace, the native `TrustedApprovalLedger`, and a `WorkflowRouter` wired to that ledger. It SHALL create approvals with the canonical request builders and write revocation events through `TrustedApprovalLedger.revoke_approval()`. It SHALL NOT patch `_resolve_current_source_authority`, `_validate_current_issue_bindings`, approval validation, ledger reads, content-addressed reads, or route derivation.

The source test SHALL persist real official source evidence whose `identity_verification_mode=trusted_approval` is backed by the exact source-identity approval under test. The issue test SHALL persist the issue-generation event and canonical candidate fingerprint together with the real approvals required for its current gate decision, including a distinct trusted human-selection approval. Both initial derivations must reach `GO_TO_KSRF` through native revalidation; a fixture that manually writes a GO result or supplies a mocked `filing_ready`/`passed` value is invalid.

### 2. Status reuses the persisted matrix and recomputes current authority

After the initial GO event, the test SHALL revoke only the targeted approval and invoke `router.dispatch("admissibility", "status")` with no replacement matrix. Status must reload the exact payload associated with the latest admissibility operation, resolve the native current authority again, and derive a fresh recommendation. It must not reuse the cached GO recommendation as current evidence.

Revoked source identity makes at least one required official evidence ID fail current filing authority. Revoked issue selection makes at least one bound viable option fail its current issue-gate decision. Either condition has higher precedence than an earlier GO and therefore yields `ABSTAIN_PENDING_RECORD`, `state=blocked`, and workflow exit code `3`.

### 3. Blockers identify the broken current binding

The source path SHALL expose the official evidence ID together with the native revoked-approval reason in `official_authority_blockers` and/or the recommendation's blocker set. The issue path SHALL expose the option ID and a native current-gate or approval blocker in `issue_binding_blockers` and the recommendation's blocker set. Assertions SHALL reject a generic downgrade that loses which evidence or option must be repaired.

The tests need not freeze every nested diagnostic string if the native subsystem already provides a stable structured reason, but they must prove both the affected identifier and revocation semantics. They must also prove that status does not silently replace the revoked approval, treat historical approval as current, or convert missing current authority into a legal absence finding.

### 4. Append-only preservation is verified at the byte boundary

Before revocation, each test SHALL capture:

- the exact bytes returned by the content-addressed store for the GO event's `result_object`; and
- the exact bytes of the complete workflow event ledger, including its terminating newline.

After status, the prior result object must be byte-identical. The new ledger bytes must begin with the complete captured prefix, and parsing the suffix must yield exactly one new `status` event. The earlier GO event line itself must remain byte-identical and retain its original result-object reference. This proves append-only behavior more strongly than comparing parsed JSON values.

### 5. The change remains deterministic and local

Fixtures SHALL use a fixed monotonic clock, canonical local source bytes, the bundled source registry, and native fingerprint/request builders. No HTTP adapter, MCP tool, model, subprocess network call, or sleep is permitted. Revocation time must be later than approval time so native temporal validation, rather than test patching, establishes `approval_revoked`.

### 6. Runtime changes are conditional and narrowly bounded

The expected implementation is test hardening against behavior already present. If either native end-to-end test fails because status bypasses or incompletely propagates current approval state, the only permitted product correction is to the existing local authority resolution, issue-binding revalidation, or status-to-recommendation plumbing. The public CLI shape, schemas, installer/runtime validator, route decision vocabulary, and storage formats remain unchanged.

## Risks and Mitigations

- **Fixture complexity hides the contract:** use existing canonical builders and native repositories, and keep one approval revocation per test so the causal link is explicit.
- **False E2E through mocks:** prohibit patching every authority, approval, ledger, CAS, and route method named above; review imports for `unittest.mock` use in the two new tests.
- **Clock ambiguity:** inject a deterministic clock and place revocation strictly after approval/check time.
- **Brittle diagnostics:** assert stable structured identifiers and revocation reason rather than incidental Russian prose.
- **Mutation mistaken for append:** compare raw result-object and event-ledger bytes, then separately assert exactly one appended status event.
- **Scope creep:** run existing runtime/offline validators only as regression checks; do not add a profile, command, or runtime payload.

## Verification

- Run the two focused native E2E revocation tests with no patch/mock on current authority or issue bindings.
- Run the complete complaint-cycle admissibility test module and the full complaint-cycle suite.
- Run root tests, strict schema and skillset validation, runtime/offline installation checks, and strict OpenSpec validation.
- Inspect the test diff to confirm no network/model call and no new public CLI, schema, installer, validator-profile, or skill-guidance change.
- Obtain independent review with no unresolved P1/P2 finding before publication.
