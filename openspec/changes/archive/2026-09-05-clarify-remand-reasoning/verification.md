# Verification scope

## Real-source review

The complete available 16-page original complaint was read. Critical scan pages
were checked visually. Its checksum is
`a371257896daf5bc812fe03b1de174516cfac8f1a1e1abcfaf21391757899c42`.
The existing public source card in `social-entitlement-boundaries.md` identifies
the external publication. No original, OCR, images, reconstructed complaint or
local source path is included in this release.

The observed inference on complaint pages 11-12 motivates a specific check of an
unchosen disposition. It is not declared false: the full official remand and
subsequent appellate act were not obtained. A six-page saved official final KSRF
act was reread, and the first-instance act was newly obtained from the official
court inventory and fully read. The later appellate text is expressly withheld
from publication in that inventory; no restricted extraction was attempted.

Only the available first-instance reasoning is established by that additional
source, not the remanding court's reasoning or completeness of the chain. The
historical outcome was already known. No claim about current housing law,
outcome-blind performance, before/after quality gain, or likely success follows.

## Independent method review

An independent agent read the complete complaint and checked critical scans,
then reviewed the exact new subsection and its social-method cross-reference.
No blocking issue was found. The review specifically checked that the instruction
neither attributes a party inference to the court nor erases express legal
conclusions merely because the disposition is a remand or refusal of transfer.

Reviewed hashes, unchanged after review:

- cross-instance reference:
  `9063ee7f1efb70e851ea1adc6d5d63c42a357be868d02cea524f72d0af1aa4c2`;
- social-entitlement reference:
  `25a34e6b4fdfdae9cd938ebc7268aa9d06bbcbbfce018cf9b302d52aefa90a57`.

This is a source/method review, not human legal approval or a model experiment.
No new synthetic case, Langfuse/DeepEval comparison, native RSI epoch, promotion
receipt, trust principal or filing action was created. Ordinary guarded Git
publication remains separate from native trusted promotion.

## Technical checks

- Both affected skills passed quick validation.
- Strict source validation: 15/15, zero errors and warnings.
- Clean-room install and repo-side offline verification: 15/15, zero errors and
  warnings; runtime fingerprint
  `0e129d2d1408260aea750cb2c3dd1f2bcfa26468b8d2338b416a079fccdc09fd`,
  259 runtime files, 10,175,596 bytes. Evals remain source-only.
- Full repository regression: 366 tests in 267.650 seconds, OK with two platform
  skips (364 passed). Both skips concern non-UTF-8 filenames rejected by macOS.
  No test or expected result was changed.
- OpenSpec strict all-items validation before archiving: 39 passed, zero failed;
  the named change also passed before implementation. The archive command merged
  the new requirement into the main spec; its generated blank final line was
  removed before the final whitespace check.

Commit, live remote verification and canonical installation are post-commit
release steps. Their exact SHA and results are recorded in the run handoff, not
claimed in advance by this pre-commit verification record.
