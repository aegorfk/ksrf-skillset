## Why

Users can inspect installation structure with `./install.sh --status` and compare
content with remote `main` using `--verify-current`, but the complete offline
runtime-content check still requires a long internal Python command. A short,
network-free public command makes local integrity verification discoverable and
usable when GitHub is unavailable.

## What Changes

- Add `./install.sh --verify [--target PATH]` as a read-only, offline runtime
  content and self-containment check.
- Add one repo-side coordinator that binds the lexical target identity across
  structural preflight, runtime validation, and postflight so an installed
  target never supplies policy and root replacement cannot inherit success.
- Give the mode stable outcomes: `0` for a complete valid runtime, `1` for a
  target/preflight/validation failure, and `2` for invalid CLI usage or an
  unexpected validator failure.
- Keep `--status --json`, `--verify-current`, and normal installation
  behavior backward-compatible; verification modes remain mutually exclusive.
- Document clearly that offline integrity does not establish freshness,
  source/release QA, current law, or filing readiness.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-skillset-install-status`: expose the existing strict offline runtime
  validator through a short, repo-side, non-mutating public command with stable
  CLI and output boundaries.
- `ksrf-runtime-payload-boundary`: let a trusted coordinator bind the expected
  runtime-root identity and require a stable final content observation before
  verification success.

## Impact

- Public shell entry point: `install.sh`.
- Repo-side coordinator: `tools/install_skillset.py`.
- Runtime validator: expected-root guard and stable offline final identity pass.
- User guidance: `README.md` and the complaint-cycle skill instructions.
- Wrapper/status regression tests: `tests/test_install_skillset_status.py`.
- Validator regressions:
  `skills/ksrf-complaint-cycle/tests/test_validate_ksrf_skillset.py`.
- No dependency, payload-layout, network-policy, or installer-transaction
  change.
