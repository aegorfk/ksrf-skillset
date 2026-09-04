# ksrf-user-facing-cli Specification

## Purpose

Define stable Russian-language help for documented public KSRF runtime commands
without changing their executable, machine-facing, or non-help contracts.
## Requirements
### Requirement: Doctrine and authority runtime CLI help is Russian and actionable

The documented doctrine-research and authority-ledger KSRF runtime CLIs MUST render their root help, and every documented doctrine subcommand help route, in Russian. Help MUST retain executable command and option tokens, return exit code `0`, write no stderr, explain public arguments, and omit test-only or maintainer-only switches. Machine identifiers, JSON keys, provider names, and execution behavior MUST remain unchanged.

#### Scenario: Doctrine root help is Russian

- **WHEN** a user runs `doctrine_research.py --help` from a clean installed payload
- **THEN** stdout contains Russian usage, command, parameter, and built-in help descriptions; lists all five stable subcommand names; omits default English scaffolding and `--offline-fixtures`; stderr is empty; and exit code is `0`

#### Scenario: Doctrine subcommand help is Russian

- **WHEN** a user runs `route`, `plan`, `search`, `validate`, or `rerank` with `--help`
- **THEN** stdout explains the subcommand and each public option in Russian while preserving its exact command and option tokens, stderr is empty, and exit code is `0`

#### Scenario: Authority-ledger help is Russian

- **WHEN** a user runs `validate_authority_ledger.py --help` from a clean installed payload
- **THEN** stdout contains Russian usage, positional-path, parameter, public-URL, drafting-gate, and built-in help descriptions; omits default English scaffolding; stderr is empty; and exit code is `0`

#### Scenario: Hidden fixture route is preserved but unsupported publicly

- **WHEN** source QA inspects the doctrine parser after help suppression
- **THEN** `--offline-fixtures` remains a registered callable option for existing tests but does not appear in any public help output

#### Scenario: Machine contracts do not change

- **WHEN** the help-only release is compared with its base
- **THEN** subcommand names, public option strings, defaults, exit-code behavior, JSON fields, provider identifiers, and non-help execution paths remain unchanged

### Requirement: Remaining documented runtime CLI help uses Russian presentation

The installed KSRF user-facing CLI MUST preserve Russian help across
`judicial_meaning.py`, `ksrf.py`, `ksrf_setup_doctor.py`,
`ksrf_autocollect.py`, `ksrf_practice_analysis.py`, and
`validate_argument_research.py` runtime commands MUST render every reachable
public help route with Russian usage, section headings, built-in help text,
descriptions, and value placeholders. Help MUST preserve executable command,
alias, exact option, choice, and machine identifiers. Every `argparse` parser,
including nested subparsers, MUST reject abbreviated long options before
handler dispatch. Apart from that intentional rejection, non-help usage,
errors, defaults, exit codes, hidden options, JSON, and execution paths MUST
remain unchanged.

#### Scenario: Nested parser help is consistently Russian

- **WHEN** source QA recursively enumerates each nested parser route and invokes
  that route from a clean installed payload with `--help`
- **THEN** every invocation exits `0`, writes no stderr, contains Russian help
  scaffolding, and contains no default English `argparse` heading, built-in help
  sentence, or generated English value placeholder

#### Scenario: Wrapper and standalone help is consistently Russian

- **WHEN** a user invokes `ksrf_setup_doctor.py`, `ksrf_autocollect.py`, or
  `validate_argument_research.py` with `--help`
- **THEN** the command explains its purpose and public inputs in Russian while
  retaining its stable program label and exact option tokens

#### Scenario: Parser state is restored after help

- **WHEN** help is rendered from an in-process parser and the same parser is
  inspected or used afterward
- **THEN** action destinations, metavariables, choices, defaults, required
  flags, aliases, hidden-help state, exact-option policy, and parser behavior
  equal their pre-help values

#### Scenario: Non-help contracts remain exact except abbreviation diagnostics

- **WHEN** representative root, nested, missing-argument, invalid-choice, and
  standalone-validator failures are compared with the base release
- **THEN** stderr/stdout placement, exit codes, command names, and default
  metavariables remain byte-for-byte compatible for exact tokens, while every
  long-option prefix is rejected with code `2` before handler execution and its
  diagnostic MAY change from Python's former accepted or ambiguous-prefix text
  to unknown-argument text

#### Scenario: Hidden test routes remain hidden

- **WHEN** the judicial-meaning collection help is rendered
- **THEN** the existing fixture-directory option remains registered for source
  tests but is absent from public help and from the installed documentation

### Requirement: Practice-analysis arguments explain their user-visible behavior

Every public argument exposed by `ksrf_practice_analysis.py` MUST have a non-empty plain-Russian explanation across all reachable help routes. Help and route summaries MUST identify the role of file, folder, workspace, identifier, reviewer, date, selection, and export arguments; state meaningful defaults and omission behavior; describe attach, import, status, validation, and lint no more broadly than their handlers; preserve human-review, trusted-source, audit-only, and filing-readiness boundaries; preserve executable tokens; remain readable in terminals from 60 through 80 columns; and MUST NOT change parser or non-help behavior.

#### Scenario: Every installed argument has actionable Russian help

- **WHEN** source QA recursively inventories all 18 routes and invokes every
  route from a clean installed payload with `--help`
- **THEN** all 42 public argument actions across 11 leaf routes and 18 total
  help routes have non-empty Russian help, every invocation exits `0` without
  stderr, and no option is left as a bare token and metavar

#### Scenario: Paths and workspaces are distinguishable

- **WHEN** help displays a workspace, source workspace, input artifact, or
  output option
- **THEN** it explains what the path contains or where the result is stored,
  states that `--trusted-source-workspace` must match the previously attached
  cassation workspace, and does not imply trust or approval merely from
  supplying a path

#### Scenario: Omission behavior and defaults are visible

- **WHEN** `--claim-id`, `--argument-research`, `--skills-root`, `--output`,
  `--trusted-source-workspace`, `--corpus-cutoff`, or `--stage` is omitted
- **THEN** help states the resulting selection, discovery, storage, date, or
  default behavior that the runtime already implements

#### Scenario: Legal and evidence gates remain explicit

- **WHEN** help describes attaching, importing, reviewing, refreshing,
  validating practice material, `--official-check-ref`, or `--stage filing`
- **THEN** it distinguishes recorded data from a human-approved finding and does
  not claim filing readiness or trusted provenance without the existing gates;
  a supplied trusted-source path alone remains audit-only, an official-check
  reference records the reviewer's reference rather than proving an official
  source check, and the filing stage remains local validation rather than
  central host-attested filing authority

#### Scenario: Route summaries match handler scope

- **WHEN** help describes `run attach`, `result import`, or `lint`
- **THEN** attach is described as dispatching a request rather than attaching a
  result, import admits material stored only for audit rather than calling every
  result trusted, and lint promises only the structures, checksums, chains, and
  self-identifiers it actually checks

#### Scenario: Narrow terminal preserves atomic values

- **WHEN** every clean-installed help route is rendered at each width from
  `COLUMNS=60` through `COLUMNS=80`
- **THEN** every line fits the declared width and no path, option, identifier,
  date format, state, or other machine token is split at a hyphen

#### Scenario: Machine and non-help contracts remain exact

- **WHEN** the documented-help release is compared with its base
- **THEN** route count, commands, options, choices, defaults, destinations,
  handlers, program labels, usage, parser state, JSON, stdout/stderr, errors,
  exit codes, and non-help execution paths remain unchanged

### Requirement: Doctor help explains automation outcomes consistently

The public doctor help MUST present its process outcomes as one concise Russian
guide shared by `ksrf.py doctor` and `ksrf_setup_doctor.py`. Source-tree and
clean-installed help MUST be equivalent apart from executable paths, and the
guide MUST remain available under the supported Python runtimes.

#### Scenario: Shared source and installed help remain aligned

- **WHEN** both public launchers are invoked with `--help` from the source tree
  and a clean installation
- **THEN** each output contains the same `0`/`2`/`3` guide, exits `0`, and writes
  no stderr
- **AND** command names, options, defaults, JSON, non-help stdout/stderr, process
  behavior, probes, and filesystem or network effects remain unchanged

### Requirement: Practice quality help explains process outcomes

The clean-installed Russian help for `quality coding-reliability` and `quality prefiling-refresh` MUST explain that code `0` requires exact top-level Boolean `complete=true`, code `2` denotes invalid arguments/input/output I/O, and code `3` denotes a valid but incomplete or stale result. It MUST state that code `3` preserves full JSON on stdout and at an explicitly requested output path, and that code `0` does not approve or authorize filing.

#### Scenario: Automation contract is discoverable at both quality routes

- **WHEN** a user invokes either quality subcommand with `--help`
- **THEN** stdout contains the `0`/`2`/`3` guide in Russian
- **AND** help returns `0` with empty stderr
- **AND** the filing-authority boundary is explicit

### Requirement: Public-cache producer inputs are discoverable

The installed CLI MUST expose `cache refresh-plan --coverage-requirements`, `cache treatment quality-export --output`, provenance options for indexed treatment source text, and `cache treatment review --decision-reason`. Help MUST identify the non-empty coverage requirement shape, the complete content-bound purpose of quality-export, the RFC 3339 timestamp requirement, and the rejected-review reason requirement.

#### Scenario: User can find the complete prefiling producer path

- **WHEN** a user reads help for cache refresh planning, treatment quality export, ingest, or treatment review
- **THEN** the required options and Russian explanations identify how to create the official producer artifacts
- **AND** no help text suggests that a verified-only list or caller-authored treatment array is a valid prefiling input

### Requirement: Prefiling CLI requires exact filing-significant inputs

The installed `quality prefiling-refresh` parser MUST require refresh plan, treatment-quality-set, the existing public cache root, baseline/current corpus digests, subject evidence SHA, checked-through, filing cutoff, reviewer, reviewed-at, and one or more explicit claim IDs. Repeated claim IDs MUST express the complete claim population, while empty, duplicate, or noncanonical values fail as input errors. Help MUST explain that the cache is reopened read-only for live regeneration and that filing cutoff is a control point for the final preparation window, not a computed procedural deadline.

#### Scenario: Required claim identity is omitted

- **WHEN** a caller omits `--claim-id`
- **THEN** argument parsing returns code `2`
- **AND** no result artifact is created

#### Scenario: Bare treatment list is supplied

- **WHEN** `--treatments` points to a bare JSON array, partial object, or foreign failure envelope instead of the exact quality-export envelope
- **THEN** the CLI returns code `2` with a Russian diagnostic
- **AND** does not reinterpret the contents as an empty or complete treatment population

### Requirement: Source and clean-installed launchers agree

The source-tree and clean-installed public launchers MUST expose the same commands/options and MUST agree on process code, stdout/stderr, JSON result, explicit output artifact, and no-side-effect behavior for equivalent complete, incomplete, and invalid quality cases, apart from expected filesystem paths.

#### Scenario: End-to-end official treatment reaches prefiling

- **WHEN** both launchers register an official seed, ingest and index its full text with document/chain/query provenance, discover and content-bind a review, export the full treatment set, generate a coverage-bound refresh plan, and run prefiling
- **THEN** both launchers accept the same evidence contract and produce equivalent quality outcomes

### Requirement: Native coding-audit preparation is actionable in Russian help

The clean-installed Russian help MUST expose `quality coding-audit-prepare` with
required workspace, built-in codebook version, general-sample maximum,
exclusion-sample maximum, and new output-directory options. It MUST explain that the
command verifies the frozen plan, screening, approved primary coding, stored full
text, and independently selected built-in codebook; creates a new immutable `1.2`
audit-input bundle without network access; refuses an existing destination; requires
its existing parent to belong to the current effective user and prohibit
group/other-user writes, with those checks repeated immediately before rename and
during final verification; bounds the directory inventory before reading every
entry; preflights ZIP member/total sizes; writes with `allowZip64=false`; and does
not perform independent secondary review, return-file import, adjudication, legal
approval, or filing. On macOS, every parent recheck, the temporary directory before
file creation, each file before its first byte, and the bundle directory/files before
and after rename MUST additionally prove through file descriptors that no extended
ACL exists. Every ACE, including deny-only and non-inheriting entries, and every ACL
API or identity fault MUST fail closed. Help MUST make no Linux ACL-inspection claim;
it directs the user to choose a private parent without extended ACL or contact a
system administrator and does not promise that `chmod` alone is sufficient.

Successful help MUST distinguish the two separately retainable stdout values:
`independent_review_packet_sha256` anchors the ZIP transferred to the reviewer,
while `manifest_sha256` anchors the parent bundle for the later native import. Help
MUST distinguish a validation failure before temporary-directory `mkdir`, which can
return code `2` with empty stdout and no output object, from every failure after a
successful `mkdir`. After that point the publisher intentionally preserves every
possible temporary object, performs no automatic file unlink or directory removal,
and returns code `2` with empty stdout. Temporary-directory identity is captured
immediately after safe open and before `fchmod`; open failure reports it as unknown.
Created-file descriptors and device/inode identities remain held through failure
classification. An ACL failure after `mkdir` follows this same preserved emergency
route.

Help MUST explain that atomic no-replace rename itself, not successful helper return,
is the filesystem commit point. After a helper error, a destination owning the
captured temporary-directory inode is preserved as post-rename state uncertainty;
every other post-`mkdir` result is also preserved without destructive cleanup as
cleanup uncertainty, even if the former temporary name appears to match. Both
routes report the held parent identity, prior temporary name, known directory
identity or explicit unknown identity, and known created-file identities. They
require unchanged inputs, no retry or transfer, and the complete diagnostic forwarded
for emergency administrator lookup, accounting, and quarantine of every name and
hardlink of every created file, with no self-service command. An unfound directory
or inode, or any incomplete link set, remains an unaccounted sensitive copy.

Help MUST separately describe the rare parent-directory `fsync` failure after rename
when every other final state check succeeds: code `2` and empty stdout can accompany
a complete visible bundle. The user preserves but does not use it, recovers the
filesystem, reruns the same unchanged inputs into another absent sibling, and
byte-compares both outputs. Any other post-rename parent-ownership/permission,
destination-entry, inventory, directory/file mode, link-count, size, identity, ACL,
or byte failure MUST be described as state uncertainty: stop without retry or
transfer, preserve inputs, forward the whole diagnostic for emergency administrator
lookup/quarantine by the reported parent, published-directory, and created-file
device/inode identities plus prior entry name, account for every file name/hardlink,
and treat a missing inode or incomplete link set as an unaccounted sensitive copy.

Prepare help MUST also explain the two post-publication wrapper states. From the
start of one-line JSON delivery until normal command return, any error or interruption
after complete durable publication—including short/failed write, explicit flush
failure, and interruption after a complete successful flush—returns code `2`,
preserves the bundle, and makes empty, partial, or apparently complete stdout invalid.
The user stops without using or retrying the same destination, repairs stdout,
reruns the same unchanged inputs into a new absent sibling, obtains one full flushed
line followed by normal return, and byte-compares both bundles. Only that successful
repeat stdout MAY provide `manifest_sha256` and
`independent_review_packet_sha256`; the first bundle MUST NOT regenerate its own
out-of-band anchor. Any error or interruption after publication but before delivery
starts—including a retained created-file, published-directory, or held-parent
descriptor close and wrapper interruption after inner return or parent close—leaves
stdout empty, while code `2` does not prove bundle absence. Help MUST label this
finalization-uncertain without claiming confirmed durability and require the same
preserve-without-use/new-sibling repeat and comparison.

#### Scenario: User can prepare and later import first-party audit inputs

- **WHEN** a user invokes `quality coding-audit-prepare --help`
- **THEN** help returns code `0` with empty stderr and describes every required
  option, all generated bundle files, contract `1.2`, and both stdout digests in
  plain Russian
- **AND** it directs the user from the generated pending templates to a separately
  completed secondary JSONL, then to `quality coding-audit-review-import` with the
  retained `manifest_sha256` and expected secondary-coder label
- **AND** it identifies the resulting `audit-decisions.jsonl` as input to the
  existing coding-reliability route only after any required adjudication and
  disclosed manual content review

#### Scenario: Help does not overstate automation

- **WHEN** help describes generated review queues, templates, and the later importer
- **THEN** it states that the generated items are pending work aids rather than
  review evidence and that import checks declarations, structure, bindings, and
  literal plus normalized quote presence rather than substantive legal correctness
- **AND** it does not claim real human participation, corpus completeness, coding
  agreement, reviewer authentication, legal readiness, approval, or filing authority

#### Scenario: Existing manual producer route remains available

- **WHEN** an expert already has exact contract-specific screening and primary records
  or an unversioned legacy five-file bundle
- **THEN** `quality coding-audit-plan` and the manual `quality coding-reliability`
  route remain documented and executable with their existing machine-facing options
  and behavior
- **AND** that compatibility route is not represented as a native import receipt

### Requirement: Treatment contention is actionable in the installed CLI

Installed treatment-discover and treatment-review commands MUST report transaction-
level SQLite contention as a stable Russian error on stderr with exit code 2 and no
success JSON on stdout. The message/help MUST explain that this attempt recorded
nothing, performs no automatic retry, and may be explicitly repeated after the
other cache operation finishes. It MUST NOT claim that corpus construction before
the transaction boundary is immediate, or that a retry supplies legal approval.

#### Scenario: Cache is busy at the treatment transaction boundary

- **WHEN** another SQLite connection owns a conflicting reservation as treatment
  proposal or review begins its reserved transaction
- **THEN** the installed command returns code 2 with an actionable Russian error
- **AND** stdout contains no success record and no hidden retry occurs

#### Scenario: User reads treatment command help

- **WHEN** a user opens help for treatment discovery or review
- **THEN** the help states that busy treatment writes are not retried automatically
- **AND** it tells the user to repeat the command only after the other operation ends

### Requirement: Audit preparation help identifies the independent-review handoff

The clean-installed Russian help for `quality coding-audit-prepare` MUST state that
new preparation emits contract `1.2`; that the produced directory is the custodian
bundle containing primary answers; that only `independent-review-packet.zip` is
intended for the independent coder; and that the archive contains the selected full
texts, blank templates, neutral frozen-plan brief, built-in neutral codebook, and
current versioned instructions but no primary coding answers or hashes. It MUST
describe the blinding as limited to the first coder's answer and specific sampling
lane, without claiming that membership in the union sample is hidden; warn that the
court text itself reveals facts and outcome; and state that the full-text archive is
not automatically safe to publish. It MUST say that primary answers, raw query text,
search matches, and the lane label are absent only in open form, while `plan_sha256`
and content-bound candidate IDs remain opaque commitments susceptible to guessing
by a party that knows or can enumerate plan variants. It MUST also explain that
`--codebook-version` is required, that this release supports exactly `1.0`, and that
the primary value is checked only for equality.

Successful prepare JSON and guidance MUST name both separately retainable digests:
`independent_review_packet_sha256` MUST equal the parent manifest's digest of
`independent-review-packet.zip` and is communicated separately to the reviewer for
comparison before using the ZIP; `manifest_sha256` MUST equal the parent-manifest
self-digest and is retained separately by the custodian for
`quality coding-audit-review-import`. Guidance MUST NOT direct the user to recover
the expected manifest digest from the bundle at import time. Import help MUST state
that an externally anchored exact Release14 `1.1` packet remains accepted under its
immutable old guide, while the unversioned five-file form remains on the manual
compatibility path. It MUST state that when no separate Release14 manifest digest
survives, native import is unavailable and the user regenerates `1.2` from the
unchanged workspace or uses that manual path without a native receipt.

The current `1.2` embedded `REVIEW-INSTRUCTIONS.md` MUST remain independently
actionable for the second coder and, after describing the exact returned 20-field
JSONL, MUST accurately direct the custodian to the native importer with the
separately retained manifest digest and expected secondary-coder label. It MUST state
“пакет аудита” rather than the hybrid “audit-пакет”, gloss `reading_family` as
“семейство толкования”, and gloss `supports` as “поддерживает” and `adverse` as
“противоречит”, while preserving all exact machine JSON identifiers and enum values.
The updated guide bytes MUST be bound by the inner file digest and therefore the
deterministic ZIP and parent-manifest digests. Guidance MUST tell the custodian to
use both hashes emitted by that same new preparation, never patch the immutable ZIP
or reuse hashes from an earlier packet. It MUST state
only that import checks the declared completed structural contract and literal plus
normalized presence of returned quotes in the bound packet text. It MUST NOT call
those declarations proof of a real human review or call quote-presence checking a
semantic validation, and MUST NOT imply validation of `proposition`,
`material_facts`, `reasoning_to_outcome`, legal correctness, reviewer identity, or
independence.

The `1.2` guide and prepare help MUST instruct the custodian to choose and separately
communicate a pseudonymous expected coder label before ZIP transfer and avoid real
names. They MUST say that later import hashes the normalized label but cannot prove
when it was selected. Historical `1.1` guidance MUST be described separately: its
frozen instructions did not require this prospective step, so a returned label is
only checked for consistency and any real-name replacement must be newly returned by
the author rather than silently edited.

#### Scenario: User reads preparation help before transferring files

- **WHEN** a user invokes `quality coding-audit-prepare --help`
- **THEN** the help names the one archive to transfer and says not to send the
  parent directory to the second coder
- **AND** it names required `--codebook-version 1.0` as the custodian's independent
  selection of the built-in neutral codebook, not a value learned from primary coding
- **AND** it tells the custodian to retain both stdout digests, send only the ZIP
  digest separately to the reviewer, and preserve the manifest digest separately for
  later native import
- **AND** it tells the custodian to select a pseudonymous coder label before transfer
  while disclosing that runtime cannot verify this precommit
- **AND** it preserves the separate human-review, privacy, legal-approval, and
  filing gates

#### Scenario: Successful preparation exposes both handoff digests

- **WHEN** `quality coding-audit-prepare` successfully publishes a new `1.2`
  custodian bundle
- **THEN** its stdout JSON contains `manifest_sha256=<64 lowercase hex>` and
  `independent_review_packet_sha256=<64 lowercase hex>`
- **AND** those values respectively equal the parent manifest's self-digest and its
  file digest for `independent-review-packet.zip`
- **AND** stdout does not expose primary coding, primary hashes, first-coder
  identity, or sample-lane membership

#### Scenario: Embedded instructions are independently actionable through return

- **WHEN** the second coder opens the `1.2` `REVIEW-INSTRUCTIONS.md` without the
  parent custodian directory
- **THEN** the guide explains ZIP-digest comparison and the exact closed 20-field
  completion contract, including enums, nested alternative grounds, identity
  preservation, and strict UTF-8 JSONL return requirements
- **AND** the attached neutral brief supplies exactly one directional
  `hypothesis_under_test` and the neutral plan rules needed to apply the attached
  codebook, without search/match/lane or custodian-review metadata
- **AND** it directs the custodian to run `quality coding-audit-review-import` after
  return using the separately retained `manifest_sha256` and expected coder label
- **AND** it says that neither return nor import proves real human participation,
  reviewer identity, independence, semantic or legal correctness, agreement,
  adjudication, legal approval, publication permission, or filing authority
- **AND** its user-facing prose says “пакет аудита”, `reading_family` (“семейство
  толкования”), `supports` (“поддерживает”), and `adverse` (“противоречит”) without
  translating the exact JSON identifiers
- **AND** the guide member, ZIP, and parent manifest bind the updated immutable bytes,
  so the user retains the two hashes from this same preparation rather than reusing
  an earlier packet's anchors

### Requirement: Native coding import has a copyable Russian handoff command

Russian help and installed guidance SHALL show a copyable
`quality coding-audit-review-import` command with required `--bundle`,
`--expected-manifest-sha256`, `--expected-secondary-coder`,
`--secondary-coding`, and `--output-dir`. They MUST
explain that the expected digest is copied from the separately retained successful
`coding-audit-prepare` stdout, not rediscovered inside the bundle. They MUST identify
`audit-decisions.jsonl` as the compatible input for `quality coding-reliability` and
`coding-audit-review-import-receipt.json` as the bounded verification receipt.

New `coding-audit-prepare` guidance MUST identify contract `1.2`, accurately name
the native importer, and still show both separately retainable stdout digests. The
importer guidance MUST state that externally anchored `1.1` Release14 packets remain
accepted, while the legacy five-file form remains on the manual compatibility path.
For prospective `1.2`, it MUST tell the custodian to choose and separately
communicate a pseudonymous coder label before ZIP transfer, while explaining that
the receipt hashes the normalized value but fixes
`secondary_coder_label_precommit_verified=false`. For historical `1.1`, it MUST
explain that the frozen old guide did not require preselection and the argument only
checks the already-returned label for batch consistency. If no separately retained
Release14 manifest digest survives, guidance MUST forbid rediscovery from the bundle
and offer only regeneration of `1.2` from the unchanged source workspace or the
expert/manual route without a native receipt.

The guidance MUST explain that the command runs after the independent reviewer has
returned a separate completed JSONL file, never asks the reviewer to receive the
parent custodian directory, and does not modify the bundle or returned file. It MUST
state that the output must be a new absent sibling of the bundle under their same
actual parent, that the parent must belong to the current effective user and not
permit group or other-user writes, and that ownership and permissions are rechecked
immediately before rename and during final confirmation.

On macOS/Darwin, help and installed guidance MUST say plainly that the parent,
temporary directory, resulting directory, and every created file must have no
extended ACL at all in addition to modes `0700`/`0600`. They MUST say that
deny-only and non-inheriting ACEs are rejected too and that an ACL API failure fails
closed. They MUST NOT imply a Linux ACL check. They MUST direct an ordinary user to
choose a private parent without extended ACL or contact a system administrator and
MUST NOT promise that `chmod` alone removes or proves absence of ACL.

Guidance MUST distinguish failure before temporary-directory creation, which can
return code `2` with empty stdout and no output object, from every failure after a
successful `mkdir`. From that point until the atomic commit, the temporary
directory and any possible sensitive files are intentionally preserved, code `2`
has empty stdout, and no automatic file unlink or directory removal is attempted,
because a concurrent name replacement prevents portable atomic ownership proof.

Temporary-directory identity is captured immediately after safe open and before
`fchmod`; an open failure is reported with unknown directory identity. Each created
file descriptor and device/inode is retained through failure classification. The
atomic no-replace rename itself, not helper return, is the filesystem commit point.
If a helper error leaves the destination owning the captured temporary-directory
inode, guidance MUST classify the preserved directory as post-rename state
uncertainty. Every other post-`mkdir` result MUST also be preserved without
destructive cleanup and classified cleanup-uncertain, even if the former temporary
name appears to match.

Both uncertainty routes MUST produce code `2` with empty stdout and report the
held parent's device/inode, prior temporary name, known temporary-directory identity
or explicit unknown identity, and known created-file identities. They MUST stop
automation with unchanged inputs and no retry or transfer. The user MUST forward the
entire diagnostic to a system administrator because no self-service recovery command
exists. The administrator MUST locate the directory and every created inode, account
for and quarantine every name/hardlink of every file, and treat an unfound directory,
inode, or incomplete link set as an unaccounted sensitive copy.

Guidance MUST separately warn that a rare parent-directory `fsync` failure after
rename, only when all other final state checks succeed, returns code `2` with empty
stdout even though the complete output may already be visible at that path. The user
MUST preserve but not use it, recover the filesystem, rerun the same unchanged
inputs into another absent sibling, and byte-compare both exact two-file outputs
before trusting either.

Guidance MUST distinguish every other post-rename state failure: parent ownership or
permission drift, destination-entry move/replacement, or output inventory,
directory/file mode, file link-count, size, identity, or byte drift means the
user-facing path or entry may no longer represent what was published through the
held descriptor. It MUST direct automation to stop, preserve inputs unchanged, and
never retry or transfer the result automatically. The diagnostic reports parent and
published-directory `st_dev`/`st_ino`, the prior published entry name, and every
known created-file device/inode. This MUST be described as emergency
system-administrator recovery, not a self-service command: the user forwards the
entire diagnostic, the administrator locates the directory and each created inode,
accounts for every name/hardlink, and quarantines each located copy. A missing
directory or inode, or an incomplete link set, remains an unaccounted sensitive
copy.

Guidance MUST then distinguish post-publication confirmation delivery. From the
start of one-line success JSON delivery until normal command return, any error or
asynchronous interruption—including a short/failed write, explicit stdout flush
failure, or interruption after a complete successful flush—preserves the directory
and returns code `2`. Stdout may be empty, partial, or apparently complete; every
form is invalid and MUST NOT be parsed. The user MUST stop automation, avoid using
the first directory or retrying the same destination, repair stdout, rerun the same
unchanged inputs into a new absent sibling, obtain one fully written and flushed
success line followed by normal command return, and compare both directories
byte-for-byte. Only the successful repeat stdout after equality MAY supply the
receipt digest, both next-step flags, and difference maps.

Guidance MUST separately describe any error or asynchronous interruption after
publication but before confirmation delivery starts. This includes a retained-
created-file, published-directory, or held-parent descriptor close failure and a
wrapper interruption after the inner publisher returns or after parent close. No
stdout has been formed, so it MUST remain empty, while code `2` MUST NOT be read as
proof that the directory is absent. This finalization-uncertain diagnostic MUST NOT
itself claim confirmed durability. The found directory and inputs are preserved
unchanged but unused; recovery uses the same identical-input/new-sibling repeat,
successful stdout, and byte comparison.

Confirmed successful output uses a `0700` directory and `0600` files. On macOS its
privacy contract additionally requires confirmed absence of every extended ACL on
the parent, resulting directory, and files; mode bits alone are insufficient there.
The receipt/diagnostics deliberately contain no packet text, quote, untrusted field
value, or absolute input path.

#### Scenario: Custodian imports a returned file without manual wrapping

- **WHEN** the user opens help or the installed practice-quality guide
- **THEN** the documented command names every required argument and both exact
  output filenames
- **AND** the user is directed to adjudication for audited-field disagreements,
  separate manual content review for other substantive differences, or otherwise
  to the existing reliability gate
- **AND** code `0` is explained only as successful import/publication; automation
  parses both `adjudication_required` and
  `non_audited_content_review_required` and stops if either is `true`

#### Scenario: Help distinguishes validation before mkdir from preserved uncertainty

- **WHEN** the user reads about failures before the atomic rename
- **THEN** a validation failure before temporary-directory `mkdir` may return code
  `2`, empty stdout, and no output object
- **AND** every failure after successful `mkdir` preserves every possible object,
  performs no automatic file unlink or directory removal, and reports either
  cleanup uncertainty or post-rename state uncertainty
- **AND** the guidance requires unchanged inputs, no retry or transfer, the complete
  diagnostic for a system administrator, and quarantine or an explicitly
  unaccounted sensitive copy, as exercised by
  [`test_pre_rename_directory_fsync_failure_preserves_staging_for_quarantine`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)
  and
  [`test_staging_setup_open_and_fchmod_failures_preserve_quarantine_entry`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Help exposes no-destructive-cleanup race branches

- **WHEN** a created-file hardlink escapes or the temporary entry is concurrently
  replaced after `mkdir`
- **THEN** help says that portable atomic ownership cannot be proved and no guessed
  name, file, or directory is deleted
- **AND** the diagnostic retains known created-file identities so the administrator
  accounts for and quarantines every name/hardlink, as exercised by
  [`test_cleanup_detects_sensitive_hardlink_outside_staging`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_precommit_failure_never_attempts_destructive_unlink`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py), and
  [`test_cleanup_never_unlinks_replacement_for_escaped_created_inode`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Help preserves a destination reached by an ambiguous rename

- **WHEN** the rename helper may have crossed the filesystem commit point by moving
  the captured staging inode before reporting an error
- **THEN** guidance says to reconcile both names by inode and never delete a
  destination that owns the staging inode
- **AND** neither unproved name is deleted; the branch is state-uncertain if the
  destination owns the inode and cleanup-uncertain if neither name proves ownership

#### Scenario: Help discloses the macOS extended-ACL boundary

- **WHEN** a user reads prepare or import help on any platform
- **THEN** help says that macOS requires no extended ACL at all on the parent,
  temporary/final directory, and every created file, in addition to `0700`/`0600`
- **AND** deny-only and non-inheriting ACEs and ACL API/identity faults fail closed,
  while the text makes no Linux ACL-inspection claim
- **AND** it directs the user to a private parent without extended ACL or to a system
  administrator, without promising that `chmod` alone is sufficient, as exercised by
  [`test_prepare_and_import_help_disclose_darwin_acl_boundary`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_extended_acl_probe_is_fail_closed_and_recaptures_fd_identity`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_extended_acl_guard_is_a_noop_outside_darwin`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_darwin_acl_probe_rejects_mode_change_inside_system_call`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_darwin_acl_removal_during_probe_is_detected_by_ctime`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_darwin_inherited_parent_acl_is_rejected_before_output`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py), and
  [`test_darwin_acl_added_after_parent_precheck_is_caught_on_staging_fd`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Help requires all-link recovery after published link-count drift

- **WHEN** final verification observes an extra hardlink to a published output file
- **THEN** guidance says that publication is state-uncertain and reports the child
  device/inode without automatically deleting or transferring either copy
- **AND** the administrator must account for and quarantine every name/hardlink;
  any missing inode or incomplete link set remains an unaccounted sensitive copy,
  as exercised by
  [`test_post_rename_hardlink_requires_every_link_to_be_quarantined`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Help invalidates interrupted confirmation through normal return

- **WHEN** a published import errors or is interrupted after confirmation delivery
  starts but before normal command return, including after a complete successful flush
- **THEN** help says that empty, partial, or apparently complete stdout is invalid,
  while code `2` preserves rather than removes the first directory
- **AND** it forbids use or same-destination retry and requires identical inputs in a
  new absent sibling, a successful repeat line and normal return, byte comparison,
  and repeat-only receipt digest/flags/maps, matching
  [`test_post_publish_stdout_write_or_flush_failure_preserves_output`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_closed_stdout_pipe_keeps_classified_exit_code_two`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_confirmation_recovery_survives_neutralizer_interrupt`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py), and
  [`test_interrupt_after_full_confirmation_before_return_invalidates_stdout`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py)

#### Scenario: Help distinguishes every pre-delivery finalization interruption

- **WHEN** an error or interruption occurs after publication but before confirmation
  delivery starts, including descriptor close or wrapper interruption after inner return
- **THEN** help says stdout is empty and code `2` does not prove output absence, while
  avoiding any claim that this diagnostic alone confirms durability
- **AND** the directory is preserved without use and recovered through the same
  unchanged-input new-sibling repeat and byte comparison, matching
  [`test_parent_close_failure_after_publish_has_distinct_empty_stdout_route`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_published_file_or_directory_close_failure_blocks_confirmation`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_keyboard_interrupt_during_published_descriptor_close_is_classified`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_import_interrupt_after_inner_return_uses_publisher_state`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_review_import_cli.py),
  [`test_prepare_interrupt_after_inner_return_uses_publisher_state`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_audit_producer.py), and
  [`test_prepare_interrupt_after_parent_close_before_delivery_is_finalization`](../../../../../skills/ksrf-cassation-judicial-meaning/tests/test_native_coding_audit_producer.py)

### Requirement: Import guidance distinguishes validation from identity and authority

The interface SHALL say in plain Russian that the closed-record checks and literal
plus normalized quote-presence checks establish only that the supplied records fit
the verified packet text and structural contract. They do not validate the truth,
adequacy, meaning, or legal correctness of `proposition`, `material_facts`,
`reasoning_to_outcome`, or any other substantive coding judgment. One
operator-pinned normalized coder label across the batch, distinct from the primary
label of every selected record (not unrelated extra primary rows), MUST be described
as a necessary consistency check, not authentication of a person, proof of when the
label was selected, or proof of independent work. Help and guidance MUST expose
`expected_secondary_coder_label_sha256`,
`secondary_coder_label_differs_from_each_sampled_primary_label=true`, and fixed
`secondary_coder_label_precommit_verified=false`, never the label itself in the
receipt or successful stdout. Literal quote validation MUST use the narrow field
`returned_quote_literal_presence_verified=true`, not a name implying semantic or
complete text review.

The interface MUST identify `audited_field_differences` and
`non_audited_content_differences` as value-free maps from each affected
`candidate_id` to all and only its differing field names. It MUST explain that
Release15 has no native artifact or machine validator proving closure of the second
map's manual review. When that flag is true, guidance MUST require a separate
external record with at least candidate ID, reviewed fields, reviewer pseudonym,
`reviewed_at`, conclusion, receipt digest, and both coding digests, and MUST NOT call
that record a built-in receipt.

Guidance MUST explain that `audit-decisions.jsonl` stays in frozen candidate order,
while the receipt's collection-level `secondary_coding_sha256` is calculated after
sorting complete returned records by each record's canonical digest. This MUST NOT
be confused with the per-record `secondary_coding_sha256` nested in each decision.

The interface MUST preserve the privacy warning for quoted judicial material and
state that literal quote presence does not verify a locator, edition allowlist
membership does not verify temporal applicability, an internal self-digest does not
authenticate a receipt, and a green import receipt is not adjudication, legal
approval, publication permission, freshness of law/practice, or filing readiness. The expert/manual
`coding-audit-plan` and `coding-reliability` route SHALL remain documented as a
separate compatibility path, without presenting hand-built decisions as native
import receipts.

The interface MUST further state that downstream `coding-reliability` does not read
the packet or import receipt. It does not revalidate adjudicated
`alternative_grounds` quotes/locators against packet text or enforce the advisory
non-audited manual-review flag. If adjudication changes `alternative_grounds`, a
human MUST recheck the final nested quotes/locators against packet text and retain a
separate external record; `complete=true` is not proof of either manual review.
Guidance MUST define `final_resolved_value_sha256` as SHA-256 over the UTF-8 bytes,
without a trailing newline, of
`json.dumps(final_alternative_grounds, sort_keys=True, separators=(",", ":"),
ensure_ascii=False, allow_nan=False)`. The optional full-record
`final_resolved_coding_sha256` MUST use the same formula over the complete final
20-field coding record.

#### Scenario: Successful receipt is not overstated

- **WHEN** import succeeds with matching or differing secondary coding
- **THEN** stdout and guidance disclose the exact bounded checks and next action
- **AND** guidance sends audited-field disagreements to the existing adjudication
  format but sends other substantive-content differences to manual content review,
  because that closed adjudication format does not accept those other fields
- **AND** guidance discloses that the manual-content-review signal is advisory in
  this release because the existing reliability command does not consume the receipt
- **AND** it discloses the exact value-free field maps and downstream packet-text
  limitation for adjudicated `alternative_grounds`
- **AND** neither success nor coder-label difference is described as authenticated
  reviewer identity, proven independence, legal approval, or filing authority
