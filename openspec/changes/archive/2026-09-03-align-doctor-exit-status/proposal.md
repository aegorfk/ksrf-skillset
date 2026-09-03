## Why

`ksrf doctor` can produce a valid report whose top-level state is `blocked`
while still returning process code `0`. A person sees the warning in prose or
JSON, but shell scripts, CI, and agent workflows read the command as success
unless they reimplement the report semantics. This is a false-green at the
exact point intended to diagnose whether a selected profile can run.

## What Changes

- Return code `0` only when the selected profile is `ready` or `degraded` and
  work can continue within the limitations shown in the report.
- Return code `3` when a successfully generated doctor report is `blocked` or
  has any unrecognized non-usable top-level state.
- Preserve code `2` for invalid arguments, malformed manifests, and other
  existing input-contract errors.
- Keep the complete human or JSON report on stdout for every valid diagnostic
  result, including blocked results; keep stderr empty in those cases.
- Apply the same behavior to `ksrf.py doctor` and the compatible
  `ksrf_setup_doctor.py` launcher in source and clean-installed payloads.
- Document the codes without changing capability probes, classifications,
  network authorization, or remediation content.

## Capabilities

### New Capabilities

- `ksrf-doctor-exit-status`: machine-readable process status aligned with the
  existing capability-doctor report state.

### Modified Capabilities

- None.

## Impact

- Runtime: `skills/ksrf-complaint-cycle/lib/ksrf/filing/cli.py`.
- User guidance: repository README and installed setup/router references.
- QA: deterministic ready, degraded, blocked, and usage-error tests for both
  launchers, including clean installation.
- No installation, account creation, network request, document transmission,
  legal assessment, promotion, release, or filing authority is added.
