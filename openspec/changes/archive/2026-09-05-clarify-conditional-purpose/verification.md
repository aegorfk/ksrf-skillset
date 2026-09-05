# Verification

## Real-source scope

Reviewed the complete available 21-page published complaint through page-level OCR,
with visual checks of pages 1–3, 15–16 and 21. The lead passage is page 16, section
6.3.3; preceding and later arguments preserve objections to the basis and meaning
of the restriction. The original SHA-256 is
`90c327d161bedc629627db923bb996c6d9ce3bef9e781b3e4160d3198cccce9d`.
The freshly obtained publisher copy matches those bytes. The attachment inventory
is not a complete underlying court record.

The source supposes a possible purpose and separately attacks the chosen means.
It does not establish the purpose or its legitimacy, concede individual misconduct,
or supply a completed proportionality assessment. A public interview cited by the
submission is not the court's own reasoning. The source supplies a method signal,
not court authority or a substantive rule imported into another complaint.

A four-page publisher copy of the resulting refusal was read separately; its SHA-256
is `89fd6652d0e62e57e6cea4b7ba175fae3b44b8257b4f81e60545ebb8828e276f`.
Its last page contains only a page number. Fresh official-host retrieval was not
confirmed; the publisher's HTTP copy is not upgraded to a fresh official anchor.
The known refusal does not certify acceptance of the submission's technique.
No original, OCR, scan, full-text derivative or private source path is published here.

## Candidate and review

The narrower correction removes the pressure to certify a disputed purpose before
making a conditional reserve objection. The initial idea about accepting an adverse
individual fact was not supported by the investigated sources and was not added.

An independent reviewer checked compatibility with the purpose workbook and
balancing QA, finding no blocking issue in these exact bytes:

- reference: `d99c9a92578e93d2b61a49e9c8749419912405dbe2a50c6fedb5ce32d9df9554`;
- README: `26d4aeb1141ed1f4a3b1336b7b2475c3539036e10d486c5e3e22044b50ba98cb`.

This is source review and static editorial review with a known outcome, not a
blind run, a model comparison, human approval or proof of improved generation.
No new synthetic case, model run, schema or gate was created. One existing exact-byte
snapshot is updated to the independently reviewed reference; assertions and the
other frozen hashes remain unchanged. This is not a legal-outcome expectation.

## Release checks

- Strict source validation: 15/15, zero errors and warnings.
- Skill metadata quick validation: passed.
- Strict OpenSpec validation before archive: 39/39 items.
- Separate-target installation: passed; canonical global skills unchanged at this stage.
- Separate-target offline verification: 15/15, zero errors and warnings.
- Initial full suite: 366 tests in 278.922 seconds, one exact-byte snapshot failure,
  two platform skips. The old snapshot was independently checked against live base.
- Targeted rerun: 10/10 passed; independent review confirmed that only the intended
  hash literal changed, with no assertion or other snapshot weakened.
  Test file SHA: `f63e4f53369934b926009304c771c6b4f9468717410576d65e416d91a0af7d64`.
- Final full suite: 366 tests in 283.304 seconds, 364 passed, two platform skips
  because the filesystem rejects non-UTF-8 filenames. No failures.
- OpenSpec archive completed; the resulting main specification passed strict validation.

After validation and archive, the manifest must be regenerated from live base
`4b9b62cc9e75e1dfb84013deccdc177508792af3`. Commit/push/live-SHA verification and
global install/verify-current remain required post-commit actions; their actual
results are recorded separately after execution, never asserted prospectively.
