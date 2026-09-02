## Why

The clean `--status` result still sends every user directly to the online
`--verify-current` command even though the repository now exposes a shorter,
network-free `--verify` check. Users should discover the cheapest local check
first and opt into network freshness only when they need it.

## What Changes

- Change the clean status recommendation into two ordered steps: offline
  content verification first, optional online comparison second.
- Keep the stable status JSON shape and exit codes unchanged; only the existing
  `recommended_action` text changes.
- Keep both commands exact-target, shell-safe, repo-side, and purely advisory:
  `--status` itself remains read-only and offline.
- Preserve the existing honest fallback when an executable command cannot be
  rendered safely.
- Update user guidance and regression tests for human and JSON status output.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-skillset-install-status`: clean status guidance now presents offline
  integrity verification before optional online freshness verification.

## Impact

The change affects `tools/install_skillset.py`, status tests, README guidance,
the release manifest, and the existing installation-status specification. It
does not change installation, verification algorithms, network behavior,
status schema keys, or exit codes.
