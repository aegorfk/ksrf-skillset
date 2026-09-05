# Tasks
- [x] 1. Add autonomous bounded method cards and usage route
- [x] 2. Implement and test three-valued evidence-bound applicability
- [x] 3. Test temporal contamination denial and synthetic counterexamples
- [x] 4. Validate the atomic main release candidate (publication verified separately against live SHA)

Initial whole-suite run: 383 tests, 5 failures, 2 skips. Three installer failures
occurred before the new reference TOC was added; clean-room offline verification
then passed. The argument-patterns fingerprint changes with this release.
The case-triage fingerprint was already stale against unchanged live-base
6d522841a4f5e3fa1ecdcfc3747c7f26703c6ea9 (91 lines); its fixture was refreshed
after reading the current entrypoint. No case-triage behavior was changed.

Final whole-suite rerun: 383 tests passed, 2 skipped (754.407 s).
Validator unit suite: 112 passed. Installer rerun: 72 passed, 2 skipped.
Runtime routes/payload: 9 + 8 passed. Transfer runtime: 4 passed including
every required/defeating condition for all 12 methods. Strict source validator:
15/15; offline self-containment: passed; OpenSpec: 42/42; clean-room install
and offline verify: 15/15. Live remote equality and canonical installation
are post-commit checks, not inferred from these tests.
