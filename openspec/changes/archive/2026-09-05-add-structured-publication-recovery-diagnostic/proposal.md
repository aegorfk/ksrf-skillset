## Why

The three native coding publishers already distinguish several recovery situations in
carefully written Russian error text, but every one is exposed to automation only as
exit code `2`. A caller cannot safely distinguish an eligible repeat-and-compare
candidate from a filesystem state that requires administrator-only accounting and
quarantine. Parsing localized prose is unstable and can turn a serious integrity
incident into an unsafe retry.

The common publisher also has a double-fault precedence gap: while an
administrator-only publication-state error is propagating, a later descriptor-close
failure can replace it with the less restrictive finalization-uncertain route. Stable
machine codes must not expose that downgrade.

## What Changes

- Give every common `_PublicationRecoveryError` one of five closed internal codes and
  derive its recovery route from one fixed code-to-route map.
- Add the exact opt-in flag `--recovery-diagnostic-json` to
  `coding-audit-prepare`, `coding-audit-review-import`, and
  `coding-audit-finalize`.
- On a classified recovery error only, let the flag replace the ordinary stderr line
  with one compact, sorted-key, ASCII-safe JSON line. The JSON retains the complete
  existing Russian recovery message, including required filesystem coordinates, and
  adds closed routing and negative-authority fields.
- Preserve the existing human stderr byte-for-byte when the flag is absent. Preserve
  parser failures, ordinary validation/input errors, all successful stdout and
  artifacts, and the finalizer's code-`3` incomplete result.
- Enforce `administrator_only` over `repeat_then_compare_candidate` when concurrent
  recovery and close faults occur. Classification is carried by the error and is
  never inferred from its localized text, errno, cause, or exit code.
- Keep the diagnostic routing-only: it performs and authorizes no retry, cleanup,
  deletion, quarantine, downstream use, publication, legal approval, or filing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-practice-quality-exit-status`: define the five closed publication-recovery
  codes, their two derived routes, double-fault precedence, exact stderr JSON
  contract, and unchanged process/filesystem semantics.
- `ksrf-user-facing-cli`: expose the opt-in flag and its privacy, stdout-validity,
  recovery, installation-parity, and legal-authority boundaries in Russian.

## Impact

Implementation is limited to the existing judicial-meaning practice-quality builder,
common publisher and CLI error boundary, installed schema and guidance, focused tests,
and the normal release manifest. It adds no dependency, service, persistent recovery
receipt, filesystem permission, network call, database action, or automatic recovery
behavior. The JSON message may contain destination entry names and device/inode
coordinates already present in the human diagnostic; help must warn that it is an
administrator recovery record and not public-safe content.
