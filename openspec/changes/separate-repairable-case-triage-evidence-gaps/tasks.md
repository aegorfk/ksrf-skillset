## 1. Frozen baseline

- [x] 1.1 Freeze published `main`, skill/eval hashes and the three stable forward-test outputs.
- [x] 1.2 Blind-grade the stable outputs before candidate editing and record the exact repair-routing failures.

## 2. Skill and eval contract

- [x] 2.1 Add the per-norm/per-stage evidence record and distinguish `FIX_FIRST` from `ABSTAIN_PENDING_RECORD`.
- [x] 2.2 Add one adversarial repairable-window eval and tighten the unavailable-record control without weakening existing controls.

## 3. Verification

- [x] 3.1 Run skill, JSON, strict OpenSpec and repository validations.
- [x] 3.2 Run an independent stable/candidate forward comparison and reject equal behavior as plateau.
- [x] 3.3 Complete independent architecture, test and final review on exact candidate bytes.

## 4. Candidate boundary

- [x] 4.1 Commit and push only the feature candidate branch after all checks pass.
- [ ] 4.2 Keep global installation, `main` publication and filing authority blocked pending a separate exact human decision.
