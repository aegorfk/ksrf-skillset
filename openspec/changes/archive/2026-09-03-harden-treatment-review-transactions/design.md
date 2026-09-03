## Context

`PublicCorpus.propose_treatment()` and `review_treatment()` currently combine
database reads made before a transaction with later writes. Their final CAS-style
checks protect only a subset of the decision: they do not bind the snapshot,
indexed text, official-source observation, source chain, predecessor, or existing
history that was inspected. A second connection can therefore change those rows in
the gap. In addition, `_append_treatment_history()` uses `INSERT OR IGNORE`, which
turns a primary-key collision into apparent success.

SQLite can reserve the single-writer slot before those reads with
`BEGIN IMMEDIATE`. This protects database provenance through commit, but it does
not lock content-addressed files against an unrelated process; filesystem
integrity remains a separately checked boundary.

## Goals / Non-Goals

**Goals:**

- Bind all database-backed proposal/review evidence, mutation, history, and return
  state to one owned reserved transaction.
- Roll back both the treatment row and its history when any validation, write, or
  commit step fails.
- Make lock contention a stable typed outcome with no retry by this operation.
- Refuse pre-existing, missing, additional, mismatching, or colliding forged
  history instead of silently accepting or repairing it.
- Preserve safe retries after a caller loses a successful response by treating an
  exact same-ID proposal, including an exact replacement, as idempotent.
- Keep the installed CLI outcome understandable without implying legal approval.

**Non-Goals:**

- Locking or transactionally publishing object-store files together with SQLite.
- Retrying, queueing, sleeping, or choosing a concurrent legal-review winner.
- Changing quote, identity, official-source, chronology, or supersession semantics.
- Repairing legacy corrupt rows or adding a database migration.
- Cryptographically detecting a direct database writer that rewrites a treatment
  and every deterministic history field into a new self-consistent state; that
  requires an external seal and remains outside this bounded transaction release.
- Making the public-corpus constructor itself fail immediately while schema/search
  initialization is contended; the no-wait guarantee starts at the treatment
  transaction boundary.

## Decisions

### One private owned transaction helper

A private context manager owns the complete treatment write transaction. It first
refuses `connection.in_transaction`, records the current `PRAGMA busy_timeout`,
then enters its cleanup-owned region before attempting to set that timeout to zero
and executes exactly one `BEGIN IMMEDIATE`. The caller performs every database-
backed check and write inside the context. The helper commits explicitly on
success; on any body or commit failure it rolls back if the owned transaction
remains active, restores the prior timeout, and re-raises. A rollback failure or
an exception after a commit attempt with no active transaction has an uncertain
outcome: the corpus connection is quarantined and the ordinary busy result is not
used.

Using `with connection:` around an explicit begin was rejected because ownership
and commit-failure behavior are implicit, and a caller-owned transaction could be
committed or rolled back accidentally. Deferred `BEGIN` was rejected because it
does not reserve the writer slot before provenance reads.

Pure validation that cannot depend on corpus state may precede the transaction:
argument enums, canonical identifiers, finite JSON conversion, and deterministic
proposal-ID construction. Snapshot existence, treatment/status/history,
predecessor/successor, indexed text, observation/seed, and final-result reads may
not precede it.

### Contention is typed, transaction-local, and not retried

`PublicCorpusBusyError(PublicCorpusError)` represents only SQLite `BUSY` or
`LOCKED`. Classification prefers `sqlite_errorcode & 0xff` so extended result
codes remain correctly grouped; a narrow message fallback covers Python runtimes
without that attribute. Other operational, I/O, read-only, constraint, and
integrity errors retain their own failure class.

The transaction temporarily uses `busy_timeout=0`, performs one begin/write/commit
attempt, and never sleeps or retries. Before the connection may be reused, the
helper restores its original timeout after both success and failure. If that
restoration itself fails, the helper quarantines the corpus connection, attempts
to close the underlying connection, and raises a distinct diagnostic that says
whether the treatment transaction committed, did not commit, or has an uncertain
outcome. If low-level close cannot be confirmed, the diagnostic says so while the
corpus object remains unusable. It does not reuse the ordinary contention message.
A caller may explicitly run the command again after an ordinary contention error.
This narrow choice avoids changing timeout behavior for corpus opening, schema
setup, search setup, or unrelated operations.

JSON-compatible Python containers in `target_identity` are round-tripped into
their canonical JSON-native value before deterministic ID construction, storage,
and replay comparison. This preserves the pre-existing acceptance of values such
as tuples and non-string mapping keys while preventing Python/SQLite representation
differences from producing a false replay failure.

### History insertion and validation are exact

History insertion uses plain `INSERT` and requires one affected row. A new
treatment plus `candidate_created`, and a decision update plus its decision event,
are indivisible. Integrity/row-count failure becomes a treatment-review error and
rolls back the whole transaction.

A canonical proposal payload is derived from the treatment's immutable columns.
Before a candidate can be reviewed, it must have exactly one history event:
`candidate_created`, null reviewer, canonical payload equal to those columns,
`event_at == created_at`, and the recomputed deterministic history ID. Extra,
missing, malformed, or mismatching events block the update. Before returning an
existing proposal, its immutable columns and the complete history appropriate to
its status must be exact; the method never normalizes or repairs a legacy row.

### Exact replay precedes successor conflict checks

Inside the reserved transaction, proposal handling first verifies snapshot
existence and looks up its deterministic treatment ID. If the stored immutable
proposal and status-appropriate history are exact, the call returns the stored
status from the same transaction without adding history. This works for ordinary
and replacement proposals and permits recovery after a lost response.

Only a new replacement then validates that its predecessor is currently completed,
has the same source/target identity, and has no successor. A successor with the
same ID has already taken the exact replay path; a different successor remains a
conflict. `created_at` is generated only for a genuinely new row.

### Review validates and returns under the same reservation

Review performs row/status/target-history validation, snapshot and indexed-text
integrity, official observation/seed/source-chain/quote validation, and chronology
after `BEGIN IMMEDIATE`. It then performs the candidate-only update, inserts the
exact decision event, re-reads the final row/history parity, and constructs the
return value before commit. No status or provenance read after commit contributes
to the reported success.

Concurrent callers therefore have deterministic semantics: the first reserved
writer may finish; a simultaneous loser receives typed contention. If that loser
explicitly retries after commit, normal immutable-review or replacement-conflict
rules apply.

### CLI reports a retryable operation failure, not success

The existing top-level CLI error boundary maps `PublicCorpusBusyError` through its
`ValueError` ancestry to exit code 2, stderr, and no JSON success payload. The
error text is stable Russian prose explaining that the cache is busy, nothing was
recorded by this attempt, and the user may repeat it later. Help describes that
the tool itself does not retry. This is an operational retry instruction, not an
automatic legal decision or filing action.

## Risks / Trade-offs

- [A long filesystem integrity read holds the SQLite writer reservation] -> Keep
  the current exact integrity checks and prefer correctness at this low-volume
  human-review boundary; surface contention without hidden waiting or retry.
- [An unrelated process mutates object bytes during the transaction] -> Do not
  claim filesystem atomicity; validate object bytes inside the decision path and
  retain downstream export/live-cache integrity gates.
- [Legacy data has tolerated malformed history] -> Fail closed and leave it visible
  to existing quality-export blockers; do not silently repair evidence history.
- [Commit is blocked by a concurrent reader in DELETE journal mode] -> Treat it as
  contention and explicitly roll back both row and history.
- [A caller already owns a transaction] -> Reject without altering that transaction
  so transaction ownership is never ambiguous.
- [Restoring the caller connection's prior timeout fails] -> Close the connection
  when possible, always quarantine the corpus object, and report the known commit
  outcome or an explicitly uncertain outcome so the caller cannot unknowingly
  reuse altered connection state or blindly repeat a committed legal-review
  decision.
- [Commit or rollback reports failure after changing transaction state] -> Inspect
  the active-transaction flag; accept an ordinary busy result only after a known
  rollback, otherwise quarantine and require a manual row/history check.

## Migration Plan

1. Add failing deterministic tests for ordering, contention, rollback, exact replay,
   forged history, source/predecessor races, classifier boundaries, and CLI output.
2. Add the private transaction/error/history helpers and refactor the two treatment
   methods without changing their public signatures.
3. Update installed Russian treatment-review guidance and help.
4. Run focused, full skill, repository, OpenSpec, strict source, clean-install, and
   offline self-containment verification.
5. Archive this change, publish one atomic commit to the feature branch and main,
   verify both remote SHAs, and install that exact published tree globally.

Rollback is the preceding skillset commit. No schema/data migration is required;
corrupt legacy history remains candidate/blocker evidence rather than being changed.

## Open Questions

None.
