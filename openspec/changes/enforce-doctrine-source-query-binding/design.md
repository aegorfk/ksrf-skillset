# Design: Doctrine source-to-query provenance binding

## Context

`validate_workspace()` checks duplicate plan IDs and source promotion/status,
but it does not compare `DoctrineSourceRecord.query_ids` with the current plan
or run configuration.

The frozen offline fixture demonstrates the gap:

- the plan and run select `q-live`;
- the source is changed to `query_ids = [q-stale]`;
- baseline and stale variants both return `status=pass` and `errors=[]`.

## Decisions

1. Build a validated set of non-empty string query IDs from the current query
   plan.
2. Rebuild the expected query plan from the bound request snapshot and require
   the observed plan hash to match that deterministic result.
3. When `search-run-config.json` exists, parse it without allowing malformed
   JSON to escape workspace QA, recompute its hash from the actual core, bind
   its `query_plan_hash` to the current query plan, and require its selected
   query sequence to equal `select_bounded_queries(expected_plan, max_queries)`.
4. For every source record, require `query_ids` to be a non-empty,
   duplicate-free list whose elements are non-empty strings.
5. Check every source query ID against both the plan and selected-query set.
6. If source records exist but the run configuration is absent or malformed,
   emit a fail-closed validation error.
7. Attach errors to the source ID and offending query ID so stale provenance
   is diagnosable.
8. Do not trust two copied `run_config_hash` values: compare the recomputed
   hash with both the stored run-config hash and the coverage artifact.
9. Emit the plan-only warning only when no search/run artifacts exist. If a
   run configuration, log, source ledger, problem candidates, or acquisition
   queue exists without coverage, fail as an incomplete search run.
10. Require exactly one logged attempt for every selected provider/query pair
    and no extra pairs. A source query ID is current-run provenance only when
    the corresponding matrix is present in `search-log.jsonl`.

## Alternatives Considered

- Checking only plan membership was rejected because a plan may contain
  queries that were not selected for the bounded run.
- Checking only the run configuration was rejected because stale or malformed
  run configuration must not create authority outside the reviewed plan.
- Changing provider, coverage, or promotion semantics was rejected as outside
  this candidate.

## Verification

- RED: an otherwise valid source using `q-stale` fails after the change.
- Positive: the source's original selected query ID remains valid.
- Planned-but-unselected query IDs fail.
- A forged selected-query list retaining the old hash fails.
- A forged selected-query list with recomputed run/coverage hashes still fails
  deterministic bounded selection.
- A self-consistently rehashed query plan that differs from the request fails.
- Increasing `max_queries` and rehashing config/coverage without the matching
  logged attempts fails.
- Malformed run-config JSON returns `status=fail` instead of raising.
- Search artifacts without a coverage report fail and are not called plan-only.
- Missing, empty, or non-string source query IDs fail without exceptions.
- Full skill tests, root tests, strict validators, OpenSpec strict validation,
  offline self-containment, and clean-room installation must pass.
