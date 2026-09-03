## Context

Both public doctor launchers use the same `argparse` subparser from
`ksrf.filing.cli`. The runtime already maps `ready` and `degraded` to `0`, input
errors to `2`, and blocked or unknown report states to `3`. The repository README
documents that mapping, but neither launcher exposes it where users naturally
look: `--help`.

## Goals / Non-Goals

**Goals:**

- Explain the complete stable mapping in plain Russian in both help routes.
- Preserve the fact that blocked reports remain available on stdout.
- Preserve the no-installation and no-automatic-remediation boundary.
- Prove source/install and supported-Python parity.

**Non-Goals:**

- Adding an `exit_code` JSON field or changing report schemas.
- Changing classification, probes, network behavior, or process codes.
- Treating `degraded` as filing readiness or repairing unavailable capabilities.

## Decisions

1. Put the guide in the shared doctor parser `epilog`. This gives both launchers
   one authoritative text and avoids duplicating wrapper behavior. Adding it to
   option help was rejected because the mapping describes the command result,
   not one argument.
2. Name both the human meaning and stable machine state tokens. Automation
   authors can correlate stdout JSON with the process code, while ordinary users
   still get a plain-language explanation.
3. Assert the text through subprocess calls for source and clean-installed
   launchers. Parser-only assertions would miss wrapper/import divergence.
4. Keep the help-only change outside the parser machine-contract digest: no
   action, option, default, handler, metavar, or usage string changes.

## Risks / Trade-offs

- [Help could drift from runtime mapping] → Test all three documented codes and
  retain focused runtime mapping tests beside the help assertions.
- [Technical state tokens reduce readability] → Pair each token with its Russian
  operational meaning.
- [Wrapper output could diverge after packaging] → Exercise both entry points
  from a clean installation as well as the source tree.

## Migration Plan

Publish and install as a normal manifest-bound skillset release. Rollback is the
previous commit; no user data or workspace migration is required.

## Open Questions

None.
