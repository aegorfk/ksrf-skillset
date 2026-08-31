# Change: Enforce doctrine source query binding

## Why

`ksrf-doctrine-research` currently accepts `source-ledger.jsonl` records whose
`query_ids` do not belong to the current `query-plan.json` or the selected
queries in `search-run-config.json`. A stale source from another bounded run
can therefore validate as if it were discovered by the current run.

## What Changes

- Require every source record to carry a non-empty, duplicate-free list of
  non-empty string query identifiers.
- Require each source query identifier to exist in the current query plan and
  in the current run's selected query identifiers.
- Recompute the run-configuration hash from the actual file and bind its
  query-plan hash to the current plan before trusting selected query IDs.
- Rebuild the expected plan from the request snapshot and derive the exact
  bounded selected-query sequence from that plan and `max_queries`.
- Require the selected query/provider matrix to match the actual entries in
  `search-log.jsonl` before any source can rely on those query IDs.
- Fail closed when a source ledger exists without the run configuration needed
  to prove the selected-query binding, including malformed JSON.
- Treat a workspace with search/run artifacts but no coverage report as an
  incomplete run, not as a valid plan-only workspace.
- Add deterministic negative and positive tests plus a bounded skill eval.

## Impact

- Scope is limited to `ksrf-doctrine-research` workspace QA.
- Plan-only workspaces without source records remain valid with their existing
  warning.
- Provider routing, transport, legal roles, and promotion rules are unchanged.
- The change does not make doctrine an official source or filing authority.
