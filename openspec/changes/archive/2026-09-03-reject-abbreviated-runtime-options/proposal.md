# Change: Reject abbreviated options in public KSRF runtime commands

## Why

Python `argparse` accepts unique prefixes of long options by default. As a
result, a mistyped command such as `ksrf.py matter init --matter-i ... --worksp
...` is silently treated as the documented `--matter-id` and `--workspace` and
creates a matter workspace. The user receives success for option tokens that
the skill never documented or asked them to approve.

## What Changes

- Disable long-option abbreviation in every public installed `argparse`
  command and in every nested subparser.
- Reject abbreviated or mistyped long options with exit code `2` before a
  handler, filesystem write, network action, or external process can run.
- Preserve exact documented long options, short options such as `-h`, aliases,
  help text, defaults, destinations, output schemas, and handler behavior.
- Add a parser-inventory contract plus source and clean-installed subprocess
  regressions, including a mutating `matter init` route.

## Impact

- Affected runtime: documented KSRF CLI entrypoints backed by `argparse`.
- Affected contract: user-facing CLI exactness; previously accepted
  undocumented long-option prefixes become invalid.
- User-visible benefit: a typo cannot silently select an option and start a
  different or mutating operation.
