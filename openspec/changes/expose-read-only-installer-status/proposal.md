## Why

The transactional installer now fails closed when an interrupted or suspicious installation needs attention, but users cannot inspect that state without attempting another mutating install or reading private journal details by hand. A stable read-only status command is needed so a user or automation can distinguish a clean target from an active transaction, recoverable interruption, or corrupt evidence before deciding what to do next.

## What Changes

- Add a status-only installer command that performs no filesystem writes, creates no lock or temporary artifacts, and never initiates recovery or cleanup.
- Return a stable JSON report and concise human-readable Russian output describing the target, observed transaction state, severity, and safe next action.
- Use fail-closed classifications for ambiguous paths, malformed journals, multiple transaction roots, symlink substitution, and inconsistent generation evidence.
- Document that the result is a bounded observation rather than a lock-backed snapshot and does not certify later installation success.

## Capabilities

### New Capabilities

- `ksrf-skillset-install-status`: Read-only inspection, stable classifications, output schema, exit codes, and safety boundaries for transactional installation state.

### Modified Capabilities

None.

## Impact

- `tools/install_skillset.py` command-line interface and read-only state inspection helpers.
- `install.sh` user entry point and public README instructions.
- Root installer tests, including filesystem write-detection and adversarial path/journal fixtures.
- `skills-manifest.json` release hashes after implementation.
