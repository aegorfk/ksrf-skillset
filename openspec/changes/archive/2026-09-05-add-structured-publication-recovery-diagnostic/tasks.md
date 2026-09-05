## 1. Contract tests

- [x] 1.1 Add failing builder and schema tests for the exact nine-field root, exact
  twelve-field scope, five closed codes, two derived routes, two derived stdout
  dispositions, fixed exit code, and rejection of unknown/missing/extra fields.
- [x] 1.2 Add failing parser and help tests for the exact opt-in
  `--recovery-diagnostic-json` flag on only prepare/import/finalize, fixed public
  command identities, Russian disclosure, no alias/default, and abbreviation refusal.
- [x] 1.3 Add failing integration tests for all five real recovery factories and all
  three publishers, including empty/partial/apparently complete invalid stdout,
  unchanged code `2`, default human parity, success `0` parity, and finalizer `3`
  parity.
- [x] 1.4 Add hostile tests for newline/escape/bidi entry names, secret cause text,
  exact one-line ASCII serialization, stderr short-write/flush faults, no stdout
  fallback, and zero rendering-time filesystem/process/network/database/recovery
  actions.
- [x] 1.5 Add a simultaneous publication-state-drift plus descriptor-close failure
  regression proving `administrator_only` wins and the first administrator recovery
  evidence is retained.

## 2. Closed recovery classification and rendering

- [x] 2.1 Add one pure practice-quality builder with the closed code-to-route and
  code-to-stdout-disposition maps, exact negative scope, opaque `message_ru`, and no
  independent route input.
- [x] 2.2 Make `_PublicationRecoveryError` carry only a validated closed code; route all
  five states through named factories, including the formerly bare durability error,
  without changing existing human messages.
- [x] 2.3 Add a dedicated compact ASCII-safe one-write/one-flush stderr renderer and
  branch to it only for classified errors under explicit opt-in; keep generic errors,
  parser errors, default human output, success output/artifacts, and code-`3` output
  unchanged.
- [x] 2.4 Preserve active classified recovery state through publisher cleanup and
  descriptor-close double faults, with fixed administrator-first and same-route
  precedence and no message/cause/errno inference.

## 3. Installed contract and guidance

- [x] 3.1 Add `coding_audit_publication_recovery_diagnostic` to the installed
  practice-quality schema with closed objects and exact code/route/disposition
  correlations.
- [x] 3.2 Update all three Russian help routes, installed `SKILL.md`,
  `references/practice-quality.md`, and README with the opt-in usage, private
  coordinate warning, two routes, invalid-stdout rule, no-action boundary, and legal,
  publication, and filing limits.
- [x] 3.3 Preserve source/clean-install parser, help, structured stderr, default error,
  success, and incomplete-result parity without installing tests, evals, OpenSpec, or
  source-only files.

## 4. Verification and release

- [x] 4.1 Run focused builder/schema/publisher/help/option regressions and all existing
  prepare/import/finalize/comparator/doctor/downstream tests.
- [x] 4.2 Run full source and supported-Python suites, strict schema/privacy/offline
  validators, and clean-install/exclusion/fingerprint checks.
- [x] 4.3 Obtain independent adversarial review of classification completeness,
  double-fault precedence, message injection/privacy, stdout/stderr semantics,
  side-effect boundaries, and authority wording; resolve every P1/P2.
- [x] 4.4 Validate and archive this OpenSpec change, refresh the runtime manifest only
  after tests, create one atomic commit, publish to main, verify remote SHA equality,
  and install only from the verified checkout.
