## ADDED Requirements

### Requirement: Publication recovery errors carry a closed non-text classification

The common native coding publisher SHALL classify every
`_PublicationRecoveryError` at construction with exactly one closed `error_code` and
SHALL derive, rather than accept, exactly one `recovery_route`. The complete mapping
SHALL be `staging_cleanup_uncertain` and `publication_state_uncertain` to
`administrator_only`, and `publication_durability_uncertain`,
`publication_finalization_uncertain`, and `confirmation_delivery_uncertain` to
`repeat_then_compare_candidate`. No classification SHALL be inferred from localized
message text, exception cause, errno, exit code, argv, or a new filesystem inspection.

#### Scenario: Staging and state uncertainty remain administrator-only

- **WHEN** cleanup of a created staging directory cannot be confirmed or the location,
  identity, integrity, or protection of a published result cannot be confirmed
- **THEN** the carried code is respectively `staging_cleanup_uncertain` or
  `publication_state_uncertain`
- **AND** the derived route is `administrator_only`
- **AND** code `2` alone does not authorize repeat, cleanup, deletion, or quarantine

#### Scenario: Only bounded confirmed-location failures are repeat candidates

- **WHEN** the exact classified failure is durability uncertainty with confirmed
  location, published-command finalization uncertainty before confirmation output, or
  confirmation delivery uncertainty
- **THEN** the carried code is respectively `publication_durability_uncertain`,
  `publication_finalization_uncertain`, or `confirmation_delivery_uncertain`
- **AND** the derived route is `repeat_then_compare_candidate`
- **AND** candidate status does not verify eligibility or authorize an automatic retry

#### Scenario: Administrator recovery wins a double fault

- **WHEN** publication state becomes administrator-only uncertain and a later
  descriptor close also fails while the first error is propagating
- **THEN** the final classified error remains the first administrator-only state error
- **AND** it cannot be replaced by a finalization repeat candidate

### Requirement: Opt-in structured recovery diagnostics preserve process semantics

The three installed native coding publisher commands MUST each accept exact boolean
`--recovery-diagnostic-json`: `quality coding-audit-prepare`,
`quality coding-audit-review-import`, and `quality coding-audit-finalize`. Only when such a command
raises a classified `_PublicationRecoveryError` and the flag is present, the runtime
SHALL replace the ordinary human stderr line with exactly one compact sorted-key ASCII
JSON line followed by one LF. It SHALL retain exit code `2` and the exact stdout and
filesystem state already produced by that failure branch.

The object SHALL have exactly `schema_version`, `artifact_type`, `command`,
`error_code`, `recovery_route`, `stdout_disposition`, `message_ru`, `exit_code`, and
`scope`. `schema_version` SHALL be `1.0`; `artifact_type` SHALL be
`coding_audit_publication_recovery_diagnostic`; `command` SHALL be one of the three
public command tokens; `exit_code` SHALL be `2`; and `message_ru` SHALL be exactly the
existing recovery message without the ordinary `Ошибка: ` prefix. The delivery code
SHALL use `empty_partial_or_apparent_complete_invalid`; every other code SHALL use
`empty_invalid`.

`scope` SHALL contain exactly `diagnostic_only=true` and the false fields
`same_destination_retry_allowed`, `recovery_eligibility_verified`,
`recovery_action_authorized`, `downstream_use_allowed`,
`automatic_retry_performed`, `automatic_delete_performed`,
`automatic_quarantine_performed`, `diagnostic_provenance_authenticated`,
`publication_safe`, `legal_readiness`, and `filing_authorized`.

#### Scenario: Every publisher identifies itself without changing the failure

- **WHEN** any of the three publishers encounters an equivalent classified recovery
  failure with `--recovery-diagnostic-json`
- **THEN** stderr is one schema-valid canonical line carrying that parser's fixed
  public command identity, closed code, derived route, disposition, and original
  recovery message
- **AND** the process remains code `2` with no new filesystem or stdout action

#### Scenario: Confirmation output remains invalid

- **WHEN** confirmation delivery fails after output transmission starts
- **THEN** the structured diagnostic says
  `stdout_disposition=empty_partial_or_apparent_complete_invalid`
- **AND** any empty, partial, or apparently complete stdout remains invalid and is not
  repaired, replaced, appended to, or parsed by the diagnostic renderer

#### Scenario: Non-delivery recovery has no confirmation stdout

- **WHEN** staging, publication state, durability, or command finalization becomes
  classified before confirmation delivery begins
- **THEN** the structured diagnostic says `stdout_disposition=empty_invalid`
- **AND** stdout remains empty

#### Scenario: Ordinary and successful behavior stays compatible

- **WHEN** the flag is absent, or a flagged invocation has an argparse, input,
  contract, ordinary I/O, success-`0`, or finalizer-incomplete-`3` outcome
- **THEN** existing stderr, stdout, process code, and filesystem artifacts remain
  byte-identical to the behavior without this feature
- **AND** no ordinary error is promoted to a publication-recovery diagnostic

#### Scenario: Structured rendering performs no recovery work

- **WHEN** the diagnostic object is built and delivered
- **THEN** it uses only the fixed parser identity, carried code, and already captured
  message; serializes with `ensure_ascii=true`, sorted keys, compact separators,
  `allow_nan=false`, and one LF; and performs one stderr write and one flush
- **AND** it performs no retry, stat or path lookup, file creation or mutation,
  cleanup, deletion, quarantine, comparison, subprocess, network, database, import,
  finalization, downstream use, publication, or filing action
- **AND** a stderr write/flush failure does not retry, recurse, or fall back to stdout
