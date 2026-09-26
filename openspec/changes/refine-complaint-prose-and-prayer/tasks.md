## Implementation
- [x] Verify a clean worktree at current origin/main and record the bounded change.
- [x] Write proposal, design and delta requirements before runtime edits.
- [x] Align affirmative prose, author-selected legal basis and prayer structure across four skills.
- [x] Implement the prayer layout and body typography for authorities without changing legal content or bindings.
- [x] Add and run meaningful synthetic presentation regressions.
- [x] Run manifest, strict source, offline/self-contained and OpenSpec checks; record any pre-existing failures.
- [x] Hand off the uncommitted change for parent review and publication; do not install unpublished global skills.

Final targeted validation: 23 tests passed across document formatting (5), complaint presentation (9), working drafts (8) and the reviewed-runtime snapshot check (1). This includes a legacy standalone `ПРОШУ` without a colon, preserved without a duplicate. Synthetic DOCX/PDF smoke passed with matching text, 1/1 rendered page and no visual findings; the page was visually inspected. OpenSpec validation passed 75/75 items; offline self-containment and strict source validation passed for 16 skills with no errors or warnings. The manifest was regenerated against base `a100539eafc71a522e3e951e39e487331722db58` (311 runtime files; tree SHA-256 `ae57693c2f8d436256f01a2a5ac113fd6510a0360ddda09a8329c302aada5fd9`).

Full root unit discovery ran 653 tests with 4 failures and 11 skips before the final legacy-marker test. Three failures were independently reproduced using exact `origin/main` source bytes: the QA eval count expects cases through 45 although 46/47 are present; its frozen SHA-256 is stale; and the facts/demands skill snapshot expects 83 lines although the baseline has 84. The fourth was the newly changed rights-builder skill's frozen snapshot. After review, the two changed skill snapshots were updated and their exact-digest test passed. The two unrelated baseline QA-eval failures remain; the full suite was not rerun. No broad green-suite claim is made.

No commit, push, global installation or manual clean-room installation is part of this implementation handoff. Publication and installation remain with the parent release workflow.

Parent review accepted the bounded source/runtime diff and the refreshed exact-byte snapshots. A manual clean-room installation into a separate target passed. Before global installation, all 16 installed skills were compared to the published base manifest and matched; no unrelated global edits would be overwritten. Publication remains a separate atomic commit, live-SHA verification and installation step, recorded in the task's delivery report.
