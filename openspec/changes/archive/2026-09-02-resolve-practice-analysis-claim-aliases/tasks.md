## 1. Contract and Red Regression

- [x] 1.1 Record the exact local and projected external identity boundary
  without adding a PII/anonymity claim.
- [x] 1.2 Add an end-to-end failing test for wording review of a claim whose ID
  is projected in request and result artifacts, including real sibling import.
- [x] 1.3 Add negative coverage for non-active alias input, projection
  collision under partial selection, stale/foreign evidence, and
  non-authoritative alias state.
- [x] 1.4 Add a migration regression in which an immutable legacy request sorts
  after, but cannot supersede, the corrected attached request.
- [x] 1.5 Add a retroactive regression in which an already imported result
  becomes ambiguous after a second active claim acquires the same public ID.

## 2. Minimal Runtime Fix

- [x] 2.1 Derive exported question identity from the emitted public claim ID and
  reject selected-to-active public-ID collisions before persistence.
- [x] 2.2 Resolve the external result binding through the canonical public-ID
  projection after selecting the active local claim.
- [x] 2.3 Reuse that projection for finding applicability without changing
  local ledger identity or any trust/revision/human gate.
- [x] 2.4 Exclude a legacy self-inconsistent projected request from executable
  state selection without deleting or rewriting its audit artifact.
- [x] 2.5 Use one fail-closed unique-owner resolver in request creation, v2
  validation, and wording review.

## 3. Verification and Review

- [x] 3.1 Prove the focused red-to-green transition.
- [x] 3.2 Run practice-analysis, root, skill, source/runtime, clean-install,
  manifest, quick-skill, and strict OpenSpec checks.
- [x] 3.3 Obtain independent implementation, trust-boundary, and test review;
  resolve every in-scope P1/P2.
- [x] 3.4 Preserve all 18 practice-analysis help routes, 42 public argument
  actions, parser state, and unrelated errors/non-help CLI behavior.

## 4. Atomic Publication and Installation

- [x] 4.1 Archive the validated change and synchronize its base capability.
- [x] 4.2 Regenerate the manifest and create one atomic release commit.
- [x] 4.3 Push the feature ref and `main` to the identical commit and confirm
  the remote SHA.
- [x] 4.4 Install the exact published runtime globally and verify its identity.
