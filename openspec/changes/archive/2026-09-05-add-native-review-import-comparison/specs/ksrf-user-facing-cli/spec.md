## ADDED Requirements

### Requirement: Native review-import comparison is actionable in Russian and install-portable

The source-tree and clean-installed `judicial_meaning.py` launchers MUST expose the
exact nested route `quality native-reliability compare-review-imports`. Its Russian
help MUST show required `--bundle` with metavar `ПАПКА_ПАКЕТА_АУДИТА`, required
`--expected-manifest-sha256` with metavar
`СОХРАНЁННЫЙ_SHA256_МАНИФЕСТА`, required
`--uncertain-review-import-dir` with metavar
`СОМНИТЕЛЬНАЯ_ПАПКА_ИМПОРТА`, required `--repeated-review-import-dir` with metavar
`ПОВТОРНАЯ_ПАПКА_ИМПОРТА`, and required
`--expected-import-receipt-sha256` with metavar
`SHA256_УСПЕШНОГО_ПОВТОРА`.

Help MUST state that the exact seven-file bundle and both different complete two-file
import directories are direct siblings under one actual safe parent. It MUST state
that the manifest SHA-256 comes only from complete successful preparation stdout
followed by normal return and that the import receipt SHA-256 comes only from complete
successful repeated-import stdout followed by normal return. It MUST prohibit copying
either value from a manifest or receipt, using a digest from the uncertain invocation,
supplying loose files, or comparing a partial/staging directory.

Help MUST explain why both bundle inputs are required: two equal import directories
alone do not prove the established receipt-to-bundle contract. It MUST state that the
command reuses the existing bundle-bound import-consumer checks but does not re-read
the original returned secondary file, authenticate the coder label, rerun import, or
resolve review differences.

Help MUST explain `0=match`, `3=mismatch`, and `2=invalid/unreadable`; one
deterministic value-free JSON stdout report; exact raw equality of both import files;
full final recapture of the bundle, both imports, and installed codebook; and the
absence of output files, mutation, repair, deletion, quarantine, automatic repeat,
subprocess, network, or database access.

Help MUST make the eligibility boundary prominent: exit code `2` from the original
importer is not sufficient. The command is allowed only when the complete original
diagnostic expressly instructed unchanged-input import into a new sibling followed by
byte comparison. A diagnostic requiring staging cleanup, inode/hardlink accounting,
location/integrity/security investigation, ACL handling, or quarantine forbids this
command and remains administrator-only.

Help and fixed scope MUST explain that `match` cannot verify the historical error
class, either producer's normal return, or the provenance of either separately typed
digest; does not establish durability of the first import or reverify the workspace
or returned secondary file; and does not authenticate a reviewer or establish legal
correctness, current law, publication permission, approval, claim readiness, or filing
authority. It MUST direct later consumers to use the repeated import directory and its
separately retained receipt digest only after an eligible comparison, while still
revalidating the exact source bundle, expected manifest digest, current downstream
inputs, difference flags, and every independent gate.

For equivalent stable inputs, source-tree and clean-installed runs from outside the
repository MUST have byte-identical report stdout, equal empty handler stderr, and the
same process code for all four states. Both MUST reject abbreviated long options,
ignore an ambient conflicting `PYTHONPATH`, leave all input and parent snapshots
unchanged, suppress bytecode writes, and require no tests, evals, OpenSpec files,
repository helper, new launcher, or new dependency.

#### Scenario: Installed help gives a copyable complete command

- **WHEN** a user opens
  `judicial_meaning.py quality native-reliability compare-review-imports --help`
  from a clean installation
- **THEN** Russian help shows the exact nested route, all five required long options,
  Russian metavars, both external sources, and `0`/`3`/`2` outcomes
- **AND** it exposes no output, discovery, repair, or automatic-repeat option

#### Scenario: Equal directories without the source bundle are not enough

- **WHEN** a user wants to compare only the two import directories
- **THEN** help explains that the exact bundle and separately retained manifest digest
  are required for the established receipt-to-bundle checks
- **AND** it does not describe raw equality or receipt self-consistency as full native
  import validation

#### Scenario: Original diagnostic authorized repeat and compare

- **WHEN** the preserved original importer diagnostic expressly directs the user to
  repeat unchanged inputs into a new absent sibling and byte-compare results
- **THEN** help permits comparison only after the repeat returns normally with code
  `0` and its stdout receipt digest is retained separately
- **AND** it tells the user not to infer either external digest from an artifact

#### Scenario: Bare exit code two is insufficient

- **WHEN** the user knows only that the original importer exited `2`
- **THEN** help says comparison eligibility is unverified and does not authorize the
  command as recovery
- **AND** it requires the complete original diagnostic classification

#### Scenario: Administrator quarantine state forbids comparison

- **WHEN** the original diagnostic names staging, escaped or unaccounted inode/link,
  location, integrity, ACL/security, cleanup, or quarantine uncertainty
- **THEN** help tells the user to stop automation and preserve the administrator
  recovery route
- **AND** it does not suggest that safe-looking directory paths can replace all-link
  accounting

#### Scenario: Match remains bounded technical evidence

- **WHEN** help explains a `match` report
- **THEN** it repeats `original_recovery_eligibility_verified=false`, both
  normal-return/provenance limitations, and the remaining fixed negative scope
- **AND** it grants no authentication, legal review, publication, approval, claim, or
  filing authority

#### Scenario: Clean installation is behaviorally identical

- **WHEN** equivalent match, mismatch, invalid, and unreadable cases run through
  source and clean-installed launchers outside the repository
- **THEN** each pair has byte-identical report stdout and equal stderr/process code
- **AND** neither run changes an input, installed codebook, or surrounding directory
