# Design: Authority-ledger drafting hypothesis binding

## Context

The validator currently returns only a set of authority identifiers from
`validate_authorities()`. `validate_drafting_blocks()` can consequently prove
that a referenced authority exists, but cannot prove that it belongs to the
same hypothesis as the drafting block.

The stable deterministic fixture is otherwise valid:

- `query_profile.hypothesis_id = H1`;
- `A1.hypothesis_ids = [H2]`;
- `B1.hypothesis_id = H1` and `B1.authority_ids = [A1]`;
- adverse and human-review gates pass.

Stable validation returns no errors.

## Decisions

1. `validate_authorities()` will retain a mapping from each valid
   `authority_id` to its non-empty string `hypothesis_ids`.
2. Existing authority-existence checks will use the mapping keys.
3. `validate_drafting_blocks()` will check every referenced authority
   independently. A reference is valid only when the block hypothesis occurs
   in that authority's declared hypothesis set.
4. An authority may declare multiple hypotheses. Membership, not equality of
   the whole list, is the invariant.
5. Errors will remain attached to the exact
   `$.drafting_blocks[i].authority_ids[j]` path.

## Alternatives Considered

- Requiring only one matching authority per block was rejected because it
  leaves unrelated authorities inside the drafting block.
- Comparing a block only with `query_profile.hypothesis_id` was rejected as a
  broader contract change; this change addresses only block-to-authority
  binding.
- Changing legal roles, verification gates, or human approval semantics was
  rejected as out of scope.

## Verification

- RED test: H1 block referencing H2-only authority fails.
- Positive control: H1 block referencing an authority with `[H1, H2]` passes.
- Existing unknown-authority behavior remains covered.
- Skill tests, strict package/full validators, root tests, OpenSpec strict
  validation, offline self-containment, and clean-room installation must pass.
