## Why

After the doctrine-research and authority-ledger release, six documented runtime
commands still mix Russian descriptions with English `argparse` headings,
built-in help text, and value placeholders. A Russian-speaking user therefore
meets `usage`, `options`, `show this help message and exit`, and identifiers such
as `WORKSPACE` or `INPUT` in otherwise Russian workflows.

## What Changes

- Render Russian help scaffolding and value placeholders for every reachable
  help route of the remaining documented runtime commands.
- Replace English maintainer jargon in existing command descriptions with clear
  Russian wording while preserving executable command, option, choice, and JSON
  tokens.
- Give the standalone argument-research validator an explanatory Russian help
  message instead of its current bare English usage line.
- Preserve non-help usage/errors, defaults, exit codes, hidden test switches,
  and all execution behavior.
- Add clean-runtime tests for current Python and the bundled legacy system
  Python where available.

## Capabilities

### Modified Capabilities

- `ksrf-user-facing-cli`: extend the Russian help-language contract to the six
  remaining documented runtime entry points.

## Impact

- Runtime: help rendering in three skills and six public entry points, including
  their nested subcommands.
- Source-only: OpenSpec and regression tests.
- No schema, network, legal methodology, command token, machine output, or
  non-help behavior change.
