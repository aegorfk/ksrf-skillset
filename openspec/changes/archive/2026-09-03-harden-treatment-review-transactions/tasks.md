## 1. Transaction and history contract tests

- [x] 1.1 Add deterministic ordering tests proving that proposal and review reserve
  the writer before their first database-backed provenance read.
- [x] 1.2 Add busy/locked classifier and held-writer tests for one attempt, typed
  error, unchanged state, restored timeout, and explicit retry semantics.
- [x] 1.3 Add DELETE-mode commit-contention and trigger/collision tests proving full
  rollback of treatment plus history.
- [x] 1.4 Add adversarial source/predecessor/successor race tests and caller-owned
  transaction ownership tests.
- [x] 1.5 Add exact ordinary/replacement replay and missing/extra/forged-history tests.

## 2. Reserved treatment runtime

- [x] 2.1 Add the typed contention classifier/error and an owned no-retry
  `BEGIN IMMEDIATE` helper with explicit commit, rollback, and timeout restoration.
- [x] 2.2 Add canonical proposal/history parity validation and non-ignoring exact
  history insertion with actionable treatment errors.
- [x] 2.3 Refactor proposal so snapshot, replay, predecessor/successor, insert,
  history, and result are checked inside the one reservation.
- [x] 2.4 Refactor review so all database provenance, candidate history, update,
  decision history, and final parity are checked inside the one reservation.

## 3. Installed user guidance

- [x] 3.1 Add stable Russian busy wording and no-retry guidance to treatment CLI
  help without implying constructor-level fail-fast behavior.
- [x] 3.2 Update the installed treatment-review methodology reference with atomicity,
  explicit retry, legacy-corruption, and filesystem-boundary guidance.

## 4. Verification and release

- [x] 4.1 Run focused treatment transaction, CLI, history, and concurrency tests.
- [x] 4.2 Run full skill and repository tests, strict source validation, manifest,
  clean-install verification, and offline self-containment checks.
- [x] 4.3 Complete tasks, validate/archive OpenSpec, and revalidate archived specs.
- [x] 4.4 Commit atomically, push feature and exact commit to main, verify remote
  SHAs, and install that exact published tree globally.
