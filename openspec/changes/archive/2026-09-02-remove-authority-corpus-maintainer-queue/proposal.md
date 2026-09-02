## Why

The installed constitutionalist corpus still exposes three `ТЗ/...` source paths that do not exist in a normal skill installation and a 31-item `next_extraction_wave` maintainer queue. The queue is not a set of verified author holdings: its only non-derived field is a plan for what a maintainer might extract later. Showing those plans beside source-status data risks false attribution and makes a historical maintenance backlog look like user guidance.

## What Changes

- Remove `local_source_hint` from the installed JSON and from future builder output while retaining source kind, label, coverage, public URL where available, and all work-level provenance.
- Remove `next_extraction_wave` from JSON schema version 2.0 and remove the matching table, table-of-contents entry, and stale wave framing from Markdown.
- Replace the stale Markdown addendum with a concise snapshot disclosure and clickable routes to the maintained verified and reference-only method-card files.
- Update the single root-only builder so a future rebuild cannot restore either maintainer-only surface.
- Extend the portable validator in both profiles so malformed schema, retired queue keys and local source hints fail closed.
- Preserve all 1,652 authority rows, 4,178 work links, aliases, routes, statuses, method cards, source counts, warnings, and non-promotion boundaries.
- Add fail-closed tests, update exact corpus hashes and manifest projections, validate, publish, install, and archive atomically.

## Capabilities

### Modified Capabilities

- `ksrf-runtime-payload-boundary`: installed prebuilt corpora are preserved semantically rather than frozen byte-for-byte and exclude maintainer-only coordinates and queues.

## Impact

- Frozen base: `5bbe4a06066e9ae20c2824d6d5b6ea5689dd4b47`.
- JSON baseline: 58,625 lines / 2,389,717 bytes / SHA-256 `285b854f9d53a0a1ce3fa38c59f9d9ddeed8bd199979a40be6fa95b4570b7015`.
- Markdown baseline: 1,890 lines / 339,751 bytes / SHA-256 `58405ad08d408147b72ee952b5e6422963e62da19c31c8b13a5c8d91a2375e98`.
- Semantic JSON projection excluding the two maintainer-only surfaces: SHA-256 `66c7076c4e01da409a1d4616f054ee2a02989e8102686cdd1c4b425892307676` under the recorded `jq -S` projection.
- The removed queue covers 31 authors and reports 276 linked works, all of which remain represented in `authorities` and the full registry.
- Runtime baseline: 15 packages / 234 files / 8,007,402 bytes / tree SHA-256 `14835bdef7236dd160264113a2494c4ab253ebd7ae5f9817910dcba4a36cbf27`.
- Final root builder: 1,340 lines / 83,791 bytes / SHA-256 `aef53ee039439a74c937a32189bdfaa3d31edc5fb98f822f2bc41994614f999f`.
- Final JSON: 58,282 lines / 2,375,837 bytes / SHA-256 `f0484b308a647c87d851c0e073d30ad24c8c6ace45c63283ef19ccc1fde955e3`.
- Final Markdown: 1,848 lines / 333,384 bytes / SHA-256 `176ac91b604fb031a975dbcfc286adf265862bab4e2e9352789ae5a7ea47f748`.
- Final runtime projection: 15 packages / 234 files / 8,014,038 bytes / tree SHA-256 `0067e91e9a2a038eac41474a3cc24adad43e8fc19aa8439cd0c814863b95c140`.
- The portable validator pins the complete canonical JSON semantic projection at SHA-256 `39c1110705ede4c9dd20f4e0fe62af145b71ec6685d5c62e2e4e8b19fd74d2e2`; coherent mutations cannot self-authorize by changing status, evidence and summary together.
- Semantic preservation is additionally pinned by canonical SHA-256 values for `authorities` (`1b86c629ae9274af5925bb7fb23c64270006240a5096ba47d852daab1915f7eb`), `summary` (`ca664591b1e71780f9daa285d538750944a85d07aff8d1ca3191152cfafaa09e`) and cleaned `sources` (`bed6a6023a48b3d02cd3b7bdedc3cd995f0042eb075b7d27d037df04dd4e2d8d`).
- No legal holding, source status, method promotion, filing gate, or authority count changes.
