## Context

The public source is the seven-item list on the Court's hearing page. The files were recovered from archived original URLs; two additional files are publisher versions, not additional independent opinions. Archive capture timestamps are not document dates. The source checkout is dirty with unrelated work; publication uses a clean temporary canonical checkout.

## Goals / Non-Goals

Preserve precise attribution and recover reusable reasoning without reconstructing documents in the public repository. The dissertation receives a focused methodological review, not a claim that its entire bibliography or every page has been verified. Historical international-law submissions do not determine present admissibility.

## Decisions

- Keep per-file hashes, source URLs, archive timestamps, extraction coverage, comparison notes and locators locally.
- Compare publisher and Court versions without erasing redactions or inferring authors from PDF metadata.
- Separate arguments about who holds a right, who may apply, who receives relief and who implements it.
- Compare doctrinal additions against existing proportionality references before changing global skills.
- Use ordinary two-pass user methodology; keep evaluation machinery in source-only evaluation assets.
- Preserve a single majority outcome with exact scope, separate opinions, source-role uncertainty and no causal claim about an expert's influence.
- Publish only non-reconstructive methods and minimal public attribution. Archive inbox sources only after extraction and integration are complete.

## Validation

New regression tests cover source roles, archival attribution, public/private boundaries, reachable two-pass methods and synthetic cases without private inputs. Run strict skillset validation, relevant regressions, available full suite and OpenSpec validation. Publish one explicit allowlist commit and verify live main SHA. No model-quality improvement is inferred from these checks.

## Validation results

- Added twelve source-only synthetic scenarios and six regression tests.
- Strict validation passed for all fifteen skills, including offline self-containment and public-source safety.
- Full discovery executed 432 tests: two filesystem-dependent skips and one failure in a pinned entrypoint digest after the intentional two-line addition. The reviewed diff contained only the new reference route; that entrypoint's line count, byte count and digest were updated without relaxing the guard.
- The final targeted run, including the entire affected digest-guard module and both source-method suites, passed 21 tests. The complete discovery suite was not repeated after this test-expectation-only correction.
- OpenSpec validation passed; the canonical runtime and release payload were byte-identical. Ten source files were archived locally after integration, with hashes verified at their destinations.
- No LLM calibration run, effectiveness estimate or current-law change was made.
