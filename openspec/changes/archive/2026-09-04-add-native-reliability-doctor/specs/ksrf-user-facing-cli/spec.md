## ADDED Requirements

### Requirement: Native reliability doctor is actionable in Russian and install-portable

The source-tree and clean-installed `judicial_meaning.py` launchers MUST expose
the exact nested route `quality native-reliability doctor`. Its Russian help MUST
show `--coding-reliability` with metavar
`ФАЙЛ_НАДЁЖНОСТИ_КОДИРОВАНИЯ`,
`--coding-audit-finalization-receipt` with metavar
`ФАЙЛ_КВИТАНЦИИ_ФИНАЛИЗАЦИИ`, and
`--expected-finalization-receipt-sha256` with metavar
`СОХРАНЁННЫЙ_SHA256_ФИНАЛИЗАЦИИ`. Help MUST explain that all three are needed for
`valid`, while omission is accepted only to diagnose `incomplete`.

Help MUST explain the `0=valid`, `3=incomplete/mismatch`, and
`2=invalid/unreadable` mapping; deterministic JSON stdout; the absence of an
output file, mutation, automatic repair, network, and database access; and the
fact that standalone `quality coding-reliability` remains compatibility-only
diagnostics. It MUST direct the user to retain the expected digest only from
successful finalizer stdout, forbid reconstructing it from the receipt, and give
the unchanged-input/new-sibling/byte-compare recovery when the value is missing
or uncertain.

Help and the fixed report scope MUST say that `valid` proves only the bounded
technical relation. They MUST NOT claim authenticated reviewer identity,
independence, legal correctness, current law, publication permission, approval,
claim readiness, or filing authority; it MUST state that downstream consumers
repeat current-plan, trusted-origin, and other independent checks.

For equivalent inputs, source-tree and clean-installed runs from outside the
repository MUST agree byte-for-byte on report stdout, agree on empty stderr and
process code for handler outcomes, reject abbreviated long options, ignore an
ambient conflicting `PYTHONPATH`, and leave their input directories unchanged.
The installed payload MUST not require tests, evals, OpenSpec files, repository
root helpers, a new launcher, or a new dependency.

#### Scenario: Installed help gives a copyable complete command

- **WHEN** a user opens
  `judicial_meaning.py quality native-reliability doctor --help` from a clean
  installation
- **THEN** the Russian text shows the exact nested route, all three long options
  and Russian metavars, their distinct origins, and the `0`/`3`/`2` outcomes
- **AND** it explains that omitted members diagnose incompleteness rather than
  establish native status

#### Scenario: Help preserves the external-anchor boundary

- **WHEN** help or remediation covers a missing or uncertain expected digest
- **THEN** it forbids copying the receipt member as the expectation
- **AND** it directs the user to unchanged-input finalization in a new sibling
  directory followed by byte comparison

#### Scenario: Valid remains a bounded technical result

- **WHEN** help explains a `valid` doctor report
- **THEN** it says that downstream consumers still revalidate current-plan,
  trusted-origin, and independent claim-readiness gates
- **AND** it grants no authentication, legal review, publication, approval, or
  filing authority

#### Scenario: Clean installation is behaviorally identical

- **WHEN** equivalent complete, incomplete, mismatched, invalid, and unreadable
  cases run through source and clean-installed launchers outside the repository
- **THEN** each pair has byte-identical report stdout and the same stderr and exit
  code
- **AND** the installed command uses only files already admitted by the runtime
  payload contract
