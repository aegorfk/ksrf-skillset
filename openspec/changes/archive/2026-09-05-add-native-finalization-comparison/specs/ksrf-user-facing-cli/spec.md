## ADDED Requirements

### Requirement: Native finalization comparison is actionable in Russian and install-portable

The source-tree and clean-installed `judicial_meaning.py` launchers MUST expose
the exact nested route `quality native-reliability compare-finalizations`. Its
Russian help MUST show required `--uncertain-finalization-dir` with metavar
`СОМНИТЕЛЬНАЯ_ПАПКА_ФИНАЛИЗАЦИИ`, required
`--repeated-finalization-dir` with metavar
`ПОВТОРНАЯ_ПАПКА_ФИНАЛИЗАЦИИ`, and required
`--expected-finalization-receipt-sha256` with metavar
`SHA256_УСПЕШНОГО_ПОВТОРА`.

Help MUST state that both directories are different complete four-file private
siblings under one actual safe parent and that the SHA-256 comes only from the
complete stdout of the repeated finalizer followed by normal code-`0` return. It
MUST prohibit copying that value from either receipt, using a digest from the
uncertain invocation, supplying loose files, or comparing a partial/staging
directory.

Help MUST explain `0=match`, `3=mismatch`, and `2=invalid/unreadable`; one
deterministic value-free JSON stdout report; exact raw equality of all four files;
the final recapture; and the absence of output files, mutation, repair, deletion,
quarantine, automatic repeat, subprocess, network, or database access.

Help MUST make the eligibility boundary prominent: exit code `2` from the original
finalizer is not sufficient. The command is allowed only when the complete original
diagnostic expressly instructed unchanged-input finalization into a new sibling
followed by byte comparison. A diagnostic requiring staging cleanup, inode/hardlink
accounting, location/security investigation, or quarantine forbids this command and
remains administrator-only.

Help and fixed scope MUST explain that `match` cannot verify the historical error
class, the repeat's normal return, or the provenance of the separately typed digest;
does not establish durability of the first directory; and does not authenticate a
reviewer or establish legal correctness, current law, publication permission,
approval, claim readiness, or filing authority. It MUST direct later consumers to
use the repeated directory and its separately retained digest only after the
eligible comparison, while still revalidating current-plan, trusted-origin, exact
bindings, and every independent gate.

For equivalent stable inputs, source-tree and clean-installed runs from outside the
repository MUST have byte-identical report stdout, equal empty handler stderr, and
the same process code for all four states. Both MUST reject abbreviated long
options, ignore an ambient conflicting `PYTHONPATH`, leave all input and parent
snapshots unchanged, suppress bytecode writes, and require no tests, evals,
OpenSpec files, repository helper, new launcher, or new dependency.

#### Scenario: Installed help gives a copyable complete command

- **WHEN** a user opens
  `judicial_meaning.py quality native-reliability compare-finalizations --help`
  from a clean installation
- **THEN** Russian help shows the exact nested route, all three required long
  options, Russian metavars, external repeat source, and `0`/`3`/`2` outcomes
- **AND** it exposes no output, discovery, repair, or automatic-repeat option

#### Scenario: Original diagnostic authorized repeat and compare

- **WHEN** the preserved original finalizer diagnostic expressly directs the user
  to repeat unchanged inputs into a new absent sibling and byte-compare results
- **THEN** help permits this comparison only after the repeat returns normally with
  code `0` and its stdout digest is retained separately
- **AND** it tells the user not to infer that digest from either receipt

#### Scenario: Bare exit code two is insufficient

- **WHEN** the user knows only that the original finalizer exited `2`
- **THEN** help says comparison eligibility is unverified and does not authorize the
  command as recovery
- **AND** it requires the complete original diagnostic classification

#### Scenario: Administrator quarantine state forbids comparison

- **WHEN** the original diagnostic names staging, escaped or unaccounted inode/link,
  location, integrity, ACL/security, cleanup, or quarantine uncertainty
- **THEN** help tells the user to stop automation and preserve the administrator
  recovery route
- **AND** it does not suggest that a safe-looking directory path can replace
  all-link accounting

#### Scenario: Match remains bounded technical evidence

- **WHEN** help explains a `match` report
- **THEN** it repeats `original_recovery_eligibility_verified=false`,
  `repeat_normal_return_verified=false`, and the remaining fixed negative scope
- **AND** it grants no authentication, legal review, publication, approval, claim,
  or filing authority

#### Scenario: Clean installation is behaviorally identical

- **WHEN** equivalent match, mismatch, invalid, and unreadable cases run through
  source and clean-installed launchers outside the repository
- **THEN** each pair has byte-identical report stdout and equal stderr/process code
- **AND** neither run changes an input or surrounding directory
