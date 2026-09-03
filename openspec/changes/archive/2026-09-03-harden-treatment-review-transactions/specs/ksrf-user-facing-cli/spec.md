## ADDED Requirements

### Requirement: Treatment contention is actionable in the installed CLI

Installed treatment-discover and treatment-review commands MUST report transaction-
level SQLite contention as a stable Russian error on stderr with exit code 2 and no
success JSON on stdout. The message/help MUST explain that this attempt recorded
nothing, performs no automatic retry, and may be explicitly repeated after the
other cache operation finishes. It MUST NOT claim that corpus construction before
the transaction boundary is immediate, or that a retry supplies legal approval.

#### Scenario: Cache is busy at the treatment transaction boundary

- **WHEN** another SQLite connection owns a conflicting reservation as treatment
  proposal or review begins its reserved transaction
- **THEN** the installed command returns code 2 with an actionable Russian error
- **AND** stdout contains no success record and no hidden retry occurs

#### Scenario: User reads treatment command help

- **WHEN** a user opens help for treatment discovery or review
- **THEN** the help states that busy treatment writes are not retried automatically
- **AND** it tells the user to repeat the command only after the other operation ends
