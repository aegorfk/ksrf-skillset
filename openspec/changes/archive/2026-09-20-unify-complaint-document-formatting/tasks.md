## Implementation
- [x] Start from verified live main, sync globals and record matching baseline.
- [x] Write proposal/design/delta specs before runtime edits.
- [x] Add the reusable formatting standard and actual-copy naming rule.
- [x] Implement style-based renderer and typographic normalization.
- [x] Run focused regressions, XML/text preservation checks and visual DOCX/PDF smoke.
- [x] Run source/privacy/manifest/clean-room/OpenSpec checks and archive change.
- [x] Prepare atomic publication and baseline-checked global installation.

Publication completion requires a successful push, matching fresh live SHA, publication guard and verified global installation; record the resulting SHA in the release receipt.

Validation: 39 focused tests passed; source strict validation and clean-room installation/verification passed for 16 skills with no warnings. The final synthetic DOCX/PDF was checked visually on 1/1 page. Text checks passed and filing_ready remained false. No full-suite rerun was needed for this bounded formatting change.
