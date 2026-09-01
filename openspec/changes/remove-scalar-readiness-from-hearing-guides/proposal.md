# Change: Replace scalar hearing-guide readiness scores with independent checks

## Why

Three installed hearing-derived guides currently describe legal quality through `Автооценка`, automated case scoring, 0–2 dimensions, and summed ranges that purport to distinguish a workable constitutional complaint from an ordinary appeal. That presentation conflicts with the shipped QA contract: admissibility, evidence, release, and human-review gates are independent, and a high aggregate score cannot compensate for a failed or unknown gate.

## What changes

- Replace scalar/plus-minus labels in the three hearing guides with `Проверка по признакам` and explicit `подтверждено / предупреждение / недостаточно данных` outcomes.
- Replace both 0–2 sum rubrics with independent dimension checks that preserve their substantive questions but cannot be added into a legal-readiness result.
- Rename the automated-evaluation headings and package instructions without removing any argument pattern, constitutional justification, technique, evidence question, drafting formula, source boundary, or consumer route.
- Add regression tests for non-compensation, preserved criteria, payload presence, and backlinks.

## Impact

- Frozen base: `83bc6684de1c9f68b98f9d0737aaa5a40afa5947`.
- `hearing-derived-argument-patterns.md`: 275 lines / 40,019 bytes / SHA-256 `0b16fcc6957638796016a0cba17346960a3bb4fa142a2a533c759c425758d70d`; 15 labelled pattern checks, five package checks, and one six-dimension summed rubric.
- `hearing-constitutional-justifications.md`: 301 lines / 40,216 bytes / SHA-256 `99988ef131eefa1bb40064de97c802de2abbc0aa6558290422535924be0305c8`; 14 labelled checks and one five-dimension summed rubric.
- `hearing-argument-techniques.md`: 390 lines / 43,874 bytes / SHA-256 `72bcd3cb5ffd81d1e89e5891bb4640caaaaae421151337f5a08d9aaf1d9d2c54`; 11 labelled technique checks.
- Final projections from the frozen base:
  - `hearing-derived-argument-patterns.md`: 277 lines / 43,739 bytes / SHA-256 `c53d24bbd29bc69efb459f3b5febc51d0630cdf2a856b54c5500fc4cb81b663f`;
  - `hearing-constitutional-justifications.md`: 303 lines / 46,950 bytes / SHA-256 `c4fd63d1ce4efda5d32b43c6d048106406b1403665e5650aba0823ce5b0074f6`;
  - `hearing-argument-techniques.md`: 394 lines / 44,997 bytes / SHA-256 `2bbaf3e6955033f178337a4296ba3c9a809291625de10459243e7834959d2b53`;
  - runtime payload: 15 packages / 235 files / 8,063,765 bytes / tree SHA-256 `ceead1ed039f946776baac817fcf75d630174458f1d31a19834b36a019326bf4`;
  - release tools: 9 files / 197,557 bytes / tree SHA-256 `ef4d7395c10f436b13f4cd09ed450a65519a5dce78cd7f8a346b363c9ff80ddd`.

## Non-goals

- Do not remove or weaken any substantive criterion, adverse signal, evidence task, drafting formula, hearing-derived excerpt, pattern package, or skill backlink.
- Do not change the canonical hard gates, hypothesis comparison dimensions, verdicts, or human approval rules.
- Do not convert the guides into an executable adjudicator or claim that the new statuses establish admissibility, legal correctness, filing readiness, or expected outcome.
- Do not clean unrelated English terminology or other references in this change.
