## ADDED Requirements

### Requirement: Treatment writes use one reserved provenance transaction

Treatment proposal and review MUST acquire an owned `BEGIN IMMEDIATE` transaction
before the first database-backed provenance read. The same transaction MUST contain
all snapshot, indexed-text, official-source, source-chain, treatment, predecessor,
successor, current-history, mutation, exact-history-insert, and final-result reads
needed by that operation. It MUST commit explicitly only after all checks and writes
succeed, and MUST roll back both treatment state and history on any body or commit
failure. Pure row-independent argument and finite canonical-JSON validation MAY
precede the transaction. A caller-owned transaction MUST be rejected without being
committed or rolled back, and a successful result MUST NOT depend on a post-commit
database read.

#### Scenario: Source binding cannot change between review and decision

- **WHEN** a second SQLite connection attempts to change the indexed source-chain,
  treatment source, official observation, or other reviewed database provenance
  after review validation has begun
- **THEN** that mutation cannot interleave before the treatment decision commits
- **AND** the successful result and immutable history bind the same protected state

#### Scenario: Proposal predecessor cannot change between validation and insertion

- **WHEN** a replacement proposal validates a completed predecessor while another
  writer attempts to change that predecessor or create a competing successor
- **THEN** at most one protected state is committed
- **AND** the losing operation records neither a treatment row nor a history event

#### Scenario: Commit failure is atomic

- **WHEN** the treatment mutation and history insert run but the transaction cannot
  commit
- **THEN** both changes are rolled back
- **AND** the connection no longer owns the failed transaction

#### Scenario: Caller transaction ownership is preserved

- **WHEN** proposal or review is invoked while its connection already has a caller-
  owned transaction
- **THEN** the operation fails before changing treatment state
- **AND** it neither commits nor rolls back the caller's transaction

### Requirement: Treatment contention is typed and never retried internally

The reserved treatment transaction MUST temporarily use zero SQLite busy timeout,
perform only one begin/write/commit attempt, and restore the connection's prior busy
timeout after success or failure before that connection is reused. If restoration
fails, the corpus connection MUST be quarantined, low-level close MUST be attempted,
and a distinct diagnostic MUST identify the transaction outcome as committed, not
committed, or uncertain and disclose when close was not confirmed. The timeout-zero
attempt MUST itself be inside this cleanup boundary. A restoration, rollback, or
uncertain post-commit error MUST NOT be mislabeled as the ordinary nothing-recorded
contention case. Only SQLite `BUSY` and `LOCKED`, including their extended result
codes, MUST become a dedicated `PublicCorpusBusyError`; unrelated operational, I/O,
read-only, or integrity failures MUST NOT be mislabeled. This no-retry boundary
applies to the treatment transaction, not to earlier writable-corpus construction
or schema/search initialization.

#### Scenario: Another writer owns the reservation

- **WHEN** proposal or review reaches its transaction boundary while another
  connection holds the SQLite writer reservation
- **THEN** it makes one begin attempt and raises `PublicCorpusBusyError`
- **AND** it adds no treatment/history state and restores the prior busy timeout

#### Scenario: A reader prevents DELETE-mode commit

- **WHEN** the transaction reaches commit while another connection's read snapshot
  prevents an exclusive commit
- **THEN** it raises `PublicCorpusBusyError` without retry
- **AND** its treatment mutation and history insertion are rolled back together

#### Scenario: Explicit retry observes the committed winner

- **WHEN** a contending caller explicitly repeats the operation after the winning
  transaction has committed
- **THEN** ordinary exact-replay, immutable-review, or replacement-conflict rules
  apply to the now-current state
- **AND** the runtime does not fabricate or choose a second legal-review decision

#### Scenario: Timeout restoration fails after a known transaction outcome

- **WHEN** SQLite cannot restore the prior busy timeout after the treatment
  transaction has committed or rolled back
- **THEN** the runtime quarantines that connection, attempts low-level close, and
  does not return the corpus object for reuse
- **AND** the error distinguishes committed from not-committed state and requires
  reopening the cache before any deliberate follow-up

#### Scenario: Commit outcome becomes uncertain

- **WHEN** a commit attempt changes SQLite transaction state but reports an error
  before the runtime can confirm successful completion
- **THEN** the runtime does not report the ordinary nothing-recorded busy result
- **AND** it quarantines the corpus connection and requires manual comparison of
  the treatment row with its exact history before any deliberate retry

#### Scenario: Rollback cannot be confirmed

- **WHEN** rollback of an active owned treatment transaction reports failure
- **THEN** the runtime quarantines the corpus connection and attempts low-level close
- **AND** the diagnostic reports an uncertain outcome rather than allowing later
  corpus work to commit partial treatment state

#### Scenario: Zero-timeout setup reports failure after application

- **WHEN** the attempt to set zero busy timeout changes connection state and then
  reports an error before any treatment transaction begins
- **THEN** the cleanup boundary restores the caller's prior timeout or quarantines
  the connection if restoration cannot be confirmed

### Requirement: Treatment history is exact at every write boundary

History insertion MUST be a non-ignoring exact insert that affects one row. A new
treatment and its `candidate_created` event MUST be indivisible, as MUST a review
status update and its `verified` or `rejected` event. A candidate is reviewable only
when its complete current history is the sole canonical `candidate_created` event:
null reviewer, event time equal to immutable `created_at`, exact proposal payload,
and recomputed deterministic history ID. Missing, extra, malformed, colliding, or
mismatching history MUST fail before or roll back the mutation and MUST NOT be
silently repaired.

An exact deterministic proposal replay, including a replacement replay, MUST be
idempotent only when the existing row's immutable proposal columns and complete
status-appropriate history are exact. It MUST return the stored status from inside
the reserved transaction without another history event. A same-ID mismatch or a
different successor MUST fail as corruption or conflict.

#### Scenario: Forged decision-history collision does not promote a candidate

- **WHEN** a row already occupies the deterministic history ID required by a review
- **THEN** the exact insert fails and the candidate status remains unchanged
- **AND** the forged row is not treated as the decision just requested

#### Scenario: Candidate base history is missing or changed

- **WHEN** `candidate_created` is absent, duplicated, has changed payload, reviewer,
  timestamp, or ID, or another event is already present on a candidate
- **THEN** review fails before the treatment update
- **AND** the evidence history remains available for quality-export diagnosis

#### Scenario: Exact proposal is safely replayed

- **WHEN** a caller repeats the exact ordinary or replacement proposal after losing
  its prior successful response
- **THEN** the existing status is returned without inserting another row or event
- **AND** any mismatch in the stored immutable row or status-appropriate history
  turns the replay into a fail-closed error

#### Scenario: History insertion aborts proposal or review

- **WHEN** a trigger, constraint, collision, or row-count failure prevents the exact
  candidate or decision history insert
- **THEN** the paired treatment insert or status update is rolled back
- **AND** the operation does not report success
