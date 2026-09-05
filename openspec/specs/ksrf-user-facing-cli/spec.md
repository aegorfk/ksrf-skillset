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

### Requirement: Native coding finalization is actionable in plain Russian

The clean-installed Russian CLI help and practice-quality guidance MUST expose a
copyable `quality coding-audit-finalize` command with required `--bundle`,
`--expected-manifest-sha256`, `--audit-import`,
`--expected-import-receipt-sha256`, and `--output-dir`, plus conditional
`--resolutions`. They MUST explain that the two expected digests are retained from
the successful prepare/import stdout outside the directories being checked, not
copied back from those directories during finalization.

Help MUST state that bundle, import, and new absent output are distinct siblings
under one private actual parent. It MUST name the four exact output files and show
the complete sequence prepare -> independent return -> native import -> resolve
reported differences if any -> native finalization. It MUST tell the user to omit
`--resolutions` when both imported maps are empty and require it when either map is
non-empty.

Help and installed guidance MUST state that a required resolution input is itself
private: a direct sibling under the same parent, owned by the effective user, mode
`0600`, single-link, and without any Darwin extended ACL. They MUST tell the user
to retain the successful finalization `receipt_sha256` from complete stdout outside
the finalization directory, and never recover that external anchor from the
self-digesting receipt being checked.

Guidance MUST publish the closed resolution-row shape and explain in ordinary
Russian that each row is pre-bound to the import receipt, candidate, entire ordered
field set, and primary/secondary hashes. It MUST explain the `primary`, `secondary`,
and `custom` choices; full bijection over both maps; pseudonymous reviewer label;
RFC 3339 review time; and exact declarations. It MUST state that a pseudonym and
declarations are not authentication, proof of authorship/independence/packet use, or
proof that a person performed the review.

#### Scenario: Custodian can complete the native review chain

- **WHEN** the user opens finalization help or installed practice-quality guidance
- **THEN** every required/conditional argument, external-anchor source, input
  relationship, resolution shape, and exact output filename is visible in Russian
- **AND** the user can distinguish no-difference finalization from the path that
  requires completed human resolution rows

### Requirement: Finalization help exposes bounded checks and exit meanings

The interface MUST explain that final coding is derived from exact imported values
and explicit choices rather than accepted whole; every final main and
`alternative_grounds` quote receives literal plus normalized presence checks against
the exact packet text; and generated adjudications and reliability use the same
captured state. It MUST also say that these checks do not validate proposition
truth, material facts, reasoning adequacy, legal correctness, norm temporal
applicability, or locator semantics. Locator review is declared only and successful
output always reports `quote_locator_verified=false`.

Help MUST define process code `2` as invalid contract/digest, unsafe filesystem
state, or I/O; code `3` as valid but incomplete/unresolved review with no closure
directory; and code `0` as atomic native technical closure only. It MUST say that
code `0` requires the generated reliability report to have exact
`complete=true`, but remains neither authenticated human review nor legal approval,
publication permission, freshness proof, or filing readiness.

The standalone `quality coding-reliability` workflow MUST remain discoverable as
the expert/manual compatibility path. Help MUST say plainly that its report alone
is not a native finalization receipt and cannot establish closure of Release15
non-audited differences or final packet-text revalidation.

#### Scenario: Automation can stop on three distinct outcomes

- **WHEN** the user reads `coding-audit-finalize --help`
- **THEN** Russian text distinguishes `0`, `2`, and `3`, whether a closure directory
  can be trusted, and the bounded meaning of a green receipt
- **AND** it does not instruct automation to infer human or legal authority from
  either reliability completion or finalization success

### Requirement: Finalization privacy and uncertainty recovery are discoverable

The finalizer help and installed guidance MUST inherit the Release15 private-output
rules in plain Russian: same effective-user-owned non-group/world-writable parent,
private sibling resolution input when present, new absent output sibling, `0700`
directory, `0600` files, and on macOS/Darwin no extended
ACL at all on every required parent/staging/final/file descriptor. They MUST reject
deny-only and non-inheriting ACEs, fail closed on ACL API/identity uncertainty, make
no Linux ACL-inspection claim, and never suggest that `chmod` alone proves ACL
absence.

Guidance MUST distinguish pre-`mkdir` validation failure from every post-`mkdir`
uncertainty. After staging starts, no file or directory is automatically unlinked;
known parent, directory, and file inode coordinates remain in value-free diagnostics
for administrator-only all-link accounting and quarantine. It MUST explain the
separate cleanup-, state-, durability-, and finalization-uncertain branches and that
an unaccounted inode/link set remains a sensitive unaccounted copy.

From the start of one-line success delivery through normal return, any write, flush,
pipe, or asynchronous interruption invalidates empty, partial, or apparently
complete stdout and preserves the directory. The user MUST stop, never retry the
same destination, repair the underlying fault, rerun unchanged inputs into a new
absent sibling, obtain a normal successful confirmation, and byte-compare the two
four-file directories before trusting the repeat receipt digest. The receipt and
diagnostics MUST be described as value-free: no packet text, quotes, substantive
selected values, pseudonyms, or absolute input paths.

#### Scenario: Interrupted success is not mistaken for closure

- **WHEN** staging/publication/confirmation fails or is interrupted after an output
  object may exist
- **THEN** help forbids destructive cleanup, same-destination retry, transfer, or
  parsing an apparently complete interrupted line
- **AND** it directs the user to the correct administrator quarantine or
  unchanged-input new-sibling repeat-and-byte-compare recovery

### Requirement: Native reliability inputs and compatibility limit are visible in Russian

Installed Russian help SHALL name the finalization receipt file and the separate
`--expected-finalization-receipt-sha256` input for `quality uncertainty-profile`,
`handoff create`, and complaint-cycle `result import`. It MUST say to take that
digest only from finalizer stdout followed by normal successful return and MUST
explain that the value inside the receipt is not a substitute. Handoff help MUST
show that the explicit value pairs with the one receipt `--quality-binding`; result
import help MUST explain that its independently supplied value is recorded in the
immutable import event and rechecked later.

Help MUST describe standalone `quality coding-reliability` as compatibility-only
diagnostics even when `complete=true`, without hiding or removing that command.

#### Scenario: User follows the complete downstream route

- **WHEN** the user opens the three relevant help surfaces
- **THEN** the Russian text supplies copyable argument names, identifies the
  out-of-band source, and distinguishes diagnostic reliability from native claim
  use

#### Scenario: User tries to copy the receipt member

- **WHEN** migration guidance explains a missing external digest
- **THEN** it prohibits reconstructing the expectation from the receipt and points
  to unchanged-input finalizer recovery

### Requirement: Native-binding failures stay actionable and value-free

Russian CLI errors SHALL identify the next technical action for missing, partial,
mismatched, or historical native bindings without repeating private input content or
absolute paths. Help MUST state that success proves only bounded technical lineage
and does not authenticate a person or establish legal correctness, current law,
publication permission, approval, or filing readiness.

#### Scenario: Imported handoff lacks an independent anchor

- **WHEN** complaint-cycle result import receives a handoff but no independent
  expected finalization receipt digest
- **THEN** the CLI stops with a concise Russian remediation and stores no new
  claim-eligible import event

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

### Requirement: Structured publication recovery is explicit, private, and install-portable

Russian help for the three installed native publisher commands MUST expose the exact
`--recovery-diagnostic-json` option on `quality coding-audit-prepare`,
`quality coding-audit-review-import`, and `quality coding-audit-finalize`. It SHALL
explain that the option changes
only classified publication-recovery stderr into one canonical JSON line; ordinary
errors and successful results are unchanged; stdout from a confirmation-delivery
failure remains invalid even if it appears complete; and the JSON can contain private
entry names and device/inode coordinates required for administrator recovery.

Help SHALL distinguish only `administrator_only` and
`repeat_then_compare_candidate`. It SHALL state that the latter is a candidate route,
not automatic permission: the user must preserve inputs/results, repair the external
fault, use a new absent sibling, obtain a normal successful repeat, and use the
applicable comparison procedure. It SHALL state that the diagnostic authenticates no
provenance or person, verifies no legal conclusion or current law, makes no artifact
public-safe, and grants no publication or filing authority.

#### Scenario: Each publisher documents the exact opt-in boundary

- **WHEN** the user invokes help for any of the three publisher commands
- **THEN** the Russian help names `--recovery-diagnostic-json`, stderr-only output,
  both closed routes, invalid confirmation stdout, the private-coordinate warning,
  and the fixed no-action and no-authority scope
- **AND** the option has no alias, abbreviation, environment default, output-file
  target, or effect on ordinary errors and successful paths

#### Scenario: Source and installed behavior agree

- **WHEN** equivalent deterministic recovery, ordinary-error, success, and incomplete
  cases run from the source launcher and a clean installed launcher
- **THEN** process codes and stdout are equal and both launchers emit byte-identical
  structured stderr or default human stderr as applicable
- **AND** the installed schema validates the structured line without installed tests,
  evals, OpenSpec, or maintainer-only files

#### Scenario: Parser faults do not masquerade as recovery diagnostics

- **WHEN** the new option is abbreviated, given a value, or used outside its three
  exact publisher routes
- **THEN** argparse returns code `2` before handler entry with its ordinary parser
  diagnostic
- **AND** no structured recovery JSON is emitted and no input or output path is opened
