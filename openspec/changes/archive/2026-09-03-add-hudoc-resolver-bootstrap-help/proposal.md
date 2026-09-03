# Change: Add safe bootstrap help to unconfigured HUDOC resolvers

## Why

The bundled HUDOC knowledge and vector resolver commands require an external,
version-checked engine. Their own user guidance says to begin with `--help`, but
when no engine is configured both wrappers currently exit `1` with only a
configuration error. A user cannot discover the required environment variables
or understand that engine-specific options remain unavailable until setup.

## What Changes

- When and only when both resolver-specific configuration variables are absent,
  accept an exact `-h` or `--help` request locally.
- Print concise Russian bootstrap guidance: what is missing, the two explicit
  configuration routes, required interface versions, disabled implicit search,
  and how to obtain the real engine help after setup.
- Complete local bootstrap help with code `0`, stdout only, before candidate
  discovery, Git worktree inspection, version-file reads, or process execution.
- Preserve fail-closed behavior for unconfigured non-help invocations, combined
  help plus extra tokens, and every explicitly present blank, invalid, or
  incompatible configuration.
- Preserve exact version gates, direct-path precedence, repository worktree
  discovery, environment construction, and argv forwarding whenever a resolver
  is configured.

## Impact

- Affected runtime: `hudoc_kb_cli.py` and `hudoc_vector_cli.py`.
- Affected contracts: the existing external HUDOC resolution boundary plus a
  dedicated bootstrap-help capability.
- Affected QA: resolver interface contract and clean-runtime help checks.
- User-visible benefit: a first-time user can obtain actionable setup guidance
  without weakening any engine compatibility or legal-source gate.
