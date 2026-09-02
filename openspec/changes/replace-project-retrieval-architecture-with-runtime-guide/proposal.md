## Why

The installed `position-retrieval-architecture.md` presents a project-bound Qdrant/Neo4j stack, local services, scripts, generated datasets, and historical corpus counters as if they were available to a skillset user. None of those project artifacts ships in the runtime payload, so the guide sends a user toward commands that cannot run after installation and obscures the useful legal method underneath them.

## What Changes

- Replace the project architecture with a standalone guide for manually discovering, comparing, and verifying candidate positions of the Constitutional Court.
- Remove every command, service default, local project path, generated result path, stale corpus counter, and conceptual MCP operation that is not shipped by the skillset.
- Preserve the useful legal method: query profile, juridical chunk roles, norm-to-right graph, proportionality checks, lexical and structural candidate discovery, adverse search, official-source and locator verification, transfer limits, provenance, and candidate-only status.
- Route the owning skill to the guide as a manual candidate-search and verification method, not as an implemented vector/graph capability.
- Add exact regressions for dead references, preserved methodology, payload membership, backlink truthfulness, output fields, and clean-room installation.
- Update public documentation with the user-facing effect and regenerate the exact manifest from frozen live `main`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ksrf-runtime-methodology-truthfulness`: installed retrieval guidance must be standalone, must not claim project-only infrastructure or artifacts, and must preserve official-source, adverse-search, provenance, transfer-limit, and human-review gates.

## Impact

- Frozen base: `a859d7e0db3eeccd78310d6b828ad9389751409a`.
- Primary runtime target: `skills/ksrf-argument-patterns/references/position-retrieval-architecture.md`, 278 lines / 20,647 bytes / SHA-256 `13a62d996e5fde6e42d1d980dbaf07ff9e16eb1d391a69bef8be4a5c0f51e809`.
- Owning backlink: `skills/ksrf-argument-patterns/SKILL.md`.
- Existing focused consumer test: `tests/test_runtime_payload_guidance.py`; a dedicated regression will replace its minimal assertions.
- Baseline package: 33 files / 3,999,635 bytes / tree SHA-256 `07ebe492c7f8408ab0b75da976c89eecbd9e2b7d219900ebb48b743fbd63c285`.
- Baseline runtime: 15 packages / 235 files / 8,069,449 bytes / tree SHA-256 `1c9252c0c9a82ab52fab0dc9e7d95f35bc585e8ccde4e82cbf1c81329af8b1d7`.
- Release tools remain unchanged at 9 files / 197,557 bytes / tree SHA-256 `ef4d7395c10f436b13f4cd09ed450a65519a5dce78cd7f8a346b363c9ff80ddd`.
- Reviewed replacement guide: 190 lines / 20,372 bytes / SHA-256 `cbc562c0fb543735afce3a09fe9494e9ee8cd55c7fd2562030db7b62f1881ef9`.
- Reviewed owning skill: 107 lines / 22,824 bytes / SHA-256 `3609fdc94431ac3aed6c781a0fc513d296a77ca5c71ebcb785b795da284ceb7f`.
- Final package projection: 33 files / 4,000,178 bytes / tree SHA-256 `25cd0e4ea9fa81d844e06ecec197293e94905a8c60b724e6100cadc79f757713`.
- Final runtime projection: 15 packages / 235 files / 8,069,992 bytes / tree SHA-256 `72c775d22eebfa7951a5d1fd47413777fda561c20ee5990910a618e361e97da1`.
- No executable retrieval backend, official-source authority, legal conclusion, filing readiness, or expected outcome is introduced.
