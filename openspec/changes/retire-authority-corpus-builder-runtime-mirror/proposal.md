## Why

The installed `ksrf-argument-patterns` package contains an 88,026-byte copy of `build_constitutionalist_authority_corpus.py`. The same bytes already have a canonical owner under root `tools/`, while the installed copy cannot reproduce the corpus from a normal skill installation: it requires a Blokhin source, two external PDF indexes, and a local Zakon.ru discovery export that are not shipped. Users should receive the prebuilt corpus and the method for using it, not a duplicate maintainer generator with unavailable inputs.

## What Changes

- Remove `skills/ksrf-argument-patterns/scripts/build_constitutionalist_authority_corpus.py` from the tracked skill and user payload.
- Keep `tools/build_constitutionalist_authority_corpus.py` as the single maintainer owner, content-identical at the frozen SHA, executable as a root tool, and covered by the release manifest.
- Reclassify the former skill path as an exact root-only duplicate identity so reverse sync ignores a stale global copy, source/runtime validation rejects its return, and the next exact installation removes it from the global runtime.
- Replace the user-facing command backlink with a truthful route to the already installed corpus and its source-status boundaries.
- Preserve `constitutionalist-authority-corpus.json` and `constitutionalist-authority-corpus.md` byte-for-byte.
- Update publication documentation, exact ownership tests, manifest projections, and clean-room validation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-runtime-payload-boundary`: the corpus builder becomes root-only maintainer tooling; the prebuilt corpus remains installed.

## Impact

- Frozen base: `ae1f66cdc61a61cad5a7e90474b5ac02b908a330`.
- Duplicate and root owner baseline: each 1,382 lines / 88,026 bytes / SHA-256 `b1c393460420cc1c3382720d60188dbe4e52f9c72a78d87457f833682f67c33f`; they are byte-identical.
- Frozen JSON corpus: 58,625 lines / 2,389,717 bytes / SHA-256 `285b854f9d53a0a1ce3fa38c59f9d9ddeed8bd199979a40be6fa95b4570b7015`.
- Frozen Markdown corpus: 1,890 lines / 339,751 bytes / SHA-256 `58405ad08d408147b72ee952b5e6422963e62da19c31c8b13a5c8d91a2375e98`.
- Baseline package: 33 files / 4,000,178 bytes / tree SHA-256 `25cd0e4ea9fa81d844e06ecec197293e94905a8c60b724e6100cadc79f757713`.
- Baseline runtime: 15 packages / 235 files / 8,095,658 bytes / tree SHA-256 `459a945b686371c136bfaaa5034b4ba581bb2f032f68ea63d150c2d1eafd8e73`.
- The removed builder contributes exactly one file and 88,026 bytes. After the truthful `SKILL.md` route rewrite and the portable-contract update, the exact runtime is 234 files / 8,007,402 bytes / tree SHA-256 `14835bdef7236dd160264113a2494c4ab253ebd7ae5f9817910dcba4a36cbf27`, a net reduction of one file and 88,256 bytes. `ksrf-argument-patterns` is 32 files / 3,911,836 bytes / tree SHA-256 `ea233c62c24e3d0148c112f0f8145a2cbae53ef7d61ec55810ab30d9b6f98d2e`. The root release tool remains present, so its bytes do not decrease. The final exact installation also removes any stale copy from the global skill.
- No corpus content, source status, legal method, legal conclusion, authority promotion, or filing gate changes.
