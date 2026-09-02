## Why

Two runtime command-line tools that are linked directly from user-facing KSRF skills still render English descriptions and the default English `argparse` scaffolding. A Russian-speaking user sees `usage`, `options`, and `show this help message and exit` at the point where the skill is supposed to explain the next action plainly.

## What Changes

- Render Russian root and subcommand help for the documented doctrine-research CLI.
- Render Russian help for the documented authority-ledger validator.
- Describe every public argument in Russian while preserving command names, option names, defaults, exit codes, JSON, and execution behavior.
- Suppress the test-only doctrine fixture switch from public help without removing or changing that test path.
- Add clean-runtime subprocess tests that fail if English `argparse` scaffolding or the hidden fixture switch returns.

## Capabilities

### New Capabilities

- `ksrf-user-facing-cli`: documented runtime CLIs provide actionable Russian help without exposing test-only switches.

## Impact

- Runtime files: two Python entry points only.
- Source-only files: OpenSpec and regression tests.
- No schema, network, legal-methodology, option-name, or machine-output change.
