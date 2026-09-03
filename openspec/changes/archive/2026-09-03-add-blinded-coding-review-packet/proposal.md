## Why

`quality coding-audit-prepare` now freezes the sample and primary coding safely,
but its directory is a custodian bundle: it contains the first coder's answers and
does not contain the full text that a second coder needs. Hand-selecting files or
sharing the whole directory either creates an identity gap or reveals the answer
that the review is meant to test.

## What Changes

- Add one deterministic `independent-review-packet.zip` to every newly produced
  native coding-audit bundle and version that parent format explicitly as
  `bundle_contract_version="1.1"`; keep legacy five-file manifests valid as the
  preceding contract.
- Put only the selected full texts, their content-bound identities, blank secondary
  templates, a Russian review guide, the exact neutral frozen-plan context needed
  for coding, the selected built-in neutral codebook, and a self-digesting inner
  manifest in that archive.
- Exclude primary answers and hashes, first-coder identity, screening matches and
  queries, sample-lane labels, internal source-row IDs, and adjudication data from
  the shareable archive.
- Require exact one-to-one parity among the frozen required candidate set, reviewer
  materials, pending templates, and inner-manifest population.
- Expose the exact ZIP SHA-256 in the producer's machine-readable stdout so the
  custodian can pin it and give the reviewer an independent expected digest.
- State precisely that the reviewer is blind only to primary coding, not to the
  judicial outcome visible in the source act, and that a packet containing full
  texts is not automatically safe for public release.
- Make the embedded guide state the complete closed 20-field secondary-coding
  contract, allowed enumerations, nested alternative-ground shape, and strict JSONL
  return format.
- Require the custodian to choose the only supported built-in neutral codebook with
  `--codebook-version 1.0`; primary records are checked for exact version equality
  but never supply the selected version or codebook bytes.
- Fail closed unless the frozen plan contains exactly one directional
  `hypothesis_under_test`, because `supports`/`adverse` need a fixed proposition and
  the current 20-field coding record has only one unqualified `relation`; project
  the accepted hypothesis and other reviewer-needed neutral plan fields into a
  closed `CODING-BRIEF.json` without search queries, screening matches, sampling
  metadata, `approved_by`, or `adverse_review`.
- Bind the exact codebook and neutral-brief bytes in both manifests, while preserving
  exact captured court text with separate normalized-store and packet-byte digests
  and rejecting unsafe control/format/surrogate characters.
- Keep the parent bundle atomic, immutable, offline, and exactly manifest-bound;
  make the ZIP bytes reproducible with fixed entry order and metadata.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-practice-quality-exit-status`: add a content-bound, primary-answer-blinded
  handoff artifact for the independent coder.
- `ksrf-user-facing-cli`: explain the new shareable archive and its privacy and
  human-review limits in installed Russian help.

## Impact

- Native audit projection in `practice_quality.py`.
- Deterministic ZIP production and manifest assembly in `cli.py`.
- Required `--codebook-version` CLI input and the installed neutral codebook
  `references/coding-audit-codebook-v1.md`.
- Backward-compatible, versioned audit artifact definitions in
  `practice-quality.v1.json`.
- Installed quality/artifact guidance and README benefit text.
- Source/install parity, determinism, blinding, schema, content identity, and
  atomic-output tests.
- No network access, automatic coding, agreement claim, adjudication, legal
  approval, publication authorization, or filing action is introduced.
