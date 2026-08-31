## ADDED Requirements

### Requirement: Doctrine sources are bound to selected current-run queries

Workspace validation MUST accept a doctrine source record only when
`query_ids` is a non-empty, duplicate-free list and every value is a
non-empty string present both in the current query plan and in
`search-run-config.json.selected_query_ids`.

#### Scenario: Stale query identifier is rejected

- **GIVEN** the current plan and run select `q-live`
- **AND** a source record carries `query_ids = [q-stale]`
- **WHEN** the workspace is validated
- **THEN** validation fails
- **AND** the error identifies the source and stale query identifier

#### Scenario: Planned but unselected query is rejected

- **GIVEN** `q-planned` exists in the current query plan
- **AND** `q-planned` is absent from the current run's selected query IDs
- **AND** a source record carries `query_ids = [q-planned]`
- **WHEN** the workspace is validated
- **THEN** validation fails

#### Scenario: Forged selected-query list is rejected

- **GIVEN** a planned but previously unselected query ID is appended to
  `search-run-config.json.selected_query_ids`
- **AND** the stored run-config and coverage hashes are left unchanged
- **WHEN** the workspace is validated
- **THEN** validation fails on the recomputed run-config hash

#### Scenario: Rehashed forged selection is rejected

- **GIVEN** a planned but unselected query ID is appended to the selected list
- **AND** both the run-config and coverage hashes are recomputed consistently
- **AND** `max_queries` is unchanged
- **WHEN** the workspace is validated
- **THEN** validation fails because the list differs from deterministic bounded
  selection

#### Scenario: Rehashed larger run without logged attempts is rejected

- **GIVEN** `max_queries` and the selected-query list are increased consistently
- **AND** run-config and coverage hashes are recomputed
- **AND** `search-log.jsonl` still contains only the original attempts
- **WHEN** the workspace is validated
- **THEN** validation fails because the selected provider/query matrix does not
  match the actual search log

#### Scenario: Self-consistent foreign query plan is rejected

- **GIVEN** an observed query plan is changed and self-consistently rehashed
- **WHEN** the workspace is validated against the bound request snapshot
- **THEN** validation fails because the plan differs from the deterministic
  request-derived plan

#### Scenario: Run configuration is bound to the current query plan

- **GIVEN** a run configuration whose `query_plan_hash` differs from the
  current plan
- **WHEN** the workspace is validated
- **THEN** validation fails before its selected query IDs can be trusted

#### Scenario: Selected current query is accepted

- **GIVEN** `q-live` exists in the current plan and selected-query list
- **AND** a valid source record carries `query_ids = [q-live]`
- **WHEN** the workspace is validated
- **THEN** no source-query binding error is added

#### Scenario: Malformed source query IDs fail closed

- **GIVEN** a source record has missing, empty, duplicate, non-list, or
  non-string `query_ids`
- **WHEN** the workspace is validated
- **THEN** validation fails without raising an unhandled exception

#### Scenario: Malformed run configuration fails closed

- **GIVEN** source records and a `search-run-config.json` that is not valid JSON
- **WHEN** the workspace is validated
- **THEN** validation returns `status=fail` without raising an unhandled
  exception

#### Scenario: Incomplete search run is not plan-only

- **GIVEN** a workspace contains a run configuration or source/search artifact
- **AND** `coverage-report.json` is absent
- **WHEN** the workspace is validated
- **THEN** validation fails as an incomplete search run
- **AND** the plan-only warning is not emitted

#### Scenario: Plan-only workspace remains valid

- **GIVEN** a valid plan-only workspace has no search/run artifacts
- **WHEN** the workspace is validated
- **THEN** the existing plan-only warning is preserved
- **AND** no source-query binding error is added
