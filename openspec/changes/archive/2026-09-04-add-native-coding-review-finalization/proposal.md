## Why

The native secondary-coding importer now verifies the exact blinded packet and
emits value-free maps of audited and non-audited differences, but the next step is
still split across unvalidated external notes and the legacy reliability command.
That command does not consume the import receipt, cannot prove that every reported
difference was resolved, and does not recheck an adjudicated
`alternative_grounds` quote against the exact packet text. A user can therefore
complete the documented manual steps without receiving one native, machine-checked
closure artifact.

## What Changes

- Add one custodian-side `quality coding-audit-finalize` command that consumes the
  exact native audit bundle, its separately retained parent-manifest SHA-256, the
  exact Release15 import directory, and the separately retained import-receipt
  SHA-256.
- Accept an optional completed human-resolution JSONL file only when either
  Release15 difference map is non-empty. Bind every resolution row in advance to
  the import receipt, candidate, complete differing-field set, and exact primary
  and secondary coding hashes.
- Require a full bijection over both difference maps. For every differing field the
  resolver chooses `primary`, `secondary`, or a schema-valid `custom` value and
  supplies a pseudonym, canonical `reviewed_at`, and explicit review declarations.
  These declarations and string labels are not identity authentication, authorship
  proof, or proof that a person performed the stated review.
- Deterministically rebuild the final coding population, generate the existing
  closed adjudication records for audited differences, and rederive the existing
  coding-reliability report from the exact native inputs. The final main quote and
  every final `alternative_grounds` quote must occur literally in the exact
  candidate packet text and also pass the existing normalized text validator.
- Keep locator review human-declared: the final receipt fixes
  `quote_locator_verified=false` even when a resolution row declares that locators
  were reviewed.
- Publish a new private sibling atomically with exactly
  `resolved-review-decisions.jsonl`, `adjudications.jsonl`,
  `coding-reliability.json`, and a self-digesting, value-free
  `coding-audit-finalization-receipt.json`.
- Bind the receipt to both out-of-band expectations, the exact bundle/import bytes,
  the optional resolution bytes or canonical absence, every output byte, both
  difference-map populations, and the final coding population without repeating
  text, quotes, substantive field values, pseudonyms, or absolute paths.
- Reuse the Release15 descriptor-held, bounded, no-follow input capture and
  no-replace publication/recovery contract, including private `0700`/`0600` modes,
  fsync durability, no destructive cleanup after staging begins, and fail-closed
  Darwin extended-ACL checks.
- Return code `2` for invalid contracts, digests, unsafe filesystem state, or I/O;
  code `3` for valid but incomplete/unresolved review; and code `0` only after full
  native technical closure and atomic confirmation. Code `0` is not legal approval,
  publication permission, filing readiness, or authenticated human review.
- Preserve the standalone expert/manual `quality coding-reliability` route as an
  explicit non-native compatibility path. A claim of native closure must use the
  finalization receipt rather than a hand-built decision/adjudication pair.

## Capabilities

### New Capabilities

- `ksrf-practice-quality-exit-status`: native, receipt-bound closure of imported
  coding review with complete difference resolution and exact-text quote checks.

### Modified Capabilities

- `ksrf-user-facing-cli`: discoverable Russian finalization workflow, exact exit
  meanings, recovery guidance, and honest human/legal boundaries.

## Impact

- Affected specs: `ksrf-practice-quality-exit-status`, `ksrf-user-facing-cli`.
- Expected runtime impact: `judicial_meaning.cli`,
  `judicial_meaning.practice_quality`, practice-quality schemas, installed Russian
  references, CLI inventory, and source/install regressions.
- The existing Release15 import format and expert/manual reliability interface
  remain readable and unchanged; only the new native closure claim requires the
  finalization receipt.
- No network, model, database, source refresh, reviewer authentication, legal
  approval, publication, deletion, or filing action is introduced.
