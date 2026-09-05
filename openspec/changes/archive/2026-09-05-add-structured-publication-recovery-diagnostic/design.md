## Context

`coding-audit-prepare`, `coding-audit-review-import`, and
`coding-audit-finalize` share `_publish_new_audit_bundle` plus a wrapper state machine.
The common code produces five semantically distinct `_PublicationRecoveryError`
states, but the exception currently carries only text. `main()` catches it as an
ordinary `OSError`, prints `Ошибка: {message}` to stderr, and returns `2`.

Two states require administrator-only handling: uncertain staging cleanup before the
atomic rename and uncertain publication location/integrity after it. Three states may
be candidates for the already documented unchanged-input/new-sibling/repeat-and-
compare procedure: confirmed-location durability failure, failure finalizing the
published command before confirmation output starts, and confirmation delivery
failure. Candidate is not authority: external fault recovery and the full original
stop rule are still prerequisites, and exit code `2` alone never permits a retry.

The Russian error text contains recovery evidence that cannot be reconstructed safely
later, especially destination/staging entry names and device/inode coordinates. A
structured mode must retain it while preventing control characters in hostile entry
names from creating extra log records.

## Goals / Non-Goals

**Goals:**

- Expose one exact, closed, schema-validated diagnostic for all five common
  publication-recovery states across all three publishers.
- Make the code-to-route relation unambiguous and preserve administrator-only
  precedence during double faults.
- Keep default human behavior and every non-recovery outcome byte-compatible.
- Preserve the existing human recovery evidence inside a single safely serialized
  JSON string while keeping all other fields fixed or closed.
- Remain install-portable, deterministic, side-effect-free at the rendering boundary,
  and explicit that the report is unauthenticated routing evidence only.

**Non-Goals:**

- Do not convert argparse, input, contract, ordinary I/O, or unclassified errors to
  JSON.
- Do not infer classification from Russian text, exception causes, errno, output
  directory inspection, or process status.
- Do not verify that a repeat is currently eligible, repair the external fault, run a
  comparator, repeat a publisher, select an output, or persist a recovery token.
- Do not remove or abbreviate filesystem coordinates from the existing message, and
  do not claim that the structured line is safe for public logs.
- Do not change artifact bytes, success confirmations, code-`3` results, comparison
  commands, downstream gates, legal review, publication authority, or filing control.

## Decisions

### 1. Cover five common publisher states under a publication-recovery name

The closed mapping is:

| `error_code` | `recovery_route` |
| --- | --- |
| `staging_cleanup_uncertain` | `administrator_only` |
| `publication_state_uncertain` | `administrator_only` |
| `publication_durability_uncertain` | `repeat_then_compare_candidate` |
| `publication_finalization_uncertain` | `repeat_then_compare_candidate` |
| `confirmation_delivery_uncertain` | `repeat_then_compare_candidate` |

Although the first state occurs before the atomic rename, it belongs to the same
publication transaction and exception type. Calling the artifact
`coding_audit_publication_recovery_diagnostic` avoids falsely describing every state
as post-publication and avoids leaving the most sensitive staging state
unstructured.

Each factory assigns only `error_code`. A single pure practice-quality function
validates the code and derives `recovery_route`; callers never supply both. The one
bare durability constructor becomes a named factory. Production source contains no
other direct construction path. No message parser or exception-chain classifier is
permitted.

### 2. Use one exact opt-in flag only on the three publishers

Each of the three parsers adds boolean `--recovery-diagnostic-json`, with no
environment variable, config default, alias, abbreviation, or global form. Parser
defaults carry the exact public command identity:

```text
coding-audit-prepare
coding-audit-review-import
coding-audit-finalize
```

`main()` branches only for `_PublicationRecoveryError` after parsing and only when the
flag is true. With no flag it retains the existing literal
`Ошибка: {str(exc)}\n`. Generic `OSError`, `ValueError`, contract/input failures and
argparse failures remain human-readable. Success code `0` and finalizer code `3`
never inspect or emit the recovery diagnostic and keep the same stdout, stderr, and
filesystem bytes with or without the flag.

### 3. Emit one closed canonical stderr object

The exact top-level fields are:

```text
schema_version, artifact_type, command, error_code, recovery_route,
stdout_disposition, message_ru, exit_code, scope
```

`schema_version` is `1.0`; `artifact_type` is
`coding_audit_publication_recovery_diagnostic`; `exit_code` is `2`.
`stdout_disposition` is derived from the code:

- `confirmation_delivery_uncertain` ->
  `empty_partial_or_apparent_complete_invalid`;
- every other code -> `empty_invalid`.

`message_ru` is exactly `str(exc)`, without the ordinary `Ошибка: ` prefix. It is
opaque human recovery evidence, not a classification input. Existing constructors
escape attacker-controlled entry names with ASCII JSON quoting and exclude cause
text. The outer serializer uses `json.dumps(..., ensure_ascii=True, sort_keys=True,
separators=(",", ":"), allow_nan=False) + "\n"`, so the complete stderr record is
ASCII, compact, deterministic, and one line even for hostile entry names.

`scope` has exactly these fixed fields:

```text
diagnostic_only=true
same_destination_retry_allowed=false
recovery_eligibility_verified=false
recovery_action_authorized=false
downstream_use_allowed=false
automatic_retry_performed=false
automatic_delete_performed=false
automatic_quarantine_performed=false
diagnostic_provenance_authenticated=false
publication_safe=false
legal_readiness=false
filing_authorized=false
```

The installed schema closes both object levels, binds every code to its only route,
binds the delivery code to its only stdout disposition, and rejects missing, extra,
or unknown fields. The current schema-family contract version remains `1.5`; this is
an additive definition with its own `x-contract-version` `1.0`.

### 4. Keep diagnostic delivery independent and side-effect-free

Structured output uses a dedicated stderr writer, not `_write_stdout_line`, because
confirmation-delivery tests intentionally break or replace the stdout writer. The
writer performs exactly one text write and one flush, detects a short write, and does
not retry, recurse, fall back to stdout, create a file, or invoke recovery work if
stderr itself fails.

Building and rendering the report uses only the exact parser command identity, stored
closed error code, and already captured `str(exc)`. It performs no path resolution,
stat/readlink, filesystem enumeration, file read/write, temporary creation, chmod/ACL,
rename, subprocess, network, database, retry, delete, quarantine, import,
finalization, comparison, or downstream action. It must not expose the traceback,
cause text, argv, cwd, pid, environment, packet contents, coding values, candidate
identifiers, or digests.

### 5. Make recovery precedence explicit before exposing codes

The publisher's `finally` block records any active `_PublicationRecoveryError` before
attempting final descriptor closes. It derives route priority from the same closed
map. Selection follows these rules:

1. an `administrator_only` error always wins over a
   `repeat_then_compare_candidate` error;
2. among equal routes, the existing semantic order remains publication-state,
   staging-cleanup, active classified error, then close-derived finalization error;
3. an already active selected error is allowed to continue rather than being raised
   again from itself;
4. raw close/bookkeeping failures retain existing behavior only when no classified
   recovery error has priority.

Thus a state-integrity failure plus descriptor-close failure remains
`publication_state_uncertain`/`administrator_only`. A close failure cannot downgrade
quarantine work to a repeat candidate.

### 6. Document privacy and authority boundaries

Russian help and installed guidance explain that JSON mode changes only the error
presentation, writes only to stderr, and may contain sensitive filesystem entry names
and device/inode coordinates. It must be retained privately and forwarded only to the
responsible administrator when the route is `administrator_only`.

`repeat_then_compare_candidate` still requires the original conditions, repaired
external fault, unchanged inputs, a new absent sibling, a normally completed repeat,
and the applicable comparison procedure. The JSON does not authenticate its own
origin, verify eligibility, authorize automatic retry or result use, establish legal
correctness or freshness, make an artifact public-safe, or authorize publication or
filing.

## Risks / Trade-offs

- Retaining `message_ru` makes the JSON useful for real administrator recovery but
  unsuitable for public telemetry. ASCII-safe serialization and explicit help reduce
  injection and accidental-publication risk; they do not anonymize the evidence.
- A dedicated flag adds one option to three established commands. Exact-option and
  source/install help tests prevent aliases or drift.
- A machine route can be mistaken for permission. The word `candidate`, fixed
  negative scope, and unchanged automation stop rule make the limitation structural.
- Correcting double-fault precedence changes only a previously unsafe edge case; all
  ordinary and same-route diagnostics remain byte-compatible.

## Verification Strategy

- Pure builder/schema tests cover exact keys, all five code/route/disposition pairs,
  unknown values, every missing/extra field, and fixed negative scope.
- CLI tests cover the exact flag on all three parsers; all five real fault classes;
  default human parity; generic-error exclusion; success `0` parity; finalizer `3`
  parity; partial/apparent stdout delivery; hostile entry names; and dedicated stderr
  delivery failure.
- A double-fault regression proves state uncertainty cannot be downgraded by close
  failure. Side-effect guards forbid filesystem reinspection and all automatic
  recovery actions during building/rendering.
- Source and clean-installed launchers must produce byte-identical structured stderr
  and identical stdout/process behavior for equivalent deterministic faults.
- Run focused publisher/schema/help/option tests, both supported Python suites, full
  source tests, strict OpenSpec/source/runtime validators, manifest freshness, and a
  clean external installation before publication.
