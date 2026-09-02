## Why

The source-independent installer status is safe and bounded, but a structurally valid retained transaction is currently traversed four times: a raw fingerprint pass and a semantic validation pass for each of the two comparison samples. Large interrupted installations therefore pay roughly twice the payload I/O needed by the two-sample concurrency contract. Mount-table discovery is also repeated for every opened directory on Linux.

## What Changes

- Make semantic validation the primary observation so a valid recovery state needs one complete traversal per comparison sample rather than an unconditional raw plus semantic traversal.
- Reuse the already complete semantic fingerprint when validation fails after all evidence and live skills have been sampled; use one bounded raw completion pass only for failures that occur before a comparable full fingerprint exists.
- Use Linux descriptor-bound mount IDs for directory boundary checks. If Linux exposes mountinfo but fd mount IDs cannot be read, retain the current live per-directory fallback; on hosts without Linux mountinfo, avoid repeatedly rediscovering the same empty set while retaining `os.path.ismount()`.
- Add instrumented regressions proving reduced reads without changing status, exit codes, JSON, Russian output, no-write behavior, budgets, or changing-evidence detection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-skillset-install-status`: Add measurable single-traversal-per-sample and mount-snapshot reuse requirements without weakening the existing two-sample observation contract.

## Impact

- `tools/install_skillset.py` observation orchestration and mount-boundary lookup.
- Root status tests with read/open/mount-call instrumentation and adversarial mutation fixtures.
- `skills-manifest.json` release-tool hash after implementation.
