## Why

`validate_argument_research.py` still reports `OK` for artifacts that omit the
entire findings or hypotheses collection, omit the portfolio role arrays, or
put objects, numbers, and strings into fields documented as text, arrays, or a
boolean. It also never checks a finding's `hypothesis_ids` against the declared
hypotheses. This makes the command look stronger than it is and lets malformed
research enter later workflows.

## What Changes

- Require the root `case_id`, `findings`, `hypotheses`, and `portfolio`
  containers instead of treating missing collections as valid empty values.
- Enforce the already published 12-field `ResearchFinding` and 14-field
  `ArgumentHypothesis` core shapes with explicit JSON types.
- Require the five portfolio fields proven by installed executable examples:
  approval, nullable principal, and the three hypothesis-role arrays.
- Validate both directions of declared reference existence: hypothesis to
  finding and finding to hypothesis, without inventing reciprocity rules.
- Require an approved portfolio to name a valid principal and a non-empty
  string reviewer; keep pending/revise/rejected portfolios principal-free.
- Replace the broad English success sentence with a Russian statement that
  limits `OK` to the checked core structure and references and explicitly
  withholds legal-readiness authority.
- Add source and clean-install regressions while preserving empty-research and
  extension-field compatibility.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ksrf-argument-research-validator`: reject false-green omissions and type
  mismatches in the executable core contract and narrow the success claim.

## Impact

- Runtime: `skills/ksrf-explore-arguments/scripts/validate_argument_research.py`.
- User documentation:
  `skills/ksrf-explore-arguments/references/artifact-contracts.md`.
- QA: root tests exercise direct validation plus source and clean-installed
  command behavior.
- No schema is inferred for hard-gate internals, comparison dimensions,
  critic findings, approval reasons, or the ECHR extension. No legal review,
  drafting, filing, publication, or promotion authority is added.
