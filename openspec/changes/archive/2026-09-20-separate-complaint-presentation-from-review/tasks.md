## Preparation
- [x] Obtain clean live-main worktree, read publication contract and record global baseline.
- [x] Create proposal, design and delta specs before runtime edits.

## Implementation
- [x] Add presentation contract and align global skill instructions.
- [x] Render macrostructure and highlight missing data without generated service labels.
- [x] Export separate Markdown review while retaining source records and false authority.
- [x] Add synthetic regressions and check DOCX/PDF output.

## Verification and publication
- [x] Run focused and required regression/skill/privacy/clean-room/OpenSpec checks.
- [x] Synchronize specs, archive change and regenerate manifest against live base.
- [x] Prepare the exact atomic publication manifest and live-SHA verification commands.
- [x] Recheck the global baseline and prepare guarded installation from the published tree.

Publication is complete only after the atomic commit reaches live main, publication guard passes, and guarded global installation is verified. The final release receipt records these post-commit outcomes; preparation checkboxes do not assert them.

Validation: 14 focused tests passed. Full discovery ran 640 tests: 629 passed, 10 skipped, one pre-existing macOS PermissionError creating the invalid UTF-8 filename fixture; the same failure was reproduced on the unchanged base. Source strict validation and clean-room offline verification passed for all 16 skills with no warnings. Synthetic DOCX/PDF was visually reviewed on every page; adverse content remains visible, notes remain separate, placeholders are yellow and filing readiness stays false.
