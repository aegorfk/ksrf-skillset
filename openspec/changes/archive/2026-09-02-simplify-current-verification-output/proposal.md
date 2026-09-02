## Why

The public `./install.sh --verify-current` command currently exposes validator
implementation labels such as `runtime`, `evals: not_checked`,
`public-source safety`, and `source/release QA`. Those labels are useful in the
maintainer report but confusing in the user-facing installation flow,
especially because source-only evals are intentionally absent from the
installed skillset.

## What Changes

- Render the public current-release result from the structured validator report
  in concise Russian rather than forwarding the maintainer renderer.
- Explain `current`, `different`, `unknown`, and validation-failure outcomes in
  user terms while retaining package counts, bounded readable findings, and
  the content digest.
- Use one public findings renderer for offline and online verification: escape
  display controls, omit internal finding codes, and disclose truncation after
  the first 50 findings.
- Replace public wrapper errors containing `repo-side`, lifecycle phase names,
  validator internals, or Python exception classes with fixed Russian guidance
  while preserving local-failure code `1` and internal-failure code `2`.
- Keep validator data, network behavior, comparison logic, exit codes, and the
  direct maintainer CLI unchanged.
- Keep explicit boundaries: equality does not prove installation provenance,
  legal-source freshness, publication authority, or filing readiness.
- Add regression tests and align README guidance.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-skillset-install-status`: public current-release verification now has a
  dedicated plain-Russian human renderer.

## Impact

The change affects `tools/install_skillset.py`, installer tests, README
guidance, the release manifest, and the existing installation-status
specification. It does not change the installed runtime payload, validator
schema, comparison algorithm, network requests, or exit codes.
