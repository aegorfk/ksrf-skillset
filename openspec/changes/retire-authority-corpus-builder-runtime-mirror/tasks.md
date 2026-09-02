## 1. Contract and baseline

- [x] 1.1 Freeze live base `ae1f66cdc61a61cad5a7e90474b5ac02b908a330` in a dedicated worktree and branch.
- [x] 1.2 Inventory the identical builder copies, four missing runtime inputs, user backlink, generated outputs, ownership/sync contracts, and baseline manifest.
- [x] 1.3 Record proposal, design, delta requirements, risks, non-goals, exact preservation hashes, and publication plan before implementation.
- [x] 1.4 Add failing tests for the new ownership model, empty mirror CLIs, reverse-sync filtering, exact-install cleanup, nested absence, output preservation, truthful route, and clean-room payload.

## 2. Runtime cleanup

- [x] 2.1 Move the builder from active mirrored ownership to one root-only owner plus one exact excluded former skill identity; keep the legacy retired-root list empty.
- [x] 2.2 Delete the nested skill duplicate and make both validators fail closed on reintroduction.
- [x] 2.3 Replace the user-facing builder backlink with the installed prebuilt-corpus route; update public installation documentation.
- [x] 2.4 Pin final package/runtime projections and regenerate the manifest from the frozen live base.

## 3. Verification and publication

- [x] 3.1 Run focused RED/GREEN, full suites, source strict, clean-room runtime strict, sync migration tests, strict OpenSpec, manifest verification, and diff checks.
- [x] 3.2 Obtain independent semantic, test, and release review with no unresolved P1/P2.
- [ ] 3.3 Publish atomically to `main`, confirm the live SHA, install and verify the exact global payload.
- [ ] 3.4 Archive the completed OpenSpec change, regenerate the manifest from the merge SHA, and publish the final evidence commit.
