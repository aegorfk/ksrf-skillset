## Why

The public practice-analysis integration guide sends users directly to
`ksrf_practice_analysis.py --help`, but 36 of its 42 public arguments currently
have no explanation. A user can see Russian option placeholders without knowing
which file to provide, where state is stored, what an omitted selector means,
or when a result remains audit-only.

## What Changes

- Give every public argument on all 18 practice-analysis help routes a concise
  plain-Russian explanation.
- Correct route summaries whose wording overstated result trust or the scope of
  attach/lint operations.
- Explain file, folder, workspace, identifier, reviewer, date, and export roles
  at the option that consumes them.
- State meaningful defaults and omission behavior, including claim selection,
  output export, skills-root discovery, corpus cutoff, and stage selection.
- Keep legal and evidence gates explicit: attaching or importing data does not
  by itself approve a finding or make it filing-ready.
- Preserve every command, option, choice, alias, destination, default, handler,
  JSON field, error, exit code, and non-help execution path.
- Add exhaustive source and clean-runtime regression coverage for all 42 public
  argument actions and all 18 routes, including readable 60–80-column
  rendering without splitting paths or machine tokens.

## Capabilities

### Modified Capabilities

- `ksrf-user-facing-cli`: require actionable Russian argument help throughout
  the practice-analysis CLI.

## Impact

- Runtime: help-only presentation in
  `ksrf-complaint-cycle/scripts/ksrf_practice_analysis.py`; parsing and command
  execution are unchanged.
- Source-only: OpenSpec and focused regression tests.
- No schema, artifact, network, legal-methodology, parser-contract, or execution
  behavior change.
