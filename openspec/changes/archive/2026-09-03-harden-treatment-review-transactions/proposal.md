## Why

Treatment proposal and review currently validate database-backed provenance before
their write transaction begins. A concurrent SQLite writer can therefore replace
the source-chain binding or invalidate a completed predecessor after validation
but before the treatment or decision is committed. Review history also uses
`INSERT OR IGNORE`, so a colliding or forged history row can be silently accepted
while the treatment status still changes. These gaps can make a successful command
describe evidence that was not the evidence protected at commit time.

## What Changes

- Put every database-backed proposal/review precondition, the treatment mutation,
  immutable history insertion, and final result read in one explicit reserved
  SQLite transaction.
- Reject caller-owned/nested transactions without committing or rolling them back.
- Convert only SQLite busy/locked contention into a dedicated public-corpus error,
  use no application retry, and restore the caller connection's prior busy timeout.
- Replace silent history insertion with exact insertion and require the canonical
  `candidate_created` event before replaying or reviewing a candidate.
- Preserve safe idempotent replay for an exact ordinary or replacement proposal,
  but reject a same-ID row or history that does not exactly match its deterministic
  contract.
- Keep concurrent winner semantics explicit: a losing caller sees either immediate
  contention or, after an explicit rerun, the immutable-review/replacement conflict.
- Expose the temporary-contention outcome to installed CLI users as a stable Russian
  error with exit code 2 and no success JSON.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-practice-quality-exit-status`: make treatment proposal, provenance review,
  mutation, and immutable history one fail-closed transaction.
- `ksrf-user-facing-cli`: disclose the non-retrying contention outcome and the
  caller's explicit rerun path.

## Impact

- Public-corpus transaction/error helpers and treatment methods in
  `public_corpus.py`.
- Treatment CLI failure behavior and Russian help/guidance.
- Deterministic concurrency, rollback, corrupted-history, and source-binding tests.
- Installed KSRF methodology reference for treatment review.
- No schema migration, network access, automatic legal review, filing authority,
  or filesystem-level atomicity claim is introduced.
