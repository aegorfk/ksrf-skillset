## Context

The corpus builder was historically mirrored between `skills/ksrf-argument-patterns/scripts/` and root `tools/`. That arrangement makes a maintainer workflow appear runnable from the installed skill even though four required input families are absent: a Blokhin bibliography source, the SКO index PDF, the `Международное правосудие` index PDF, and a local Zakon.ru JSON export. The generated JSON and Markdown corpus are already installed and are the only user-facing outputs needed at runtime.

## Goals / Non-Goals

**Goals:**

- remove the duplicate from source and installed runtime;
- preserve one content-identical root owner for maintainers and correct its mode to executable;
- keep both generated corpus outputs byte-identical;
- make reverse sync ignore a stale installed mirror rather than copy it back;
- fail closed if the retired nested path reappears;
- remove the dead user-facing command while preserving the live corpus route;
- prove an exact one-file, 88,026-byte runtime reduction.

**Non-Goals:**

- regenerate, edit, shrink, or reclassify the corpus;
- delete the root maintainer tool;
- ship the four missing source inputs;
- expose a new runtime command or claim automated authority promotion;
- change source, legal, human-review, or filing gates.

## Decisions

1. **One root owner.** `tools/build_constitutionalist_authority_corpus.py` joins the root-only release-tool set, remains fixed at SHA-256 `b1c393460420cc1c3382720d60188dbe4e52f9c72a78d87457f833682f67c33f`, and uses executable mode `100755` like the other root tools.
2. **The old mirror is not placed in the legacy retired-root list.** The active mirrored set becomes empty, the root-only set gains the builder, and the legacy `RETIRED_MIRRORED_TOOL_NAMES` set remains empty. That legacy list deletes files from root `tools/`, so using it here would destroy the canonical owner.
3. **Exact nested path is source-only policy data.** Both `tools/skillset_file_contract.py` and the portable validator list `ksrf-argument-patterns/scripts/build_constitutionalist_authority_corpus.py` among root-only skill paths. Runtime presence fails as `SOURCE_ONLY_ARTIFACT_PRESENT`; source-repository presence fails as `ROOT_ONLY_DUPLICATE_PRESENT`.
4. **Users keep outputs, not build machinery.** The JSON and Markdown corpus remain byte-identical and installed. `SKILL.md` routes readers to those references, explains that they are a bounded prebuilt map, and does not mention the retired script path.
5. **No silent regeneration.** This change never runs the builder and never invents replacements for its missing inputs.
6. **Reverse sync and final install have separate effects.** The exact root-only skill path is filtered out of the global source payload, so reverse sync cannot copy a stale installed mirror back into the already-clean source tree. The next canonical exact installation replaces the global skill directory and removes the stale mirror there. Both legacy mirrored-tool CLI lists emit nothing, leaving the root owner untouched.
7. **Publication remains atomic.** The manifest is regenerated from live `main`; source strict, clean-room runtime strict, ownership tests, sync tests, exact output digests, independent review, live SHA verification, installation, and OpenSpec archive remain required.

## Risks / Trade-offs

- **Maintainer command becomes less discoverable to users** → intentional: it is documented in the source/publication contract and remains release-covered under root `tools/`, while runtime documentation points to the usable outputs.
- **The legacy retired list deletes the root owner** → keep it empty and assert both legacy mirror CLIs emit no names.
- **Reverse sync reintroduces the duplicate** → bind exclusion to the exact root-only skill path; source validation rejects any surviving target copy, and sync tests start from a clean source target with a stale global mirror.
- **Generated corpus drifts during cleanup** → exact SHA/line/byte invariants block publication.
- **A similarly named legitimate file is over-excluded** → exclusion and validation use the full skill-relative identity, not a global basename rule.

## Migration Plan

1. Freeze the base, both identical builder files, both corpus outputs, backlink, ownership sets, sync behavior, and manifest.
2. Record this OpenSpec change and validate it strictly before implementation.
3. Add RED tests for the root-only ownership model, empty mirror CLIs, nested absence, output preservation, truthful route, reverse-sync filtering, exact-install cleanup, and clean-room payload.
4. Remove the nested copy, update canonical and portable contracts, replace the user backlink, update publication docs, and regenerate the manifest.
5. Run focused and full tests, both validation profiles, clean-room install, OpenSpec strict, exact manifest verification, and independent reviews.
6. Publish to `main`, verify live SHA, install globally, archive the change, regenerate the evidence manifest, and publish the final SHA.

Rollback is the exact prior `main` commit; no data or schema migration is involved.

## Open Questions

None.
