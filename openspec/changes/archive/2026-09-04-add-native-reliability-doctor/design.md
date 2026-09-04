## Context

Release 17 defines native coding reliability as a verified relation among three
independent inputs: the unchanged closed `coding_reliability` v1.1 object, the
closed `coding_audit_finalization_receipt` object, and a lowercase SHA-256 retained
out of band from successful finalizer stdout. Its verifier recomputes the
reliability and receipt self-digests, the receipt-to-reliability file digest, and
the exact audit-plan and ordered-candidate equalities. Downstream uncertainty,
handoff, complaint import/state, and filing consumers additionally verify their
own current-plan or trusted-origin context and fail closed.

There is no small installed command that lets a user inspect only this relation.
The existing setup/profile doctor has a different capability contract and MUST
not absorb artifact validation. The new command therefore belongs below the
existing judicial-meaning `quality` surface and reuses the Release 17 relation
rather than defining a parallel notion of reliability.

The runtime is dependency-free and installed from the existing skill payload.
The portable launcher already sets `sys.dont_write_bytecode = True`; tests and
OpenSpec files are maintainer-only and are not installed.

## Goals / Non-Goals

**Goals:**

- Provide `judicial_meaning.py quality native-reliability doctor` as a local,
  read-only preflight for the exact Release 17 triple.
- Produce one closed, deterministic, value-free JSON report for every invocation
  that reaches the doctor handler.
- Distinguish a valid relation (`0`), an absent or mismatched relation (`3`), and
  invalid or unreadable input (`2`) without leaking input-derived values.
- Give fixed Russian remediation and preserve exact source/clean-install parity.
- Preserve all existing consumer-specific current-plan and authority gates.

**Non-Goals:**

- Do not add or infer `native=true` and do not change `coding_reliability` v1.1 or
  either Release 17 finalization artifact.
- Do not authenticate the expected digest's provenance, reviewer identity,
  authorship, independence, legal correctness, current law, approval,
  publication permission, or filing readiness.
- Do not repair, normalize, regenerate, import, attach, persist, or promote any
  input or doctor report.
- Do not add network discovery, database access, a new dependency, a new
  launcher, or a new installed service.
- Do not replace downstream verification or evaluate a consumer's current plan,
  trusted receipt, six-binding population, or claim readiness.

## Decisions

### 1. Use a nested quality route with three separately supplied inputs

The exact route is:

```text
judicial_meaning.py quality native-reliability doctor \
  --coding-reliability FILE \
  --coding-audit-finalization-receipt FILE \
  --expected-finalization-receipt-sha256 SAVED_SHA256
```

The three options are optional at parser level only so that omission can produce
the machine-readable `incomplete` state and exit `3`. Supplying an option without
its value, an unknown option, or another parser-level syntax fault remains the
standard argparse exit `2` before the handler and produces no doctor report.
There is no `--output`, stdin artifact mode, discovery mode, or implicit default
path.

Each supplied file is opened only for reading through a bounded regular-file
reader. The leaf MUST NOT be a symlink, directory, device, or FIFO, and each
input is capped at 64 MiB. The reliability input MUST be a strict UTF-8 JSON
object with unique keys at every depth, no `NaN` or infinity, and bytes exactly
equal to:

```text
_canonical_bytes(reliability_object) + b"\n"
```

Every file-type, identity-race, or size rejection at this boundary maps to the
corresponding closed `*_unreadable` reason and `status=unreadable`; paths, sizes,
and operating-system errors never enter the report. The reader uses nonblocking,
no-follow semantics where the platform exposes them and rechecks the opened
descriptor as a bounded regular file before reading.

Candidate membership and ordered difference-population checks use set indexes
and one ordered pass over the closed field set. Validation is linear in the
number of candidates and difference pairs (with a constant number of closed
fields), so the 64 MiB byte cap does not conceal a quadratic availability path.

Here `_canonical_bytes` means sorted keys, compact separators,
`ensure_ascii=false`, and `allow_nan=false`; the file therefore has exactly one
trailing LF. The receipt member `coding_reliability_file_sha256` is checked
against SHA-256 of those exact bytes. The receipt itself is a strict closed JSON
object; its `receipt_sha256` is recomputed as SHA-256 of canonical bytes of the
object with `receipt_sha256` removed, without adding a file LF. The expected
digest MUST be a separately supplied lowercase 64-hex string and MUST never be
read from the receipt.

Alternatives rejected:

- A flat `quality native-reliability-doctor` route would not preserve the
  requested namespace for later reliability diagnostics.
- Required argparse options would collapse an incomplete triple into an invalid
  invocation and make exit `3` unavailable.
- Accepting reformatted reliability JSON would stop checking the exact file
  bytes bound by the finalization receipt.

### 2. Share one structured evaluator with the Release 17 verifier

The implementation will extract or introduce one internal structured evaluator
for the closed reliability/receipt contracts and relation checks. The existing
`verify_native_coding_reliability(...)` remains a compatibility projection with
its existing public result and fail-closed exceptions. The doctor is a second,
value-free projection over the same booleans and bounded reason codes; it MUST
not parse exception text or duplicate the validation rules.

The exact relation checks are:

- closed reliability v1.1 structure, invariants, and self-digest, followed by its
  separate complete/non-stale native-readiness check;
- closed finalization-receipt contract and recomputed receipt self-digest;
- external expected digest equality with that self-digest;
- exact canonical reliability-file digest equality;
- receipt/reliability audit-plan digest equality; and
- exact ordered receipt candidate population equality with reliability
  `required_candidate_ids`.

No current plan is accepted by the doctor. Consequently `valid` confirms only
this portable relation. A handoff or other downstream consumer MUST still
revalidate its current plan, trusted origin, six bindings, and every independent
gate.

### 3. Use a five-state report and fixed classification precedence

The doctor first records missing inputs, then attempts to read and validate every
supplied input for which evaluation is possible. A supplied invalid input is not
hidden by a different omitted input. One top-level state is selected in this
fixed order:

1. `unreadable`: a supplied file cannot be opened or read as bytes;
2. `invalid`: read bytes are not strict UTF-8 JSON, a closed artifact structure
   or canonical file contract is invalid, canonical reliability bytes differ,
   or the supplied expected digest is not lowercase 64-hex;
3. `incomplete`: one or more of the three options is absent, or a structurally
   valid reliability v1.1 report has `complete=false`;
4. `mismatch`: all members are present and independently valid, but at least one
   self/external/file/plan/candidate relation fails;
5. `valid`: every required relation succeeds.

`valid` maps to exit `0`; `incomplete` and `mismatch` map to `3`; `invalid` and
`unreadable` map to `2`. Every handler outcome is emitted as a complete report on
stdout with empty stderr. A parser failure or failure while writing stdout cannot
promise a completed report and retains the existing top-level exit-`2` error
path.

### 4. Make the report closed, canonical, and value-free

The report has exactly these top-level members:

```text
schema_version, artifact_type, status, native_relation_valid,
reason_codes, checks, remediation, scope
```

`schema_version` is `1.0`; `artifact_type` is
`native_reliability_doctor_report`. `checks` contains exactly:

```text
coding_reliability_present
coding_reliability_readable
coding_reliability_contract_valid
coding_reliability_complete
finalization_receipt_present
finalization_receipt_readable
finalization_receipt_contract_valid
expected_receipt_sha256_present
expected_receipt_sha256_valid
receipt_self_digest_valid
external_receipt_digest_valid
coding_reliability_file_digest_valid
audit_plan_digest_valid
candidate_population_valid
```

Presence checks are Boolean. Other checks are Boolean when evaluated and `null`
when prerequisites make evaluation impossible. `scope` contains exactly fixed
Booleans `technical_lineage_only=true`,
`consumer_revalidation_required=true`,
`reviewer_identity_authenticated=false`, `legal_readiness=false`, and
`filing_authorized=false`.

Reason codes come only from the closed enum defined by the delta spec and are
ordered by the classification/check order above. Remediation entries contain
exactly `code` and `message_ru`, are deduplicated, and follow this fixed order:

| Code | Fixed Russian message |
|---|---|
| `check_local_read_access` | `Проверьте, что указанный локальный файл существует и доступен для чтения; команда не будет его изменять.` |
| `use_original_finalizer_files` | `Используйте исходные файлы успешной финализации и не исправляйте их JSON вручную.` |
| `provide_exact_triple` | `Передайте оба неизменённых файла финализации и отдельно сохранённый SHA-256 из её успешного стандартного вывода.` |
| `retain_external_digest` | `Берите ожидаемый SHA-256 только из стандартного вывода успешно завершившейся финализации и не восстанавливайте его из квитанции.` |
| `recover_in_new_sibling` | `Повторите финализацию из тех же неизменённых входов в новой соседней папке и побайтово сравните результат.` |

Unreadable reason codes select `check_local_read_access`; JSON,
canonical-byte, and artifact-contract invalidity select
`use_original_finalizer_files`; missing members and
`coding_reliability_incomplete` select `provide_exact_triple`; a missing or
invalid external expectation also selects `retain_external_digest` and
`recover_in_new_sibling`; and any relation mismatch selects
`recover_in_new_sibling`. Selected entries are deduplicated and serialized in
the fixed table order.

No report field may contain an input path, digest value, candidate identifier,
coding value, quotation, substantive label, pseudonym, attributable timestamp,
exception string, environment value, or complete input object. Report stdout is
exactly `_canonical_bytes(report) + b"\n"`, which fixes UTF-8 encoding, sorted
object keys, compact separators, unescaped Russian text, forbidden non-finite
numbers, and one trailing LF. There are no generated timestamps or host-dependent
fields.

### 5. Enforce application-level read-only execution

After argument parsing, the doctor may read only the two explicitly supplied
local files and write only its stdout report. It MUST NOT call any file mutation,
temporary-file, subprocess, socket/HTTP, database, import/attach, or repair path.
The existing launcher's bytecode suppression remains part of clean-install tests.
Tests compare input and directory snapshots and install spies around mutation,
network, database, and subprocess entry points.

### 6. Extend the existing installed schema additively

The practice-quality schema gains a closed
`native_reliability_doctor_report` definition and a top-level `oneOf` reference;
its contract metadata advances additively while all existing artifact branches
remain unchanged. The source and installed launchers validate and emit the same
report bytes and exit code from a working directory outside the repository, even
with an ambient conflicting `PYTHONPATH`.

No new payload rule is needed: the modified library, CLI, schema, `SKILL.md`, and
reference are already runtime classes in the exact manifest contract. Tests and
this OpenSpec change remain excluded from installation.

## Risks / Trade-offs

- **A user may treat `valid` as filing approval.** → Keep fixed negative scope
  fields in every report, repeat the boundary in Russian help, and require every
  downstream consumer to revalidate its own current plan and authority gates.
- **A matching expected digest may still be a self-declaration copied from the
  receipt.** → Accept it only through the separate CLI option, never infer it,
  and state that the doctor cannot authenticate how it was retained.
- **Refactoring the verifier could drift existing Release 17 behavior.** → Run
  the complete existing native-triple/downstream regression corpus and compare
  the legacy projection before adding the doctor projection.
- **Error details could leak private review content or host paths.** → Map all
  faults to closed codes and fixed messages before serialization; never serialize
  exceptions or values.
- **A nominally read-only command could create bytecode or incidental files.** →
  Retain `sys.dont_write_bytecode`, omit `--output`, spy on mutation APIs, and
  compare directory snapshots in source and clean-install tests.
- **Five statuses share only three exit codes.** → Keep exact status in the JSON
  while reserving `3` for structurally diagnosable non-valid relations and `2`
  for unusable inputs.

## Migration Plan

1. Add failing evaluator, report-schema, CLI, privacy, no-side-effect, and
   source/clean-install parity tests.
2. Implement the shared evaluator projection, closed report, and nested command
   without changing existing consumer interfaces.
3. Update installed Russian guidance and regenerate the normal release manifest.
4. Run focused and full suites, strict OpenSpec/schema/skill validation, then
   sync and archive the change only after implementation is complete.

Existing Release 16 output needs no rewrite when the user still has the exact two
finalizer files and separately retained successful stdout digest. If the external
digest is absent or uncertain, the doctor returns `incomplete` or `mismatch` and
the fixed new-sibling/byte-compare recovery; it never reconstructs the value from
the receipt. Rollback removes only the additive route/report branch/guidance;
Release 17 consumers and artifacts remain valid and unchanged.

## Open Questions

None. The command route, input distinction, canonical byte rules, status
precedence, report shape, authority boundary, and installation behavior are
closed by this change.
