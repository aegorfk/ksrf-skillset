# Change: Separate shipped autocollect contract from aspirational roadmap

## Why

`ksrf-live-argument-patterns.md` is an installed methodology reference used by four skills, but its 127-line automation section mixes eight real or partial candidate outputs of the shipped `ksrf_autocollect.py` with two functions the collector does not implement. It overstates several candidates as completed legal analysis and is the only prose that names some output concepts. The section therefore cannot simply disappear: the exact shipped output contract and its limits must first move to `ksrf-tool-layer.md`.

## What changes

- Document the eight real/partial autocollect outputs under their exact CaseFile keys in `ksrf-tool-layer.md`, with candidate-only limits and explicit routes for the two unimplemented functions.
- Remove the roadmap TOC entry and `Функциональность для максимальной автоматизации` section from the argument-method guide only after that runtime contract exists.
- Rename the two surviving `Автоматический индикатор` labels to `Проверочный сигнал` without changing their substantive criteria.
- Replace the two downstream bullets that would otherwise point to the removed `конструктор требования` and `QA-карта` with the real, shipped checks in `ksrf-complaint-facts-demands` and `ksrf-complaint-qa`.
- Add one route from the argument-method guide to the exact local-collector contract.
- Preserve the guide's corpus boundary, argument patterns, structural templates, downstream skill routes, the collector and its output schema, and every other paragraph outside the approved projection.
- Add exact preservation and runtime-payload regression tests.

## Impact

- Frozen base: `0d4ac416f6471eccafd255eb20261b0f2c05e68d`.
- Source file before change: 550 lines / 58,199 bytes / SHA-256 `ec3365c9eda92f6accf56bb9d34891bd16c5075eb8d82e35eb777822ba15f52d`.
- Exact argument-guide projection: one TOC row, one 127-line roadmap, two label substitutions, two dead-route rewrites, and one route to the shipped collector contract; expected file projection is 424 lines / 52,749 bytes / SHA-256 `88676c07982a7b897a3ff93f89f0860083eb4ed3e9cff37e7db75802062805dd`.
- `ksrf-tool-layer.md` grows from 185 lines / 21,014 bytes to 205 lines / 26,710 bytes while the argument guide shrinks by 5,450 bytes; the truthful replacement adds 246 net runtime bytes.
- Final runtime manifest: 15 packages / 235 files / 8,052,188 bytes / tree SHA-256 `5f1162261f3956ad7cdf2d4d1b13f9b3cb3c8dfb4b43721e4130b12f7488d498`.

## Non-goals

- Do not exclude or delete `ksrf-live-argument-patterns.md`; its methodology remains actively routed.
- Do not remove or change `ksrf_autocollect.py`, any CaseFile key, or any shipped candidate output.
- Do not remove any legal pattern, test, structural template, source boundary, or downstream skill route; only the two routes made dead by the removal may be rewritten to their shipped checks.
- Do not claim that candidate extraction proves application, test choice, stable practice, admissibility, or review entitlement.
- Do not clean other future-function references or scalar scoring rubrics in this change.
