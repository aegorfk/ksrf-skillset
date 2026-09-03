## Context

`diagnose_capabilities()` already derives one of three top-level report states:
`ready`, `degraded`, or `blocked`. Individual capability rows may use more
specific states, but the top-level classification intentionally answers
whether the selected profile has a blocking required gap. The shared CLI
renders this report and then falls through to an unconditional `return 0`, so
its process contract contradicts its own top-level state.

Both public doctor entry points call the same `ksrf.filing.cli.main`: the
`ksrf.py doctor` route passes normal arguments, while
`ksrf_setup_doctor.py` prepends `doctor`. The correction therefore belongs in
the shared command branch rather than duplicated launcher logic.

## Goals / Non-Goals

- Goals:
  - make valid blocked diagnostics machine-detectable without parsing output;
  - preserve the full actionable report on stdout for humans and automation;
  - keep ready and degraded profiles usable with code `0`;
  - keep invalid command/manifests distinct at code `2`;
  - prove identical behavior in source and clean installation.
- Non-Goals:
  - change probe execution, profile requirements, or state derivation;
  - treat optional gaps or `degraded` as a hard failure;
  - add an `exit_code` field to the report schema;
  - install missing programs, create accounts, enable network access, or
    attempt remediation;
  - infer legal readiness from operational capabilities.

## Decisions

### Map only top-level usability to the process code

The doctor command maps top-level `ready` and `degraded` to code `0` because
the selected profile can operate, subject to the report's stated limits. It
maps `blocked` to code `3`, matching other valid-but-blocked KSRF workflow
results. Any future or malformed top-level state also fails closed with code
`3`; manifest and argument contract failures continue through the existing
exception handler as code `2`.

Individual row states do not directly determine the exit code. For example,
an optional `unavailable` capability correctly contributes to a top-level
`degraded` report and remains code `0`; a required unavailable capability with
`blocking_when_missing=true` produces top-level `blocked` and code `3`.

### Preserve report channels and bytes

The branch first builds and renders the same report. JSON and human output stay
on stdout even for code `3`, because they contain the missing capability and
remediation. Valid diagnostic results keep stderr empty. No report field,
ordering, timestamp, probe, or network-authorization behavior changes.

### Share one implementation across both launchers

The shared CLI initializes a default exit code of `0`; only the doctor branch
replaces it from the top-level report state. Start, matter, intake, and workflow
routes retain their existing exit behavior. Both source launchers and their
installed copies therefore inherit the same mapping without wrapper-specific
special cases.

## Risks / Trade-offs

- Existing callers that treated a blocked doctor run as successful will now
  receive code `3`. That is the intentional correction; the stdout report is
  unchanged so callers can still inspect remediation details.
- `degraded` remains code `0`, so callers that need a completely ready profile
  must continue to inspect `state`. This avoids turning optional tools into
  mandatory blockers.
- Code `3` denotes an operationally blocked profile, not a legal decision and
  not an authorization to remediate automatically.

## Verification

Tests create deterministic minimal manifests for ready, degraded, and blocked
top-level states. They invoke both public launchers in human and JSON modes
from the source tree and a clean installation, asserting exact codes, stdout
state, empty stderr, no writes to the manifest, and no network authorization.
An invalid-manifest control retains code `2`. Full root and per-skill suites,
strict source/runtime validation, offline containment, quick validation,
OpenSpec, manifest, independent review, atomic publication, and installed
current verification remain release gates.
