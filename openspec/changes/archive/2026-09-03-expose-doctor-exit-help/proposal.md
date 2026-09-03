## Why

`ksrf doctor` now returns distinct process codes for usable, invalid, and
blocked outcomes, but its own `--help` output does not explain them. Users and
automation authors should not have to discover that contract by experiment or
by reading repository-only documentation.

## What Changes

- Add a concise Russian exit-code guide to the `doctor --help` output shared by
  `ksrf.py doctor` and `ksrf_setup_doctor.py`.
- Explain that a blocked report remains on stdout and that doctor does not
  install or repair anything automatically.
- Verify identical help from the source tree and a clean user installation,
  including supported legacy Python.
- Preserve every command, option, default, report field, non-help output, and
  execution path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-doctor-exit-status`: make the published `0`/`2`/`3` process contract
  discoverable from both public launcher help routes.
- `ksrf-user-facing-cli`: require the doctor help to explain exit outcomes in
  plain Russian without changing its machine contract.

## Impact

- Shared parser construction in
  `skills/ksrf-complaint-cycle/lib/ksrf/filing/cli.py`.
- Source/install help-contract tests and release manifest.
- No new dependency, network access, probe, mutation, or legal-readiness
  authority.
