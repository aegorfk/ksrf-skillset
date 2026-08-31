# Change: Enforce authority-ledger hypothesis binding

## Why

`ksrf-practice-authority-builder` currently validates that every
`drafting_blocks[].authority_ids[]` value exists, but it discards each
authority's `hypothesis_ids` before validating the block. An otherwise valid
drafting ledger can therefore attach an H1 block to an authority that supports
only H2 and still pass `--require-drafting`.

## What Changes

- Preserve the `authority_id -> hypothesis_ids` mapping during validation.
- Reject each drafting-block authority reference whose authority does not
  include the block's `hypothesis_id`.
- Keep multi-hypothesis authorities valid when the block hypothesis is one of
  their declared hypotheses.
- Clarify the invariant in the normative ledger contract and cover the
  negative and positive cases with deterministic tests.

## Impact

- Scope is limited to `ksrf-practice-authority-builder`.
- Research and audit ledgers without drafting blocks remain unaffected.
- Existing unknown-authority validation remains unchanged.
- This change adds no legal authority and does not promote a candidate to
  filing-ready status.
