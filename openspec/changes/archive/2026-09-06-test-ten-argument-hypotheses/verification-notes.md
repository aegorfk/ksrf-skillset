# Verification discoveries

The frozen experiment design, packets, prompts and model configuration remain unchanged. This note records tooling and regression findings, not post-hoc legal hypotheses or replacement answers.

## Inherited source-table test failures

The first full suite ran 548 tests and found one failure and one error in the existing source-credit tests. Both tests, their shared helper, the public tables and relevant method references match base commit `825f7e65c920bca5db1ebbc3deaba9577f7e5173` byte for byte. The earlier published table-numbering change added an ordinal cell, while two older tests still expected the applicant in the first cell.

Before changing these tests, the selected repair is to normalize only the leading numeric ordinal cell for their existing semantic checks. Preserve source URLs, attribution, meaningful column count and adjacency checks; do not renumber or edit source descriptions. No legal prompt, source packet or runtime methodology changes are involved.

## Probe receipt and score binding

Independent negative tests found that a review-stage receipt could retain a matching packet/output hash while carrying a wrong arm/prompt/model identity, and that injected diagnostic scores on a trial or failed call could bypass review-score binding. Actual generated receipts have not shown either corruption. A separate read-only gate reconstructs exact prompts and verifies current arm/model/tool/packet/output bindings; the observability bridge verifies frozen review scores. Preserve the executed runner snapshot and do not modify its bytes while the frozen batch runs. Apply fail-closed code/test corrections without regenerating legal answers or selecting different outcomes.

## Completed pilot and scoped verification

All 40 calls completed without failed calls or replacement answers. An exact-binding audit covered all 40 before the runner changed. The runner correction was applied only after the batch exited successfully; its 23 targeted tests passed. The observability bridge's 26 tests passed in the existing DeepEval 4.2.0 environment. No runtime method was expanded on these null findings.

The final DeepEval artifact covers all 40 calls using the retained executed runner snapshot. Fresh authenticated readback of 10 existing traces verifies exactly 40 unique generations, 192 numeric scores and 8 unknown scores with no duplicates. All numeric scores equal 2; H3 and H10 have unknown lawful/effective-relief scores for both arms in both orders. Mechanical locator diagnostics remain unknown for 20 answers and 200 score entries; this is not a grounding pass. All source-bearing artifacts remain private.

See `docs/argument-method-development-pilot.md` for the ten method-level results and limitations. Nine pairs are ties in both reviews; H2 is tie/baseline. The same-model reviews, one pair per hypothesis, eight overlapping original documents, known outcomes and ceiling scores do not establish equivalence, population effect or filing readiness. The separate `evaluate-five-argument-methods` human/outcome-blind change remains open.

The final full suite ran 554 tests in 319.048 seconds: 543 passed, 11 skipped in the primary environment. The separate 26-test DeepEval run passed without skips. Source validation and offline self-containment passed for all 15 skills, as did installation and offline runtime verification in an isolated temporary directory. Runtime content remains 279 files / 10,601,705 bytes with SHA-256 `611468656495f64d9f1d8c2924241d30c73e672342893105bfcb14520cb30d7c`. The new experiment tools stay maintainer-only; clean release HEAD/live SHA binds them, while the existing runtime/release-file manifest scope is unchanged.
